from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import logging
from dotenv import load_dotenv

# Criterio Senior: Cargar .env prioritario, .env.example como fallback
if os.path.exists(".env"):
    load_dotenv(".env")
elif os.path.exists(".env.example"):
    load_dotenv(".env.example")
    logging.info("Utilizando .env.example como configuración base.")

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

# --- CONFIGURACIÓN DE RUTAS ---

# 1. Importar routers
from app.routers import dashboard, auth, datasets, files

# 2. Registrar API Routers PRIMERO (tienen prioridad sobre estáticos)
app.include_router(auth.router,      prefix="/api/auth",      tags=["auth"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(datasets.router,  prefix="/api/datasets",  tags=["datasets"])
app.include_router(files.router,     prefix="/api/files",     tags=["files"])

@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "service": "oar-datalake"}

# 3. Configurar Frontend
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

# Ruta raíz explícita para el index.html
@app.get("/")
async def read_index():
    return FileResponse(os.path.join(frontend_path, "index.html"))

# Montar el resto de la carpeta frontend en la raíz "/" 
# Esto resuelve /css/... y /js/... automáticamente
app.mount("/", StaticFiles(directory=frontend_path), name="static")
