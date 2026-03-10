from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.utils.storage import storage
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Tipos de archivo aceptados por el CHECK constraint de la tabla files
_DB_FILE_TYPES = {"csv", "geojson", "shapefile", "pdf", "other"}
_GIS_EXTENSIONS = {"shp", "dbf", "prj", "shx", "cpg"}


def resolve_file_type(filename: str) -> str:
    """
    Resuelve el valor correcto para la columna file_type de PostgreSQL.
    Debe ser uno de: csv, geojson, shapefile, pdf, other
    """
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
    user_id:    str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Sube un archivo a MinIO y registra metadatos en PostgreSQL."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="El archivo debe tener nombre.")

    file_type   = resolve_file_type(file.filename)
    content     = await file.read()
    file_uuid   = str(uuid.uuid4())
    object_name = f"{dataset_id}/{file_uuid}_{file.filename}"

    try:
        # 1. MinIO
        storage_path = storage.upload_file(
            file_content=content,
            object_name=object_name,
            content_type=file.content_type,
        )

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
                "size":         len(content),
                "uploaded_by":  uuid.UUID(user_id) if user_id else None,
            },
        )

        # 3. Audit log con details como JSONB
        import json
        await db.execute(
            text("""
                INSERT INTO audit_log (user_id, action, entity, entity_id, details)
                VALUES (:user, 'UPLOAD', 'files', :entity_id, CAST(:details AS JSONB))
            """),
            {
                "user":      uuid.UUID(user_id) if user_id else None,
                "entity_id": uuid.UUID(file_uuid),
                "details":   json.dumps({
                    "filename":  file.filename,
                    "file_type": file_type,
                    "size":      len(content),
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
async def list_files(dataset_id: str, db: AsyncSession = Depends(get_db)):
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
async def get_file_url(file_id: str, db: AsyncSession = Depends(get_db)):
    """Genera una URL temporal firmada para descarga del archivo."""
    import uuid as uuid_mod
    result = await db.execute(
        text("SELECT storage_path, name FROM files WHERE id = :id"),
        {"id": uuid_mod.UUID(file_id)},
    )
    file_data = result.fetchone()


    if not file_data:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    # storage_path = "bucket/dataset_id/uuid_filename"
    # Quitamos el prefijo "bucket/" para obtener la object key
    parts = file_data.storage_path.split("/", 1)
    object_key = parts[1] if len(parts) > 1 else file_data.storage_path

    url = storage.get_download_url(object_key)
    if not url:
        raise HTTPException(status_code=500, detail="No se pudo generar URL de descarga")

    return {"url": url, "filename": file_data.name}
