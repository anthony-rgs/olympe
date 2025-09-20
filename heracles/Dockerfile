FROM python:3.11

# Set the main working directory
WORKDIR /app

# Copy project files into the container
COPY . /app

# System dependencies required by Playwright/Chromium + docker exec + bash
RUN apt-get update && apt-get install -y \
  git \
  bash \
  ca-certificates \
  curl \
  gnupg \
  libnss3 \
  libatk-bridge2.0-0 \
  libx11-xcb1 \
  libgtk-3-0 \
  libxcomposite1 \
  libxdamage1 \
  libgbm1 \
  libasound2 \
  libatk1.0-0 \
  libcups2 \
  libdrm2 \
  libdbus-1-3 \
  libxrandr2 \
  libnspr4 \
  fonts-liberation \
  xdg-utils \
  && install -m 0755 -d /etc/apt/keyrings \
  && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
  && chmod a+r /etc/apt/keyrings/docker.gpg \
  && . /etc/os-release \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian ${VERSION_CODENAME} stable" > /etc/apt/sources.list.d/docker.list \
  && apt-get update \
  && apt-get install -y docker-ce-cli \
  && rm -rf /var/lib/apt/lists/*
  
# Copy the entry script and make it executable
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Passive container: run scripts manually via the entrypoint
CMD ["/app/entrypoint.sh"]