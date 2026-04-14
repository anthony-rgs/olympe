#!/bin/sh
set -e

BGUTIL_SERVER=$(find /usr/local/lib/python3.11/site-packages/bgutil_ytdlp_pot_provider -name "server.js" 2>/dev/null | head -1)

if [ -n "$BGUTIL_SERVER" ]; then
  echo "[entrypoint] Starting bgutil PO token server: $BGUTIL_SERVER"
  node "$BGUTIL_SERVER" &
else
  echo "[entrypoint] bgutil server.js not found, PO token auto-generation disabled"
fi

exec uvicorn app.main:app \
  --host "${UVICORN_HOST}" \
  --port "${UVICORN_PORT}" \
  --proxy-headers \
  --forwarded-allow-ips='*' \
  --log-level "${UVICORN_LOG_LEVEL}"
