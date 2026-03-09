from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(credentials: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Verifica las credenciales del usuario."""
    # Como la contraseña se encriptó en PostgreSQL con pgcrypto: crypt('...', gen_salt('bf'))
    # podemos verificarla pidiéndole a la base de datos que compruebe el hash.
    query = text("""
        SELECT id, username, role 
        FROM users 
        WHERE username = :username AND password = crypt(:password, password)
    """)
    result = await db.execute(query, {"username": credentials.username, "password": credentials.password})
    user = result.fetchone()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos"
        )

    # En un sistema real aquí se generaría un token JWT,
    # para mantenerlo simple y funcional devolvemos los datos del usuario.
    return {
        "success": True,
        "token": "simulated_jwt_token_for_now",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "role": user.role
        }
    }
