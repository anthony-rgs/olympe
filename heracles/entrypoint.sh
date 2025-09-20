#!/bin/bash

set -e  # exit immediately if a command fails

echo "📦 Waiting for Artemis code..."
count=0
while [ ! -f /code-artemis/requirements.txt ]; do
  echo "⏳ requirements.txt not found, waiting... ($count/30)"
  sleep 1
  count=$((count + 1))
  if [ "$count" -ge 30 ]; then
    echo "❌ requirements.txt still not found after 30 seconds"
    exit 1
  fi
done

echo "📦 requirements.txt detected, installing Python dependencies..."
python -m pip install --no-cache-dir -r /code-artemis/requirements.txt

echo "🧩 Installing Chromium via Playwright..."
python -m playwright install chromium

echo "✅ Installation completed"
sleep infinity