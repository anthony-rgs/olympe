#!/bin/bash
echo ">>> [entrypoint] Sisyphe starting..."

# Create the script that cron will call
cat <<'EOF' > /run-script.sh
#!/bin/bash
echo "[CRON] Script started at $(date)"
docker exec olympe-heracles python3 -u /app/run_billion_club.py
EOF

chmod +x /run-script.sh

# Prepare log file
touch /var/log/cron.log
chmod 666 /var/log/cron.log

# Start cron in the background
cron

# Tail cron logs continuously
tail -f /var/log/cron.log