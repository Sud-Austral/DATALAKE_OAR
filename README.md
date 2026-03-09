# Datalake OAR

Railway data lake para almacenamiento y gestión de activos de datos: **APIs, CSV, GeoJSON, Shapefile y PDF**.

## Stack

| Componente | Tecnología |
|---|---|
| Backend | FastAPI (Python 3.12) |
| Object Storage | MinIO (S3-compatible) |
| Database | PostgreSQL 16 (instancia externa) |
| Orquestación | Docker Compose |

## Estructura

```
DATALAKE_OAR/
├── DATABASE/
│   ├── db.sql        ← Schema completo (7 tablas)
│   └── init.sql      ← Bootstrap con datos iniciales
├── app/
│   ├── main.py       ← FastAPI entry point
│   └── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Quickstart

```bash
# 1. Configurar variables de entorno
cp .env.example .env
# Editar .env: DATABASE_URL, MINIO_ACCESS_KEY, MINIO_SECRET_KEY

# 2. Aplicar schema en la DB externa
psql $DATABASE_URL -f DATABASE/db.sql

# 3. Levantar servicios
docker compose up -d

# 4. Verificar
curl http://localhost:8000/health
```

## Servicios

| Servicio | URL |
|---|---|
| API Docs (Swagger) | http://localhost:8000/api/docs |
| MinIO Console | http://localhost:9001 |

## Schema de Base de Datos

| Tabla | Descripción |
|---|---|
| `users` | Usuarios con roles: `admin`, `editor`, `viewer` |
| `datasets` | Agrupación lógica de activos de datos |
| `files` | Registro de archivos físicos en MinIO |
| `api_ingestions` | Historial de pulls desde APIs externas |
| `tags` | Clasificación semántica de datasets |
| `dataset_tags` | Relación N:M datasets ↔ tags |
| `audit_log` | Trazabilidad de operaciones por usuario |

## Variables de Entorno

| Variable | Descripción |
|---|---|
| `DATABASE_URL` | Connection string PostgreSQL externo |
| `MINIO_ACCESS_KEY` | Usuario MinIO |
| `MINIO_SECRET_KEY` | Contraseña MinIO |
| `MINIO_BUCKET` | Bucket principal (default: `oar-datalake`) |
| `SECRET_KEY` | Clave JWT para autenticación |
