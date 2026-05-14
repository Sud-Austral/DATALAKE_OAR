"""
DATALAKE OAR — Router: API Ingestions
Permite crear, listar, ejecutar y monitorear ingestas desde APIs externas.
Cada ingesta extrae datos de un endpoint HTTP y los almacena como archivo
en MinIO, registrando el resultado en PostgreSQL.
"""
import uuid
import json
import logging
import httpx
from datetime import datetime, timezone
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db
from app.routers.auth import verify_token
from app.utils.storage import storage

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Constantes ─────────────────────────────────────────────────────────
_TIMEOUT_S = 60        # Timeout HTTP para llamadas a APIs externas
_MAX_RESP_MB = 50      # Límite de respuesta (50 MB)


# ── Modelos Pydantic ────────────────────────────────────────────────────
class IngestionCreate(BaseModel):
    dataset_id: Optional[str] = None
    source: str                          # Nombre descriptivo del origen (ej: "INDEC API")
    endpoint: str                        # URL del endpoint externo
    method: str = "GET"                  # GET | POST | PUT
    parameters: dict = {}               # Query params o body payload
    headers: dict = {}                  # Headers personalizados

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        v = v.upper()
        if v not in ("GET", "POST", "PUT"):
            raise ValueError("method debe ser GET, POST o PUT")
        return v


class IngestionUpdate(BaseModel):
    source: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    parameters: Optional[dict] = None
    headers: Optional[dict] = None
    dataset_id: Optional[str] = None


# ── Serialización ───────────────────────────────────────────────────────
def _serialize(row: dict) -> dict:
    """Convierte UUID y datetime a tipos JSON-serializables."""
    result = {}
    for k, v in row.items():
        if isinstance(v, uuid.UUID):
            result[k] = str(v)
        elif isinstance(v, datetime):
            result[k] = v.isoformat()
        elif isinstance(v, dict):
            result[k] = v
        else:
            result[k] = v
    return result


