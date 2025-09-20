FROM python:3.11-slim

WORKDIR /app

# Python runtime flags:
# - no .pyc files
# - unbuffered stdout/stderr (better logs in Docker)
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY app/ /app/app/

# Default network port (exposed to other services / proxy)
EXPOSE 8000

# Make UVicorn flags configurable via env (easy to tweak on the server)
ENV UVICORN_HOST=0.0.0.0 \
  UVICORN_PORT=8000 \
  UVICORN_LOG_LEVEL=info

# Start API; pass proxy headers so client IP/proto are preserved behind a proxy
CMD ["sh", "-c", "uvicorn app.main:app --host ${UVICORN_HOST} --port ${UVICORN_PORT} --proxy-headers --forwarded-allow-ips='*' --log-level ${UVICORN_LOG_LEVEL}"]
