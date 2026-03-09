from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class DatasetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    domain: str
    owner_id: str


@router.get("/")
async def list_datasets(db: AsyncSession = Depends(get_db)):
    """Lista todos los datasets activos."""
    query = text(
        "SELECT * FROM datasets WHERE status = 'active' ORDER BY created_at DESC"
    )
    result = await db.execute(query)
    rows = result.mappings().all()
    # BUG FIX #6: UUID y datetime no son serializables por defecto en JSON.
    # Se convierten a str/isoformat explícitamente.
    return [
        {
            **{k: v for k, v in row.items() if k not in ("id", "owner_id", "created_at", "updated_at")},
            "id": str(row["id"]),
            "owner_id": str(row["owner_id"]) if row["owner_id"] else None,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }
        for row in rows
    ]


@router.post("/", status_code=201)
async def create_dataset(ds: DatasetCreate, db: AsyncSession = Depends(get_db)):
    """Crea un nuevo contenedor de datos (Dataset)."""
    query = text("""
        INSERT INTO datasets (name, description, domain, owner_id)
        VALUES (:name, :description, :domain, :owner_id::uuid)
        RETURNING id
    """)
    result = await db.execute(query, ds.model_dump())
    new_id = result.fetchone()[0]

    await db.execute(
        text("""
            INSERT INTO audit_log (user_id, action, entity, entity_id)
            VALUES (:user::uuid, 'CREATE', 'datasets', :id)
        """),
        {"user": ds.owner_id, "id": new_id},
    )

    await db.commit()
    return {"id": str(new_id), "status": "created"}
