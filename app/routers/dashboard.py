from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Obtiene estadísticas reales para el dashboard."""
    try:
        datasets_count = await db.scalar(text("SELECT count(*) FROM datasets WHERE status = 'active'"))
        files_count    = await db.scalar(text("SELECT count(*) FROM files"))

        success_rate_raw = await db.scalar(text("""
            SELECT
                CASE WHEN count(*) > 0
                THEN round((count(*) FILTER (WHERE status = 'success')::numeric / count(*)) * 100, 1)
                ELSE 100.0 END
            FROM api_ingestions
        """))
        success_rate = float(success_rate_raw) if success_rate_raw is not None else 100.0

        total_bytes = await db.scalar(text("SELECT coalesce(sum(size_bytes), 0) FROM files"))
        total_bytes = int(total_bytes or 0)

        # Formatear el tamaño de forma legible
        if total_bytes >= 1024 ** 3:
            storage_str = f"{total_bytes / (1024**3):.2f} GB"
        elif total_bytes >= 1024 ** 2:
            storage_str = f"{total_bytes / (1024**2):.1f} MB"
        else:
            storage_str = f"{total_bytes / 1024:.1f} KB"

        return {
            "datasets":     int(datasets_count or 0),
            "files":        int(files_count or 0),
            "success_rate": f"{success_rate:.1f}%",
            "storage":      storage_str,
        }
    except Exception as e:
        logger.error(f"Error obteniendo stats: {e}")
        # Devolver ceros en vez de 500 para que el dashboard no falle en cold-start
        return {"datasets": 0, "files": 0, "success_rate": "N/A", "storage": "0 KB"}


@router.get("/recent-activity")
async def get_recent_activity(db: AsyncSession = Depends(get_db)):
    """Obtiene los últimos movimientos registrados en el audit_log."""
    try:
        result = await db.execute(text("""
            SELECT action, entity, details, created_at
            FROM audit_log
            ORDER BY created_at DESC
            LIMIT 10
        """))
        rows = result.mappings().all()
        return [
            {
                "action":     row["action"],
                "entity":     row["entity"],
                "details":    row["details"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Error obteniendo actividad reciente: {e}")
        return []