# ── Ejecución real de la ingesta (background task) ─────────────────────
async def _execute_ingestion(ingestion_id: str, user_id: str):
    """
    Tarea background: llama al endpoint externo, almacena la respuesta
    en MinIO y actualiza el estado en PostgreSQL.
    """
    from app.database import get_db as _get_db_factory

    # Necesitamos una sesión independiente porque esta función corre
    # en background, fuera del ciclo de vida del request original.
    from app.database import _get_engine
    _, factory = _get_engine()

    async with factory() as db:
        try:
            # 1. Leer configuración de la ingesta
            result = await db.execute(
                text(
                    "SELECT * FROM api_ingestions WHERE id = :id"
                ),
                {"id": uuid.UUID(ingestion_id)},
            )
            row = result.mappings().fetchone()
            if not row:
                logger.error(f"Ingesta {ingestion_id} no encontrada en BD.")
                return

            # 2. Marcar como 'running'
            started_at = datetime.now(timezone.utc)
            await db.execute(
                text(
                    """UPDATE api_ingestions
                       SET status = 'running', started_at = :ts, error_message = NULL
                       WHERE id = :id"""
                ),
                {"ts": started_at, "id": uuid.UUID(ingestion_id)},
            )
            await db.commit()

            # 3. Ejecutar la llamada HTTP
            method   = (row["method"] or "GET").upper()
            endpoint = row["endpoint"]
            params   = row["parameters"] or {}
            headers  = dict(row["headers"] or {})
            headers.setdefault("Accept", "application/json")

            async with httpx.AsyncClient(timeout=_TIMEOUT_S, follow_redirects=True) as client:
                if method == "GET":
                    resp = await client.get(endpoint, params=params, headers=headers)
                elif method == "POST":
                    resp = await client.post(endpoint, json=params, headers=headers)
                else:  # PUT
                    resp = await client.put(endpoint, json=params, headers=headers)

                resp.raise_for_status()
                content      = resp.content
                content_type = resp.headers.get("content-type", "application/octet-stream")

            # 4. Determinar extensión y nombre de objeto
            if "json" in content_type:
                ext = "json"
            elif "csv" in content_type or endpoint.endswith(".csv"):
                ext = "csv"
            elif "xml" in content_type:
                ext = "xml"
            else:
                ext = "bin"

            source_slug = (row["source"] or "ingesta").lower().replace(" ", "_")[:40]
            ts_str      = started_at.strftime("%Y%m%d_%H%M%S")
            obj_name    = f"ingestions/{ingestion_id}/{source_slug}_{ts_str}.{ext}"

            # 5. Subir a MinIO
            storage_path = storage.upload_file(
                file_content=content,
                object_name=obj_name,
                content_type=content_type,
            )

            # 6. Actualizar estado a 'success'
            finished_at = datetime.now(timezone.utc)
            await db.execute(
                text(
                    """UPDATE api_ingestions
                       SET status = 'success',
                           finished_at = :ts,
                           file_path = :fp
                       WHERE id = :id"""
                ),
                {
                    "ts": finished_at,
                    "fp": storage_path,
                    "id": uuid.UUID(ingestion_id),
                },
            )

            # 7. Audit log
            await db.execute(
                text(
                    """INSERT INTO audit_log (user_id, action, entity, entity_id, details)
                       VALUES (:user, 'RUN_INGESTION', 'api_ingestions', :eid,
                               CAST(:details AS JSONB))"""
                ),
                {
                    "user":    uuid.UUID(user_id),
                    "eid":     uuid.UUID(ingestion_id),
                    "details": json.dumps(
                        {
                            "source":   row["source"],
                            "endpoint": row["endpoint"],
                            "status":   "success",
                            "bytes":    len(content),
                            "file":     storage_path,
                        }
                    ),
                },
            )
            await db.commit()
            logger.info(f"Ingesta {ingestion_id} exitosa — {len(content)} bytes → {storage_path}")

        except Exception as exc:
            logger.error(f"Ingesta {ingestion_id} falló: {exc}")
            try:
                err_msg = str(exc)[:1000]
                await db.execute(
                    text(
                        """UPDATE api_ingestions
                           SET status = 'failed',
                               finished_at = :ts,
                               error_message = :err
                           WHERE id = :id"""
                    ),
                    {
                        "ts":  datetime.now(timezone.utc),
                        "err": err_msg,
                        "id":  uuid.UUID(ingestion_id),
                    },
                )
                await db.commit()
            except Exception as inner:
                logger.error(f"Error al actualizar estado de fallo: {inner}")


# ══════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════

@router.get("/")
async def list_ingestions(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(verify_token),
):
    """Lista todas las ingestas ordenadas por fecha de creación descendente."""
    result = await db.execute(
        text(
            """SELECT id, dataset_id, source, endpoint, method,
                      parameters, headers, file_path, status,
                      error_message, triggered_by, started_at,
                      finished_at, created_at
               FROM api_ingestions
               ORDER BY created_at DESC"""
        )
    )
    return [_serialize(dict(row)) for row in result.mappings().all()]


@router.post("/", status_code=201)
async def create_ingestion(
    body: IngestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_token),
):
    """Registra una nueva configuración de ingesta (no la ejecuta aún)."""
    try:
        result = await db.execute(
            text(
                """INSERT INTO api_ingestions
                       (dataset_id, source, endpoint, method, parameters, headers, triggered_by)
                   VALUES
                       (:ds_id, :source, :endpoint, :method,
                        CAST(:params AS JSONB), CAST(:headers AS JSONB), :user_id)
                   RETURNING id, created_at"""
            ),
            {
                "ds_id":    uuid.UUID(body.dataset_id) if body.dataset_id else None,
                "source":   body.source,
                "endpoint": body.endpoint,
                "method":   body.method,
                "params":   json.dumps(body.parameters),
                "headers":  json.dumps(body.headers),
                "user_id":  uuid.UUID(current_user["id"]),
            },
        )
        row = result.fetchone()
        new_id = row[0]

        await db.execute(
            text(
                """INSERT INTO audit_log (user_id, action, entity, entity_id, details)
                   VALUES (:user, 'CREATE', 'api_ingestions', :eid, CAST(:details AS JSONB))"""
            ),
            {
                "user":    uuid.UUID(current_user["id"]),
                "eid":     new_id,
                "details": json.dumps({"source": body.source, "endpoint": body.endpoint}),
            },
        )
        await db.commit()
        return {"id": str(new_id), "status": "created"}

    except Exception as e:
        await db.rollback()
        logger.error(f"Error creando ingesta: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ingestion_id}")
