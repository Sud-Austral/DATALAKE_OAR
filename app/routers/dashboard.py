from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db # Asumiendo que existe o lo crearé

router = APIRouter()

@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Obtiene estadísticas reales para el dashboard."""
    # Queries reales a las 7 tablas creadas en db.sql
    datasets_count = await db.scalar(text("SELECT count(*) FROM datasets"))
    files_count = await db.scalar(text("SELECT count(*) FROM files"))
    success_rate = await db.scalar(text("""
        SELECT 
            CASE WHEN count(*) > 0 
            THEN (count(*) FILTER (WHERE status = 'success')::float / count(*)) * 100 
            ELSE 100 END 
        FROM api_ingestions
    """))
    total_size = await db.scalar(text("SELECT sum(size_bytes) FROM files")) or 0
    
    return {
        "datasets": datasets_count,
        "files": files_count,
        "success_rate": f"{success_rate:.1f}%",
        "storage": f"{total_size / (1024**3):.2f} GB"
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
    return [dict(row) for row in result.mappings()]
