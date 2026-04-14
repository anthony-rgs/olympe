#!/bin/sh
set -e

exec uvicorn app.main:app \
  --host "${UVICORN_HOST}" \
  --port "${UVICORN_PORT}" \
  --proxy-headers \
  --forwarded-allow-ips='*' \
  --log-level "${UVICORN_LOG_LEVEL}"
