from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.utils.storage import storage
import uuid

router = APIRouter()

# BUG FIX #7: La extensión del archivo se detectaba con split('.')[−1] lo cual
# falla si el nombre no tiene extensión, o si tiene múltiples puntos (ej: data.v2.csv).
ALLOWED_TYPES = {"csv", "geojson", "pdf", "zip", "shp", "dbf", "prj", "shx"}


def resolve_file_type(filename: str) -> str:
    parts = filename.rsplit(".", 1)
    if len(parts) < 2:
        return "other"
    ext = parts[-1].lower()
    if ext in ("shp", "dbf", "prj", "shx"):
        return "shapefile"
    return ext if ext in ALLOWED_TYPES else "other"


@router.post("/upload")
async def upload_file(
    dataset_id: str = Form(...),
    user_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Sube un archivo físico a MinIO y registra metadatos en PostgreSQL."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="El archivo no tiene nombre.")

    file_type = resolve_file_type(file.filename)
    content = await file.read()
    file_uuid = str(uuid.uuid4())
    object_name = f"{dataset_id}/{file_uuid}_{file.filename}"

    try:
        # 1. Persistencia física en MinIO
        storage_path = storage.upload_file(
            file_content=content,
            object_name=object_name,
            content_type=file.content_type,
        )

        # 2. Registro en PostgreSQL
        await db.execute(
            text("""
                INSERT INTO files
                    (id, dataset_id, name, original_name, file_type, mime_type,
                     storage_path, bucket, size_bytes, uploaded_by)
                VALUES
                    (:id, :dataset_id::uuid, :name, :orig_name, :type, :mime,
                     :path, :bucket, :size, :user::uuid)
            """),
            {
                "id": file_uuid,
                "dataset_id": dataset_id,
                "name": file.filename,
                "orig_name": file.filename,
                "type": file_type,
                "mime": file.content_type,
                "path": storage_path,
                "bucket": storage.bucket_name,
                "size": len(content),
                "user": user_id,
            },
        )

        # 3. Audit Log
        await db.execute(
            text("""
                INSERT INTO audit_log (user_id, action, entity, entity_id, details)
                VALUES (:user::uuid, 'UPLOAD', 'files', :id::uuid, :details)
            """),
            {
                "user": user_id,
                "id": file_uuid,
                "details": f"Archivo '{file.filename}' ({file_type}) subido — {len(content)} bytes",
            },
        )

        await db.commit()
        return {"status": "success", "file_id": file_uuid, "path": storage_path}

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list/{dataset_id}")
async def list_files(dataset_id: str, db: AsyncSession = Depends(get_db)):
    """Lista archivos de un dataset específico."""
    result = await db.execute(
        text("SELECT * FROM files WHERE dataset_id = :ds_id::uuid ORDER BY created_at DESC"),
        {"ds_id": dataset_id},
    )
    rows = result.mappings().all()
    return [
        {
            **{k: v for k, v in row.items() if k not in ("id", "dataset_id", "uploaded_by", "created_at")},
            "id": str(row["id"]),
            "dataset_id": str(row["dataset_id"]),
            "uploaded_by": str(row["uploaded_by"]) if row["uploaded_by"] else None,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in rows
    ]


@router.get("/download/{file_id}")
async def get_file_url(file_id: str, db: AsyncSession = Depends(get_db)):
    """Genera una URL temporal de descarga."""
    result = await db.execute(
        text("SELECT storage_path, name FROM files WHERE id = :id::uuid"),
        {"id": file_id},
    )
    file_data = result.fetchone()

    if not file_data:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    # Quitamos el prefijo "bucket/" del path para obtener la object key
    path_only = "/".join(file_data.storage_path.split("/")[1:])
    url = storage.get_download_url(path_only)

    if not url:
        raise HTTPException(status_code=500, detail="No se pudo generar la URL de descarga")

    return {"url": url, "filename": file_data.name}
