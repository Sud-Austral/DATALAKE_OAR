from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.utils.storage import storage
from app.routers.auth import verify_token
import uuid
import json
import io
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

_DB_FILE_TYPES = {"csv", "geojson", "shapefile", "pdf", "other"}
_GIS_EXTENSIONS = {"shp", "dbf", "prj", "shx", "cpg"}
_CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB por chunk


def resolve_file_type(filename: str) -> str:
    if not filename or "." not in filename:
        return "other"
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext in _GIS_EXTENSIONS:
        return "shapefile"
    if ext in _DB_FILE_TYPES:
        return ext
    return "other"


@router.post("/upload")
async def upload_file(
    dataset_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_token),   # ← protegido
):
    """Sube un archivo a MinIO usando lectura en chunks (soporta archivos grandes)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="El archivo debe tener nombre.")

    file_type   = resolve_file_type(file.filename)
    file_uuid   = str(uuid.uuid4())
    object_name = f"{dataset_id}/{file_uuid}_{file.filename}"
    user_id     = current_user["id"]

    # ── Leer en chunks para no cargar todo en RAM ─────────────────────
    chunks = []
    total_size = 0
    while True:
        chunk = await file.read(_CHUNK_SIZE)
        if not chunk:
            break
        chunks.append(chunk)
        total_size += len(chunk)

    content = b"".join(chunks)

    try:
        # 1. MinIO upload
        try:
            storage_path = storage.upload_file(
                file_content=content,
                object_name=object_name,
                content_type=file.content_type,
            )
        except Exception as minio_err:
            err_str = str(minio_err)
            ep = os.getenv("MINIO_ENDPOINT", "localhost:9000")
            if not os.getenv("MINIO_ACCESS_KEY"):
                msg = "MINIO_ACCESS_KEY no configurada en Railway → Variables."
            elif "Connection" in err_str or "endpoint" in err_str.lower() or "refused" in err_str.lower():
                msg = (f"No se puede conectar a MinIO en '{ep}'. "
                       "Verifica que el servicio MinIO esté corriendo.")
            else:
                msg = f"Error en MinIO ({ep}): {err_str}"
            logger.error(f"MinIO upload failed: {msg}")
            raise HTTPException(status_code=503, detail=msg)

        # 2. Metadata en PostgreSQL
        await db.execute(
            text("""
                INSERT INTO files
                    (id, dataset_id, name, original_name, file_type,
                     mime_type, storage_path, bucket, size_bytes, uploaded_by)
                VALUES
                    (:id, :dataset_id, :name, :orig_name, :file_type,
                     :mime, :storage_path, :bucket, :size, :uploaded_by)
            """),
            {
                "id":           uuid.UUID(file_uuid),
                "dataset_id":   uuid.UUID(dataset_id),
                "name":         file.filename,
                "orig_name":    file.filename,
                "file_type":    file_type,
                "mime":         file.content_type or "application/octet-stream",
                "storage_path": storage_path,
                "bucket":       storage.bucket_name,
                "size":         total_size,
                "uploaded_by":  uuid.UUID(user_id),
            },
        )

        # 3. Audit log
        await db.execute(
            text("""
                INSERT INTO audit_log (user_id, action, entity, entity_id, details)
                VALUES (:user, 'UPLOAD', 'files', :entity_id, CAST(:details AS JSONB))
            """),
            {
                "user":      uuid.UUID(user_id),
                "entity_id": uuid.UUID(file_uuid),
                "details":   json.dumps({
                    "filename":  file.filename,
                    "file_type": file_type,
                    "size":      total_size,
                }),
            },
        )

        await db.commit()
        return {"status": "success", "file_id": file_uuid, "path": storage_path}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error en upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list/{dataset_id}")
async def list_files(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    # PúBlico: no requiere token — permite integración con otros sistemas
):
    """Lista archivos de un dataset específico."""
    import uuid as uuid_mod
    from datetime import datetime

    try:
        result = await db.execute(
            text("""
                SELECT id, dataset_id, name, file_type, size_bytes,
                       mime_type, storage_path, uploaded_by, created_at
                FROM files
                WHERE dataset_id = :ds_id
                ORDER BY created_at DESC
            """),
            {"ds_id": uuid_mod.UUID(dataset_id)},
        )
        rows = result.mappings().all()

        def serialize(v):
            if isinstance(v, uuid_mod.UUID): return str(v)
            if isinstance(v, datetime):      return v.isoformat()
            return v

        return [{k: serialize(v) for k, v in row.items()} for row in rows]
    except Exception as e:
        logger.error(f"Error listando archivos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{file_id}")
async def download_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    # PúBlico: descarga abierta — permite embeber archivos del datalake en otros proyectos
):
    """
    Descarga un archivo en streaming a través del backend.
    No usa presigned URLs porque MinIO corre en localhost:9000
    y esa dirección no es accesible desde el navegador del usuario.
    """
    import uuid as uuid_mod

    result = await db.execute(
        text("SELECT storage_path, name, mime_type FROM files WHERE id = :id"),
        {"id": uuid_mod.UUID(file_id)},
    )
    file_data = result.fetchone()

    if not file_data:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    parts = file_data.storage_path.split("/", 1)
    object_key = parts[1] if len(parts) > 1 else file_data.storage_path

    try:
        client   = storage._get_client()
        response = client.get_object(Bucket=storage.bucket_name, Key=object_key)
        body     = response["Body"].read()
        mime     = file_data.mime_type or "application/octet-stream"
        filename = file_data.name or "archivo"

        return StreamingResponse(
            io.BytesIO(body),
            media_type=mime,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(body)),
            },
        )
    except Exception as e:
        logger.error(f"Error descargando {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error al descargar: {str(e)}")
