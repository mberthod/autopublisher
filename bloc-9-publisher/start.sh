#!/bin/bash
# Démarre le worker de publication serveur en arrière-plan.
cd /data/home-mathieu/saas-rse/bloc-9-publisher || exit 1
# Charge les secrets (Unipile, etc.) depuis .env non versionné
[ -f .env ] && set -a && . ./.env && set +a
pkill -f 'bloc-9-publisher.*worker.py' 2>/dev/null
sleep 1
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}" \
POLL_INTERVAL="${POLL_INTERVAL:-60}" \
nohup .venv/bin/python worker.py > /tmp/bloc9.log 2>&1 &
disown
sleep 3
echo "worker lancé (PID $(pgrep -f 'bloc-9-publisher.*worker.py' | head -1))"
tail -3 /tmp/bloc9.log 2>/dev/null
