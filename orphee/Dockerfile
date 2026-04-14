FROM python:3.11-slim

WORKDIR /app

# Python runtime flags
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1

# ffmpeg + curl + unzip + Node.js
RUN apt-get update && apt-get install -y --no-install-recommends \
  ffmpeg \
  curl \
  unzip \
  && curl -fsSL https://github.com/denoland/deno/releases/latest/download/deno-x86_64-unknown-linux-gnu.zip -o /tmp/deno.zip \
  && unzip /tmp/deno.zip -d /usr/local/bin \
  && rm /tmp/deno.zip \
  && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
  && apt-get install -y nodejs \
  && rm -rf /var/lib/apt/lists/*

# Dépendances Python (dont bgutil-ytdlp-pot-provider)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installe les dépendances Node.js du serveur bgutil (server.js dans un sous-dossier)
RUN BGUTIL_SERVER=$(find /usr/local/lib/python3.11/site-packages/bgutil_ytdlp_pot_provider -name "server.js" | head -1) \
  && if [ -n "$BGUTIL_SERVER" ]; then \
       npm install --prefix "$(dirname $BGUTIL_SERVER)" --omit=dev; \
     else \
       echo "bgutil server.js not found, skipping npm install"; \
     fi

# Code applicatif
COPY app/ /app/app/
COPY fonts/ /app/fonts/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENV UVICORN_HOST=0.0.0.0 \
  UVICORN_PORT=8000 \
  UVICORN_LOG_LEVEL=info

CMD ["/entrypoint.sh"]
