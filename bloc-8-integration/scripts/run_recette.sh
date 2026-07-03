#!/usr/bin/env bash
# Script de recette — vérifie l'état de tous les blocs SaaS RSE.
set -euo pipefail

BASE1="http://localhost:8000"
BASE2="http://localhost:8001"
BASE7="http://localhost:8002"
BASE3="http://localhost:8003"
DB="/data/home-mathieu/saas-rse/bloc-1-backend/data/saas_rse.db"

pass=0
fail=0

check() {
  local desc="$1" url="$2" expect="$3"
  local result
  result=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
  if [[ "$result" == "$expect" ]]; then
    echo "  ✅ $desc ($result)"
    pass=$((pass + 1))
  else
    echo "  ❌ $desc (attendu $expect, obtenu $result)"
    fail=$((fail + 1))
  fi
}

db_count() {
  python3 - "$DB" "$1" << 'PYEOF'
import sqlite3, sys
try:
    conn = sqlite3.connect(sys.argv[1])
    cur = conn.cursor()
    cur.execute(sys.argv[2])
    print(cur.fetchone()[0])
except Exception:
    print("?")
PYEOF
}

echo ""
echo "=== SaaS RSE — Recette Phase A ==="
echo "$(date '+%Y-%m-%d %H:%M:%S')"
echo ""

echo "[ Bloc 1 — Backend API ]"
check "Health"        "$BASE1/api/v1/posts"           200
check "Personas"      "$BASE1/api/v1/personas"        200
check "Plannings"     "$BASE1/api/v1/plannings"       200
check "Tasks pending" "$BASE1/api/v1/tasks/pending"   200
check "Selectors"     "$BASE1/api/v1/selectors/latest" 200

echo ""
echo "[ Bloc 2 — GrilledMe ]"
grille=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE2/api/v1/grillme/sessions" \
  -H "Content-Type: application/json" -d '{"bu":"noisyless"}' 2>/dev/null || echo "000")
if [[ "$grille" == "201" ]]; then
  echo "  ✅ Session GrilledMe créée (201)"
  pass=$((pass + 1))
else
  echo "  ❌ GrilledMe session ($grille)"
  fail=$((fail + 1))
fi

echo ""
echo "[ Bloc 7 — Résilience + Queue ]"
check "Health"      "$BASE7/healthz"            200
check "Ready"       "$BASE7/readyz"             200
check "Queue stats" "$BASE7/api/v1/queue/stats" 200

echo ""
echo "[ Bloc 3 — Génération ]"
check "Health" "$BASE3/healthz" 200

echo ""
echo "[ Métriques BDD ]"
if [[ -f "$DB" ]]; then
  personas=$(db_count "SELECT COUNT(*) FROM personas")
  total=$(db_count "SELECT COUNT(*) FROM posts")
  published=$(db_count "SELECT COUNT(*) FROM posts WHERE status='published'")
  failed=$(db_count "SELECT COUNT(*) FROM posts WHERE status='failed'")
  echo "  📊 Personas    : $personas"
  echo "  📊 Posts total : $total"
  echo "  📊 Published   : $published"
  echo "  📊 Failed      : $failed"
  if [[ "$published" =~ ^[0-9]+$ ]] && [[ "$failed" =~ ^[0-9]+$ ]]; then
    denom=$((published + failed))
    if [[ $denom -gt 0 ]]; then
      ratio=$(python3 -c "print(f'{$failed * 100 / $denom:.1f}')")
      echo "  📊 Taux échec  : ${ratio}%"
      gate=$(python3 -c "print('ok' if $failed * 100 / $denom < 5 else 'ko')")
      if [[ "$gate" == "ok" ]]; then
        echo "  ✅ Taux échec < 5% — Gate S5 OK"
        pass=$((pass + 1))
      else
        echo "  ❌ Taux échec >= 5% — Gate S5 KO"
        fail=$((fail + 1))
      fi
    fi
    if [[ $published -ge 30 ]]; then
      echo "  🎉 30+ posts publiés — Objectif Phase A atteint !"
    else
      echo "  ⏳ $published/30 posts publiés — Phase A en cours"
    fi
  fi
else
  echo "  ⚠️  DB introuvable : $DB"
fi

echo ""
echo "=== Résumé : $pass ✅  $fail ❌ ==="
if [[ $fail -eq 0 ]]; then
  echo "🎉 Tous les checks passent !"
  exit 0
else
  echo "⚠️  $fail check(s) en échec."
  exit 1
fi