async def get_ingestion(
    ingestion_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(verify_token),
):
    """Devuelve el detalle de una ingesta por su ID."""
    result = await db.execute(
        text("SELECT * FROM api_ingestions WHERE id = :id"),
        {"id": uuid.UUID(ingestion_id)},
    )
    row = result.mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Ingesta no encontrada")
    return _serialize(dict(row))


@router.put("/{ingestion_id}")
async def update_ingestion(
    ingestion_id: str,
    body: IngestionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_token),
):
    """Actualiza los campos de una ingesta existente (solo si no está running)."""
    result = await db.execute(
        text("SELECT status FROM api_ingestions WHERE id = :id"),
        {"id": uuid.UUID(ingestion_id)},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Ingesta no encontrada")
    if row[0] == "running":
        raise HTTPException(status_code=409, detail="No se puede editar una ingesta en ejecución")

    updates: dict[str, Any] = {}
    if body.source     is not None: updates["source"]     = body.source
    if body.endpoint   is not None: updates["endpoint"]   = body.endpoint
    if body.method     is not None: updates["method"]     = body.method.upper()
    if body.parameters is not None: updates["parameters"] = json.dumps(body.parameters)
    if body.headers    is not None: updates["headers"]    = json.dumps(body.headers)
    if body.dataset_id is not None:
        updates["dataset_id"] = uuid.UUID(body.dataset_id) if body.dataset_id else None

    if not updates:
        raise HTTPException(status_code=400, detail="Sin campos para actualizar")

    set_clause = ", ".join(
        f"{k} = {'CAST(:' + k + ' AS JSONB)' if k in ('parameters','headers') else ':' + k}"
        for k in updates
    )
    updates["id"] = uuid.UUID(ingestion_id)

    try:
        await db.execute(
            text(f"UPDATE api_ingestions SET {set_clause} WHERE id = :id"),
            updates,
        )
        await db.commit()
        return {"status": "updated"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{ingestion_id}", status_code=204)
async def delete_ingestion(
    ingestion_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_token),
):
    """Elimina una ingesta. Requiere rol admin o editor."""
    if current_user["role"] not in ("admin", "editor"):
        raise HTTPException(status_code=403, detail="Se requiere rol admin o editor")

    result = await db.execute(
        text("DELETE FROM api_ingestions WHERE id = :id RETURNING id"),
        {"id": uuid.UUID(ingestion_id)},
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Ingesta no encontrada")
    await db.commit()


@router.post("/{ingestion_id}/run")
async def run_ingestion(
    ingestion_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_token),
):
    """
    Lanza la ejecución de una ingesta en background.
    Devuelve inmediatamente con status 'running'.
    """
    result = await db.execute(
        text("SELECT status FROM api_ingestions WHERE id = :id"),
        {"id": uuid.UUID(ingestion_id)},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Ingesta no encontrada")
    if row[0] == "running":
        raise HTTPException(status_code=409, detail="La ingesta ya está en ejecución")

    background_tasks.add_task(
        _execute_ingestion,
        ingestion_id=ingestion_id,
        user_id=current_user["id"],
    )
    return {"status": "running", "ingestion_id": ingestion_id}


@router.get("/{ingestion_id}/status")
async def ingestion_status(
    ingestion_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(verify_token),
):
    """Polling endpoint: devuelve el estado actual de una ingesta."""
    result = await db.execute(
        text(
            """SELECT id, status, error_message, file_path,
                      started_at, finished_at
               FROM api_ingestions WHERE id = :id"""
        ),
        {"id": uuid.UUID(ingestion_id)},
    )
    row = result.mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Ingesta no encontrada")
    return _serialize(dict(row))
