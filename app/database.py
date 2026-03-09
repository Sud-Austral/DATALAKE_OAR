from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import os
import logging

logger = logging.getLogger(__name__)

_engine = None
_session_factory = None

def _get_engine():
    """Crea el engine de forma lazy, solo cuando se necesita."""
    global _engine, _session_factory
    if _engine is None:
        raw_url = os.getenv("DATABASE_URL", "")
        if not raw_url:
            available_vars = ", ".join([k for k in os.environ.keys() if "URL" in k or "DB" in k or "POSTGRES" in k])
            raise RuntimeError(
                f"DATABASE_URL no encontrada en el entorno. "
                f"Variables detectadas similares: [{available_vars}]. "
                "Asegúrate de configurar DATABASE_URL en la pestaña Variables de Railway."
            )

        # asyncpg requiere el esquema postgresql+asyncpg://
        db_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        logger.info("Inicializando conexión a la base de datos...")

        _engine = create_async_engine(db_url, echo=False, pool_pre_ping=True)
        _session_factory = async_sessionmaker(
            _engine, expire_on_commit=False, class_=AsyncSession
        )
    return _engine, _session_factory

async def get_db():
    """Dependency de FastAPI para inyectar sesiones de base de datos."""
    _, factory = _get_engine()
    async with factory() as session:
        yield session
