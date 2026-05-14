"""
DATALAKE OAR — Router: Config / Administración del Sistema
Gestión de usuarios, roles y parámetros del sistema.
Solo accesible para usuarios con rol 'admin'.
"""
import uuid
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db
from app.routers.auth import verify_token

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Guard de administrador ──────────────────────────────────────────────
def _require_admin(current_user: dict = Depends(verify_token)) -> dict:
    """Dependency que fuerza rol 'admin'. Lanza 403 si no lo tiene."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador para esta operación.",
        )
    return current_user


# ── Serialización ───────────────────────────────────────────────────────
def _serialize(row: dict) -> dict:
    result = {}
    for k, v in row.items():
        if k == "password":          # nunca exponer el hash
            continue
        if isinstance(v, uuid.UUID):
            result[k] = str(v)
        elif hasattr(v, "isoformat"):
            result[k] = v.isoformat()
        else:
            result[k] = v
    return result


# ── Modelos ─────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: str = "viewer"

    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("admin", "editor", "viewer"):
            raise ValueError("role debe ser admin, editor o viewer")
        return v


class UserUpdate(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None      # si se envía, se re-hashea con pgcrypto


# ══════════════════════════════════════════════════════════════════════════
# USUARIOS
# ══════════════════════════════════════════════════════════════════════════

@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(_require_admin),
):
    """Lista todos los usuarios del sistema (sin exponer hashes de contraseña)."""
    result = await db.execute(
        text(
            """SELECT id, username, email, role, is_active, created_at, updated_at
               FROM users
               ORDER BY created_at DESC"""
        )
    )
    return [_serialize(dict(row)) for row in result.mappings().all()]


@router.post("/users", status_code=201)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(_require_admin),
):
    """Crea un nuevo usuario con contraseña hasheada por pgcrypto."""
    if body.role not in ("admin", "editor", "viewer"):
        raise HTTPException(status_code=400, detail="role debe ser admin, editor o viewer")
    try:
        result = await db.execute(
            text(
                """INSERT INTO users (username, email, password, role)
                   VALUES (:username, :email, crypt(:password, gen_salt('bf')), :role)
                   RETURNING id, created_at"""
            ),
            {
                "username": body.username.strip(),
                "email":    body.email.strip().lower(),
                "password": body.password,
                "role":     body.role,
            },
        )
        row = result.fetchone()
        new_id = str(row[0])

        # Audit
        await db.execute(
            text(
                """INSERT INTO audit_log (user_id, action, entity, entity_id, details)
                   VALUES (:admin_id, 'CREATE_USER', 'users', :new_id, CAST(:details AS JSONB))"""
            ),
            {
                "admin_id": uuid.UUID(admin["id"]),
                "new_id":   uuid.UUID(new_id),
                "details":  json.dumps({"username": body.username, "role": body.role}),
            },
        )
        await db.commit()
        return {"id": new_id, "status": "created"}

    except Exception as e:
        await db.rollback()
        err = str(e)
        if "unique" in err.lower() or "duplicate" in err.lower():
            raise HTTPException(status_code=409, detail="El usuario o email ya existe.")
        logger.error(f"Error creando usuario: {e}")
        raise HTTPException(status_code=500, detail=err)


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(_require_admin),
):
    """Actualiza email, rol, estado activo o contraseña de un usuario."""
    if body.role and body.role not in ("admin", "editor", "viewer"):
        raise HTTPException(status_code=400, detail="role debe ser admin, editor o viewer")

    # Construir set dinámico
    sets = []
    params: dict = {"id": uuid.UUID(user_id)}

    if body.email    is not None:
        sets.append("email = :email"); params["email"] = body.email.strip().lower()
    if body.role     is not None:
        sets.append("role = :role");   params["role"]  = body.role
    if body.is_active is not None:
        sets.append("is_active = :active"); params["active"] = body.is_active
    if body.password is not None:
        sets.append("password = crypt(:pw, gen_salt('bf'))"); params["pw"] = body.password

    if not sets:
        raise HTTPException(status_code=400, detail="Sin campos para actualizar")

    sets.append("updated_at = NOW()")

    try:
        result = await db.execute(
            text(f"UPDATE users SET {', '.join(sets)} WHERE id = :id RETURNING id"),
            params,
        )
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        await db.execute(
            text(
                """INSERT INTO audit_log (user_id, action, entity, entity_id, details)
                   VALUES (:admin_id, 'UPDATE_USER', 'users', :uid, CAST(:details AS JSONB))"""
            ),
            {
                "admin_id": uuid.UUID(admin["id"]),
                "uid":      uuid.UUID(user_id),
                "details":  json.dumps({k: v for k, v in body.model_dump().items()
                                        if v is not None and k != "password"}),
            },
        )
        await db.commit()
        return {"status": "updated"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(_require_admin),
):
    """Elimina un usuario. No puede eliminarse a sí mismo."""
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta.")

    result = await db.execute(
        text("DELETE FROM users WHERE id = :id RETURNING id"),
        {"id": uuid.UUID(user_id)},
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    await db.execute(
        text(
            """INSERT INTO audit_log (user_id, action, entity, entity_id, details)
               VALUES (:admin_id, 'DELETE_USER', 'users', :uid, '{}')"""
        ),
        {"admin_id": uuid.UUID(admin["id"]), "uid": uuid.UUID(user_id)},
    )
    await db.commit()


# ══════════════════════════════════════════════════════════════════════════
# ESTADÍSTICAS DEL SISTEMA (para panel de config)
# ══════════════════════════════════════════════════════════════════════════

@router.get("/system-info")
async def system_info(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(verify_token),          # cualquier usuario autenticado
):
    """
    Devuelve métricas generales del sistema para el panel de configuración:
    conteo de usuarios por rol, ingestas por estado, etc.
    """
    try:
        users_result = await db.execute(
            text(
                """SELECT role, COUNT(*) AS cnt, 
                          SUM(CASE WHEN is_active THEN 1 ELSE 0 END) AS active
                   FROM users GROUP BY role"""
            )
        )
        users_by_role = [dict(r) for r in users_result.mappings().all()]

        ing_result = await db.execute(
            text(
                """SELECT status, COUNT(*) AS cnt
                   FROM api_ingestions GROUP BY status"""
            )
        )
        ingestions_by_status = [dict(r) for r in ing_result.mappings().all()]

        audit_result = await db.execute(
            text(
                """SELECT COUNT(*) AS total,
                          MAX(created_at) AS last_activity
                   FROM audit_log"""
            )
        )
        audit_row = audit_result.fetchone()

        return {
            "users_by_role":       users_by_role,
            "ingestions_by_status": ingestions_by_status,
            "audit_total":         audit_row[0] if audit_row else 0,
            "last_activity":       audit_row[1].isoformat() if audit_row and audit_row[1] else None,
        }
    except Exception as e:
        logger.error(f"Error en system_info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit-log")
async def audit_log(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(_require_admin),
):
    """Devuelve las últimas entradas del audit log (máx 200)."""
    limit = min(limit, 200)
    result = await db.execute(
        text(
            """SELECT al.id, al.action, al.entity, al.entity_id,
                      al.details, al.ip_address, al.created_at,
                      u.username
               FROM audit_log al
               LEFT JOIN users u ON al.user_id = u.id
               ORDER BY al.created_at DESC
               LIMIT :limit"""
        ),
        {"limit": limit},
    )
    rows = result.mappings().all()
    return [_serialize(dict(r)) for r in rows]
