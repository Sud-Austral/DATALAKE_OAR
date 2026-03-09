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

# Montar Frontend Estático
# Creamos la ruta física relativa a este archivo
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(frontend_path, "index.html"))

app.mount("/", StaticFiles(directory=frontend_path), name="static")

from app.routers import dashboard
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
async def health():
    """Healthcheck endpoint."""
    return {"status": "ok", "service": "oar-datalake"}


# Routers (a implementar)
# from routers import users, datasets, files, ingestions
# app.include_router(users.router,     prefix="/api/users",      tags=["users"])
# app.include_router(datasets.router,  prefix="/api/datasets",   tags=["datasets"])
# app.include_router(files.router,     prefix="/api/files",      tags=["files"])
# app.include_router(ingestions.router,prefix="/api/ingestions", tags=["ingestions"])
