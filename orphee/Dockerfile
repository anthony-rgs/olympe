FROM python:3.11-slim

WORKDIR /app

# Python runtime flags
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1

# ffmpeg requis pour le traitement vidéo
RUN apt-get update && apt-get install -y --no-install-recommends \
  ffmpeg \
  curl \
  && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
  && apt-get install -y nodejs \
  && npm install -g yt-dlp-utils \
  && rm -rf /var/lib/apt/lists/*

# Dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code applicatif
COPY app/ /app/app/
COPY fonts/ /app/fonts/

EXPOSE 8000

ENV UVICORN_HOST=0.0.0.0 \
  UVICORN_PORT=8000 \
  UVICORN_LOG_LEVEL=info

CMD ["sh", "-c", "uvicorn app.main:app --host ${UVICORN_HOST} --port ${UVICORN_PORT} --proxy-headers --forwarded-allow-ips='*' --log-level ${UVICORN_LOG_LEVEL}"]
