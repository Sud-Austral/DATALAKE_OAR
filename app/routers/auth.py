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
    """Verifica las credenciales del usuario."""
    # Como desarrollador senior, protegemos la ejecución con try/except para capturar el error real
    try:
        # Usamos :password::text para asegurar tipos
        query = text("""
            SELECT id, username, role 
            FROM users 
            WHERE username = :username AND password = crypt(:password::text, password)
        """)
        
        result = await db.execute(query, {
            "username": credentials.username, 
            "password": credentials.password
        })
        user = result.fetchone()

        if not user:
            logger.warning(f"Intento de login fallido para usuario: {credentials.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario o contraseña incorrectos"
            )

        logger.info(f"Login exitoso: {user.username} ({user.role})")
        
        return {
            "success": True,
            "token": "simulated_jwt_token_for_now",
            "user": {
                "id": str(user.id),
                "username": user.username,
                "role": user.role
            }
        }
    except Exception as e:
        logger.error(f"Error crítico en proceso de login: {str(e)}")
        # Si el error es una tabla no encontrada o función crypt no existe, 
        # lo capturamos aquí para no dar un 500 genérico si es posible.
        if "users" in str(e).lower():
            raise HTTPException(status_code=500, detail="La tabla 'users' no existe. Ejecuta DATABASE/db.sql")
        if "crypt" in str(e).lower():
            raise HTTPException(status_code=500, detail="Extensión 'pgcrypto' no instalada. Ejecuta CREATE EXTENSION pgcrypto")
        
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")
