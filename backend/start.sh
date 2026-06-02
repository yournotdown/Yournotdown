#!/usr/bin/env sh
set -eu

PORT="${PORT:-8001}"

echo "[yournotdown] Starting uvicorn on 0.0.0.0:${PORT}"

exec uvicorn server:app \
    --host 0.0.0.0 \
    --port "${PORT}" \
    --workers 1 \
    --proxy-headers \
    --forwarded-allow-ips="*" \
    --timeout-keep-alive 75
