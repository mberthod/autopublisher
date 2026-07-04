#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="/tmp"

start_bloc() {
  local name=$1
  local dir=$2
  local port=$3
  local cmd=$4

  echo "Starting $name on port $port..."
  cd "$SCRIPT_DIR/$dir"
  nohup bash -c "$cmd" > "$LOG_DIR/${name}.log" 2>&1 &
  cd "$SCRIPT_DIR"
}

# Kill any existing instances
pkill -f "uvicorn app.main:app.*8000" 2>/dev/null || true
pkill -f "uvicorn app.main:app.*8001" 2>/dev/null || true
pkill -f "uvicorn app.main:app.*8002" 2>/dev/null || true
pkill -f "uvicorn app.main:app.*8003" 2>/dev/null || true
pkill -f "uvicorn.*8004" 2>/dev/null || true
sleep 1

start_bloc "bloc1" "bloc-1-backend"   8000 ".venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000"
start_bloc "bloc2" "bloc-2-grillme"   8001 ".venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001"
start_bloc "bloc7" "bloc-7-resilience" 8002 ".venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8002"
start_bloc "bloc3" "bloc-3-generation" 8003 ".venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8003"
start_bloc "bloc4" "bloc-4-carrousels" 8004 "python3 api_server.py"

sleep 3

echo ""
echo "=== Services status ==="
for port in 8000 8001 8002 8003 8004; do
  if ss -tlnp | grep -q ":$port "; then
    echo "  ✓ Port $port UP"
  else
    echo "  ✗ Port $port DOWN — check /tmp/bloc*.log"
  fi
done

echo ""
echo "=== Next steps ==="
echo "  Dashboard : cd bloc-6-dashboard && npm run dev"
echo "  Extension : load unpacked from bloc-5-extension/ in chrome://extensions"
echo ""
echo "  Logs : tail -f /tmp/bloc1.log /tmp/bloc2.log /tmp/bloc3.log"
