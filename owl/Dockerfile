FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ /app/app/

# Idle container (so Héraclès can `docker exec` into it)
CMD ["tail", "-f", "/dev/null"]