#!/bin/bash
set -e

echo "=== OAR Datalake Startup ==="

export MINIO_ROOT_USER="${MINIO_ACCESS_KEY:-oar_datalake_admin}"
export MINIO_ROOT_PASSWORD="${MINIO_SECRET_KEY:-OAR_Secret_2026_Secure}"

# ── Función para arrancar MinIO ───────────────────────────────────────
start_minio() {
    echo "[MinIO] Starting on :9000..."
    minio server /data --address ":9000" --console-address ":9001" &
    MINIO_PID=$!
    echo "[MinIO] PID: $MINIO_PID"
}

# ── Watchdog de MinIO ─────────────────────────────────────────────────
watch_minio() {
    while true; do
        sleep 15
        if ! kill -0 "$MINIO_PID" 2>/dev/null; then
            echo "[MinIO] Process died! Restarting..."
            start_minio
        fi
    done
}

# ── Arrancar MinIO y esperar a que esté listo ─────────────────────────
start_minio

echo "[MinIO] Waiting for readiness..."
for i in $(seq 1 20); do
    if curl -sf http://localhost:9000/minio/health/live > /dev/null 2>&1; then
        echo "[MinIO] Ready!"
        break
    fi
    if [ "$i" -eq 20 ]; then
        echo "[MinIO] WARNING: MinIO did not respond after 40s. Starting app anyway..."
    fi
    sleep 2
done

# ── Watchdog en background ────────────────────────────────────────────
watch_minio &

# ── FastAPI (foreground — Railway monitorea este proceso) ─────────────
echo "[FastAPI] Starting on :${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
