#!/bin/sh
set -e

BGUTIL_DIR=$(pip show bgutil-ytdlp-pot-provider | grep ^Location | cut -d' ' -f2)/bgutil_ytdlp_pot_provider
BGUTIL_SERVER="$BGUTIL_DIR/server.js"
echo "[entrypoint] Starting bgutil PO token server: $BGUTIL_SERVER"
node "$BGUTIL_SERVER" &

exec uvicorn app.main:app \
  --host "${UVICORN_HOST}" \
  --port "${UVICORN_PORT}" \
  --proxy-headers \
  --forwarded-allow-ips='*' \
  --log-level "${UVICORN_LOG_LEVEL}"
