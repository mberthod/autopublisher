#!/usr/bin/env bash
# Remet la base de données à zéro (DESTRUCTIF — uniquement pour tests).
set -euo pipefail

DB_PATH="/data/home-mathieu/saas-rse/bloc-1-backend/data/saas_rse.db"

echo "⚠️  Suppression de la DB : $DB_PATH"
read -p "Confirmer ? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Annulé."
  exit 0
fi

rm -f "$DB_PATH"
echo "✅ DB supprimée."

echo "Redémarrage du backend pour recréer les tables..."
pkill -f "uvicorn app.main.*8000" || true
sleep 1
cd /data/home-mathieu/saas-rse/bloc-1-backend
nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/bloc1.log 2>&1 &
sleep 3
curl -s http://localhost:8000/api/v1/posts > /dev/null && echo "✅ Backend relancé."
