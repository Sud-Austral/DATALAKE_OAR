# ============================================================
# DATALAKE OAR — Dockerfile
# FastAPI + MinIO en el mismo contenedor Railway
# ============================================================
FROM python:3.12-slim

# ── System dependencies ──────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    libpq-dev \
    gcc \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── MinIO server binary ──────────────────────────────────────
RUN wget -q https://dl.min.io/server/minio/release/linux-amd64/minio \
    -O /usr/local/bin/minio \
    && chmod +x /usr/local/bin/minio

# ── Python app ───────────────────────────────────────────────
WORKDIR /app

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY .env.example .
COPY app/ ./app/
COPY frontend/ ./frontend/
COPY start.sh .
RUN chmod +x start.sh

# ── MinIO data directory ─────────────────────────────────────
RUN mkdir -p /data

# ── Variables de entorno base ────────────────────────────────
# Railway sobreescribe estas con las de Settings > Variables
ENV PORT=8000
ENV MINIO_ENDPOINT=localhost:9000
ENV MINIO_ACCESS_KEY=oar_datalake_admin
ENV MINIO_SECRET_KEY=OAR_Secret_2026_Secure
ENV MINIO_BUCKET=oar-datalake
ENV MINIO_SECURE=false

# ── Startup: MinIO primero, luego uvicorn ────────────────────
CMD ["./start.sh"]
