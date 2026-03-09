"""
DATALAKE OAR — FastAPI Application Entry Point
Railway data lake: APIs, CSV, GeoJSON, Shapefile, PDF
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

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
)

# BUG FIX #1: Los routers deben registrarse ANTES de montar los estáticos.
# StaticFiles actúa como catch-all y "secuestra" cualquier ruta /api/* si va primero.
from app.routers import dashboard, auth, datasets, files

app.include_router(auth.router,      prefix="/api/auth",      tags=["auth"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(datasets.router,  prefix="/api/datasets",  tags=["datasets"])
app.include_router(files.router,     prefix="/api/files",     tags=["files"])

# BUG FIX #2: El endpoint /health estaba huérfano (sin decorador) tras las ediciones
# anteriores. Se restaura correctamente.
@app.get("/health", tags=["system"])
async def health():
    """Healthcheck endpoint para Railway."""
    return {"status": "ok", "service": "oar-datalake", "version": "0.1.0"}

# BUG FIX #3: La ruta raíz "/" debe declararse ANTES de montar StaticFiles,
# porque StaticFiles registrado en "/" absorbe todas las rutas no definidas aún.
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(frontend_path, "index.html"))

# StaticFiles al final — solo sirve lo que no capturaron las rutas anteriores
app.mount("/static", StaticFiles(directory=frontend_path), name="static")
