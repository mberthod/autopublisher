# Bloc 7 — Résilience (queue + retry + Telegram)

Queue SQLite persistante avec retry exponentiel ([1s, 5s, 30s] ±20% jitter) et alertes Telegram après 3 échecs.

## Setup

```bash
cd /data/home-mathieu/saas-rse/bloc-7-resilience
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# Édite .env : TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
```

## Lancer

```bash
# Terminal 1 — API
uvicorn app.main:app --reload --port 8002

# Terminal 2 — Worker (process séparé)
python -m app.workers.queue_worker
```

## Tests

```bash
pytest -v
pytest -v --cov=app
```

## Usage depuis un autre bloc

```python
from app.services.queue_service import enqueue_task

# Depuis n'importe quel service qui a accès à la session DB :
enqueue_task(db, task_type="publish_post", payload={"post_id": "uuid"})
enqueue_task(db, task_type="generate_text", payload={"post_id": "uuid", "persona_id": "uuid"})
enqueue_task(db, task_type="generate_image", payload={"post_id": "uuid", "prompt": "..."})
```

## Comportement

- **Retry** : 1er échec → retry après 1s ±0.2s ; 2e → 5s ±1s ; 3e → 30s ±6s
- **Après 3 échecs** : tâche en `failed` + alerte Telegram
- **Recovery au démarrage** : toute tâche en `running` depuis >5min → remise en `pending`
- **Worker** : poll toutes les 5s, process 1 tâche par iteration

## API

| Endpoint | Description |
|----------|-------------|
| GET /healthz | Liveness |
| GET /api/v1/queue/stats | Stats par statut |
| POST /api/v1/queue/tasks | Enqueue une tâche |
