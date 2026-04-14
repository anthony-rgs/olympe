#!/bin/sh
set -e

BGUTIL_SERVER=$(python3 -c "import bgutil_ytdlp_pot_provider, os; print(os.path.join(os.path.dirname(bgutil_ytdlp_pot_provider.__file__), 'server.js'))")
echo "[entrypoint] Starting bgutil PO token server: $BGUTIL_SERVER"
node "$BGUTIL_SERVER" &

exec uvicorn app.main:app \
  --host "${UVICORN_HOST}" \
  --port "${UVICORN_PORT}" \
  --proxy-headers \
  --forwarded-allow-ips='*' \
  --log-level "${UVICORN_LOG_LEVEL}"
