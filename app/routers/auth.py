from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(credentials: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Verifica las credenciales del usuario contra pgcrypto."""
    try:
        # FIX-7: Query limpia sin casts en parámetros (::text rompe asyncpg).
        # asyncpg convierte :param → $N automáticamente; cualquier sufijo :: lo rompe.
        result = await db.execute(
            text("""
                SELECT id, username, role
                FROM users
                WHERE username = :username
                  AND is_active = true
                  AND password = crypt(:password, password)
            """),
            {"username": credentials.username.strip(), "password": credentials.password},
        )
        user = result.fetchone()

        if not user:
            logger.warning(f"Login fallido para '{credentials.username}'")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario o contraseña incorrectos",
            )

        logger.info(f"Login exitoso: {user.username} [{user.role}]")

        # FIX-8: UUID no es JSON-serializable — se convierte a str.
        return {
            "success": True,
            "token": "simulated_jwt_token_for_now",
            "user": {
                "id": str(user.id),
                "username": user.username,
                "role": user.role,
            },
        }

    except HTTPException:
        raise  # Re-lanzar 401 sin capturarlo como error interno
    except Exception as e:
        logger.error(f"Error en login: {e}")
        detail = str(e)
        if "crypt" in detail.lower():
            detail = "La extensión pgcrypto no está instalada en la base de datos."
        elif "users" in detail.lower() and "exist" in detail.lower():
            detail = "La tabla 'users' no existe. Ejecuta DATABASE/db.sql primero."
        raise HTTPException(status_code=500, detail=detail)
