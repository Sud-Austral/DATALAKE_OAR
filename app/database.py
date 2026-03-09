from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import os
import logging

logger = logging.getLogger(__name__)

_engine = None
_session_factory = None


def _get_engine():
    """Crea el engine de forma lazy, solamente cuando se necesita por primera vez."""
    global _engine, _session_factory
    if _engine is None:
        raw_url = os.getenv("DATABASE_URL", "").strip()
        if not raw_url:
            similar = ", ".join(
                k for k in os.environ if any(x in k.upper() for x in ("URL", "DB", "POSTGRES", "PG"))
            )
            raise RuntimeError(
                f"DATABASE_URL no encontrada. Variables similares detectadas: [{similar}]. "
                "Configúrala en Railway > Variables o en el archivo .env."
            )

        # FIX-5: Manejar los 3 prefijos que puede tener la URL de PostgreSQL.
        # Railway / Heroku usan "postgres://", asyncpg requiere "postgresql+asyncpg://"
        db_url = (
            raw_url
            .replace("postgres://",    "postgresql+asyncpg://", 1)
            .replace("postgresql://",  "postgresql+asyncpg://", 1)
        )
        # Evitar doble reemplazo si ya tiene el prefijo correcto
        if db_url.startswith("postgresql+asyncpg+asyncpg://"):
            db_url = db_url.replace("postgresql+asyncpg+asyncpg://", "postgresql+asyncpg://", 1)

        logger.info("Inicializando pool de conexión a PostgreSQL...")

        _engine = create_async_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,   # Detecta conexiones muertas automáticamente
            pool_size=5,
            max_overflow=10,
        )
        _session_factory = async_sessionmaker(
            _engine, expire_on_commit=False, class_=AsyncSession
        )
    return _engine, _session_factory


async def get_db():
    """Dependency de FastAPI para inyectar sesiones de base de datos."""
    _, factory = _get_engine()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
