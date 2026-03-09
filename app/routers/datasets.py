from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class DatasetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    domain: str
    owner_id: str


def _serialize_row(row: dict) -> dict:
    """Convierte UUID y datetime a tipos JSON-serializables."""
    import uuid
    from datetime import datetime
    result = {}
    for k, v in row.items():
        if isinstance(v, uuid.UUID):
            result[k] = str(v)
        elif isinstance(v, datetime):
            result[k] = v.isoformat()
        else:
            result[k] = v
    return result


@router.get("/")
async def list_datasets(db: AsyncSession = Depends(get_db)):
    """Lista todos los datasets activos."""
    result = await db.execute(
        text("SELECT * FROM datasets WHERE status = 'active' ORDER BY created_at DESC")
    )
    return [_serialize_row(dict(row)) for row in result.mappings().all()]


@router.post("/", status_code=201)
async def create_dataset(ds: DatasetCreate, db: AsyncSession = Depends(get_db)):
    """Crea un nuevo contenedor de datos (Dataset)."""
    try:
        result = await db.execute(
            text("""
                INSERT INTO datasets (name, description, domain, owner_id)
                VALUES (:name, :description, :domain, :owner_id::uuid)
                RETURNING id, created_at
            """),
            ds.model_dump(),
        )
        row = result.fetchone()
        new_id = row[0]

        # FIX-10: details en audit_log es JSONB — se pasa como dict, no como string.
        await db.execute(
            text("""
                INSERT INTO audit_log (user_id, action, entity, entity_id, details)
                VALUES (:user::uuid, 'CREATE', 'datasets', :id, :details::jsonb)
            """),
            {
                "user": ds.owner_id,
                "id": str(new_id),
                "details": f'{{"dataset_name": "{ds.name}"}}',
            },
        )
        await db.commit()
        return {"id": str(new_id), "status": "created"}

    except Exception as e:
        await db.rollback()
        logger.error(f"Error creando dataset: {e}")
        raise HTTPException(status_code=500, detail=str(e))
