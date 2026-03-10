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
        import uuid
        result = await db.execute(
            text("""
                INSERT INTO datasets (name, description, domain, owner_id)
                VALUES (:name, :description, :domain, :owner_id)
                RETURNING id, created_at
            """),
            {
                "name": ds.name,
                "description": ds.description,
                "domain": ds.domain,
                "owner_id": uuid.UUID(ds.owner_id)
            },
        )
        row = result.fetchone()
        new_id = row[0]

        import json
        await db.execute(
            text("""
                INSERT INTO audit_log (user_id, action, entity, entity_id, details)
                VALUES (:user, 'CREATE', 'datasets', :id, CAST(:details AS JSONB))
            """),
            {
                "user": uuid.UUID(ds.owner_id),
                "id": new_id,
                "details": json.dumps({"dataset_name": ds.name}),
            },
        )
        await db.commit()
        return {"id": str(new_id), "status": "created"}

    except Exception as e:
        await db.rollback()
        logger.error(f"Error creando dataset: {e}")
        raise HTTPException(status_code=500, detail=str(e))
