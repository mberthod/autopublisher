# Bloc 2 — GrilledMe (onboarding conversationnel multi-agents)

Agent conversationnel à 2 étages (Interrogateur + Stratège) qui produit un Persona structuré via une discussion, pas un formulaire.

## Setup

```bash
cd /data/home-mathieu/saas-rse/bloc-2-grillme

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# Édite .env et ajoute ta DEEPSEEK_API_KEY
```

## Tests (sans clé LLM — tout mocké)

```bash
pytest -v
pytest -v --cov=app
```

## Lancer le service

```bash
# Le bloc 1 doit être démarré pour que la DB existe
uvicorn app.main:app --reload --port 8001
# Swagger : http://localhost:8001/docs
```

## Test conversationnel manuel

```bash
# 1. Démarrer une session
SESSION_ID=$(curl -s -X POST http://localhost:8001/api/v1/grillme/sessions \
  -H "Content-Type: application/json" \
  -d '{"bu": "noisyless"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

echo "Session: $SESSION_ID"

# 2. Répondre à la première question
curl -s -X POST http://localhost:8001/api/v1/grillme/sessions/$SESSION_ID/messages \
  -H "Content-Type: application/json" \
  -d '{"user_message": "Je cible les propriétaires Airbnb en zone urbaine, 30-55 ans, ayant 1-5 biens"}' \
  | python3 -m json.tool

# 3. Continuer jusqu'à is_complete=true

# 4. Récupérer le Persona final
curl -s http://localhost:8001/api/v1/grillme/sessions/$SESSION_ID/persona | python3 -m json.tool
```

## Architecture

- **Agent Interrogateur** : pose des questions une par une, challenge les réponses vagues, remplit la matrice
- **Agent Stratège** : une fois la matrice complète, synthétise un Persona final avec charte de branding
- **GrilledMeSession** : table SQLite qui stocke la matrice partielle et le transcript complet
- **Shared DB** : utilise la même DB que le bloc 1 (défini dans DATABASE_URL)

## Variables d'environnement

| Variable | Valeur par défaut | Description |
|----------|------------------|-------------|
| DEEPSEEK_API_KEY | sk-placeholder | Clé API DeepSeek |
| DEEPSEEK_BASE_URL | https://api.deepseek.com/v1 | URL base DeepSeek |
| DEEPSEEK_MODEL | deepseek-chat | Modèle à utiliser |
| DATABASE_URL | sqlite:////data/...bloc-1-backend/data/saas_rse.db | DB partagée avec bloc 1 |
