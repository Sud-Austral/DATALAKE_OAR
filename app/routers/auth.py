"""
Autenticación JWT para el Datalake OAR.
- login() genera un token firmado (HS256) con expiración de 8 horas
- verify_token() valida el token en cada request protegido
- El SECRET_KEY se lee de la variable de entorno (Railway → Variables)
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from jose import jwt, JWTError

from app.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Configuración JWT ──────────────────────────────────────────────────
_SECRET   = os.getenv("SECRET_KEY", "change_me_to_a_random_256bit_secret")
_ALGO     = "HS256"
_EXPIRE_H = 8  # horas

_bearer = HTTPBearer(auto_error=False)


# ── Modelos ────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


# ── Helpers ────────────────────────────────────────────────────────────
def _create_token(user_id: str, username: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=_EXPIRE_H)
    payload = {
        "sub":      user_id,
        "username": username,
        "role":     role,
        "exp":      expire,
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGO)


def verify_token(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    """
    Dependency para proteger endpoints.
    Uso: async def mi_endpoint(user=Depends(verify_token)):
    """
    if not creds or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación requerido.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(creds.credentials, _SECRET, algorithms=[_ALGO])
        return {
            "id":       payload["sub"],
            "username": payload["username"],
            "role":     payload["role"],
        }
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido o expirado: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Endpoints ──────────────────────────────────────────────────────────
@router.post("/login")
async def login(credentials: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Verifica credenciales contra pgcrypto y devuelve JWT firmado."""
    try:
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

        user_id  = str(user.id)
        token    = _create_token(user_id, user.username, user.role)

        logger.info(f"Login exitoso: {user.username} [{user.role}]")
        return {
            "success": True,
            "token": token,
            "user": {
                "id":       user_id,
                "username": user.username,
                "role":     user.role,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en login: {e}")
        detail = str(e)
        if "crypt" in detail.lower():
            detail = "La extensión pgcrypto no está instalada. Ejecuta setup_railway.sql."
        raise HTTPException(status_code=500, detail=detail)


@router.get("/me")
async def me(user: dict = Depends(verify_token)):
    """Devuelve el usuario autenticado actual (valida el token)."""
    return user
