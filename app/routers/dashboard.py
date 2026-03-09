from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db

router = APIRouter()


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Obtiene estadísticas reales para el dashboard."""
    datasets_count = await db.scalar(text("SELECT count(*) FROM datasets"))
    files_count = await db.scalar(text("SELECT count(*) FROM files"))

    # BUG FIX #5: Si success_rate es None (tabla vacía), el format :.1f lanzaba
    # TypeError. Se añade fallback explícito a 100.0 cuando no hay registros.
    success_rate_raw = await db.scalar(text("""
        SELECT
            CASE WHEN count(*) > 0
            THEN (count(*) FILTER (WHERE status = 'success')::float / count(*)) * 100
            ELSE 100.0 END
        FROM api_ingestions
    """))
    success_rate = success_rate_raw if success_rate_raw is not None else 100.0

    total_size = await db.scalar(text("SELECT coalesce(sum(size_bytes), 0) FROM files"))

    return {
        "datasets": datasets_count or 0,
        "files": files_count or 0,
        "success_rate": f"{success_rate:.1f}%",
        "storage": f"{total_size / (1024 ** 3):.2f} GB",
    }


@router.get("/recent-activity")
async def get_recent_activity(db: AsyncSession = Depends(get_db)):
    """Obtiene los últimos movimientos registrados en el audit_log."""
    query = text("""
        SELECT action, entity, details, created_at
        FROM audit_log
        ORDER BY created_at DESC
        LIMIT 5
    """)
    result = await db.execute(query)
    rows = result.mappings().all()
    # BUG FIX: created_at es un objeto datetime — se serializa a ISO string
    # para que el frontend pueda parsearla correctamente con new Date()
    return [
        {**dict(row), "created_at": row["created_at"].isoformat()}
        for row in rows
    ]
