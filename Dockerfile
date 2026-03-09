# ============================================================
# DATALAKE OAR — Dockerfile
# Python 3.12 + FastAPI + Geospatial dependencies
# ============================================================
FROM python:3.12-slim

# System dependencies (GDAL for geospatial formats)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code y configuración base
COPY .env.example .
COPY app/ ./app/
COPY frontend/ ./frontend/

# Railway utiliza la variable PORT. Si no existe, usamos 8000.
ENV PORT=8000

# Ejecutar usando la variable de entorno PORT
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
