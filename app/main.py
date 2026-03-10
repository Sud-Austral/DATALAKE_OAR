"""
DATALAKE OAR — FastAPI Application Entry Point
Railway data lake: APIs, CSV, GeoJSON, Shapefile, PDF
"""
import os
import logging
from dotenv import load_dotenv

# FIX-1: Cargar entorno ANTES de cualquier import de módulos propios.
# Los módulos (database.py, storage.py) leen os.getenv() al instanciarse;
# si load_dotenv() se llama después de importarlos, las variables llegan vacías.
_env_file = ".env" if os.path.exists(".env") else (".env.example" if os.path.exists(".env.example") else None)
if _env_file:
    load_dotenv(_env_file, override=False)  # override=False: Railway Variables tienen prioridad

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s"
)
logger = logging.getLogger(__name__)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(
    title="Datalake OAR",
    description="Railway data lake — APIs, CSV, GeoJSON, Shapefile, PDF",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    # allow_credentials NO puede usarse con allow_origins=["*"]
    # Se elimina para evitar error de arranque en starlette >= 0.21
)

# FIX-2: Los routers se importan DESPUÉS de load_dotenv() para que puedan
# leer variables de entorno correctamente durante sus propias importaciones.
from app.routers import dashboard, auth, datasets, files

app.include_router(auth.router,      prefix="/api/auth",      tags=["auth"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(datasets.router,  prefix="/api/datasets",  tags=["datasets"])
app.include_router(files.router,     prefix="/api/files",     tags=["files"])

@app.get("/health", tags=["system"])
async def health():
    """Healthcheck para Railway. Confirma que la app arrancó correctamente."""
    return {"status": "ok", "service": "oar-datalake", "version": "0.1.0"}

# FIX-3: Resolver el path del frontend de forma robusta usando __file__
# independientemente del directorio de trabajo actual (cwd) del proceso.
_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_path = os.path.join(_base_dir, "frontend")

@app.get("/")
async def read_index():
    """Sirve el frontend SPA."""
    return FileResponse(os.path.join(frontend_path, "index.html"))

# FIX-4: StaticFiles SIEMPRE al final. FastAPI registra rutas en orden;
# el mount "/" actúa como catch-all y bloquea rutas posteriores.
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")
