# Bloc 7 — Résilience : retry, queue, alertes Telegram

> **Statut** : SPEC à implémenter par Claude Code
> **Owner** : Mathieu (revieweur), Claude Code (implémenteur)
> **Livrable** : Worker de queue avec retry exponentiel + backoff + jitter, alertes Telegram après 3 échecs

---

## 🎯 Objectif

Wrapper tous les appels critiques du backend (génération LLM, génération d'image, publication extension) dans une **queue persistante** avec :
- **3 tentatives** par tâche (retry)
- **Backoff exponentiel** : 1s, 5s, 30s entre les tentatives
- **Jitter** aléatoire ±20% sur chaque délai (anti-thundering-herd)
- **Alerte Telegram** si les 3 tentatives échouent
- **Statut final "failed"** en BDD avec error_code + error_message + screenshot

**Pas dans ce scope** (phase B+) : circuit breaker, rate limiting intelligent, fallback API officielle.

---

## 📥 Inputs

```python
# Fonction de queueing
from app.services.queue_service import enqueue_task

enqueue_task(
    task_type="publish_post",            # "publish_post" | "generate_text" | "generate_image"
    payload={"post_id": "uuid", ...},    # dict sérialisable
    max_retries=3                        # default
)
```

---

## 📤 Outputs

```python
# Worker qui process la queue
# - Sur succès: statut BDD → "success" | "published"
# - Sur échec définitif (3 retries): statut BDD → "failed" + alerte Telegram
```

---

## 🏗️ Architecture cible

```
[API endpoint] → enqueue_task(task_type, payload)
    │
    ▼
[SQLite queue table]
    - id (uuid)
    - task_type
    - payload (JSON)
    - status (pending | running | success | failed)
    - attempts (int)
    - max_retries (int)
    - next_retry_at (datetime)
    - last_error (Text)
    - created_at, updated_at, completed_at
    │
    ▼
[Worker loop (async)]
    │
    ├──► Toutes les 5s: SELECT * FROM queue WHERE status='pending' AND next_retry_at <= NOW()
    │
    ├──► Pour chaque tâche:
    │     1. UPDATE status='running'
    │     2. task = TASK_HANDLERS[task_type](payload)   # appel le bon service
    │     3. Si succès:
    │        - UPDATE status='success', completed_at=NOW()
    │        - Si task_type == "publish_post": POST callback à l'extension (via SSE ou polling inverse)
    │     4. Si échec:
    │        - attempts += 1
    │        - Si attempts < max_retries:
    │          - Calcule backoff: delays = [1, 5, 30] → backoff[attempts-1]
    │          - Ajoute jitter: delay *= random(0.8, 1.2)
    │          - UPDATE status='pending', next_retry_at=NOW()+delay
    │        - Sinon (3ème échec):
    │          - UPDATE status='failed', last_error=error_msg
    │          - Send Telegram alert
    │
    └──► Sleep 5s, recommence
```

---

## 📁 Structure de fichiers

```
/data/home-mathieu/saas-rse/
└── bloc-7-resilience/
    ├── SPEC.md                            ← ce fichier
    ├── README.md
    ├── pyproject.toml
    ├── .env.example
    ├── app/
    │   ├── __init__.py
    │   ├── main.py                        ← FastAPI app + endpoint healthz
    │   ├── config.py
    │   ├── models.py                      ← SQLAlchemy: QueueTask
    │   ├── db.py
    │   ├── workers/
    │   │   ├── __init__.py
    │   │   ├── queue_worker.py            ← boucle principale
    │   │   └── task_handlers.py           ← dispatch task_type → service
    │   ├── services/
    │   │   ├── __init__.py
    │   │   ├── queue_service.py           ← enqueue_task, claim_next_task
    │   │   ├── retry_policy.py            ← calcul backoff + jitter
    │   │   └── telegram_notifier.py       # send_telegram_alert
    │   └── api/
    │       └── queue_routes.py            # GET /api/v1/queue/stats
    └── tests/
        ├── test_retry_policy.py
        ├── test_queue_service.py
        ├── test_telegram_notifier.py
        └── test_queue_worker_e2e.py
```

---

## 🛠️ Dépendances

```toml
[project]
dependencies = [
  "fastapi>=0.115,<1",
  "uvicorn>=0.32,<1",
  "sqlalchemy>=2.0,<3",
  "pydantic>=2.9,<3",
  "pydantic-settings>=2.6,<3",
  "httpx>=0.28,<1",                       # Telegram API
  "apscheduler>=3.10,<4",                 # ou asyncio sleep loop
  "loguru>=0.7,<1",
]
```

---

## 🔑 Variables d'environnement

`.env` :
```bash
# Telegram
TELEGRAM_BOT_TOKEN=...                   # depuis @BotFather
TELEGRAM_CHAT_ID=...                     # ton chat ID (utilisateur ou groupe)

# Queue
QUEUE_POLL_INTERVAL_SECONDS=5
QUEUE_MAX_RETRIES=3
QUEUE_BACKOFF_BASE_SECONDS=1              # delays = [1, 5, 30] par défaut
QUEUE_JITTER_FACTOR=0.2                   # ±20%

# Database
DATABASE_URL=sqlite:///./data/saas_rse.db

# Logging
LOG_LEVEL=INFO
```

---

## 📝 Modèle de données

```python
# app/models.py
from sqlalchemy import Column, String, Text, DateTime, Integer, JSON
from sqlalchemy.orm import declarative_base
import uuid
from datetime import datetime

Base = declarative_base()

class QueueTask(Base):
    __tablename__ = "queue_tasks"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_type = Column(String, nullable=False)  # "publish_post" | "generate_text" | "generate_image"
    payload = Column(JSON, nullable=False)
    status = Column(String, default="pending", nullable=False)  # "pending" | "running" | "success" | "failed"
    attempts = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    next_retry_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_error = Column(Text, nullable=True)
    last_error_code = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
```

---

## 🧮 Politique de retry (critique)

```python
# app/services/retry_policy.py
import random

BACKOFF_SCHEDULE = [1, 5, 30]  # secondes, indexé par attempts (0, 1, 2)

def compute_next_retry_delay(attempts: int, jitter_factor: float = 0.2) -> int:
    """
    Returns the delay in seconds before the next retry.
    attempts: number of attempts already made (0, 1, 2, ...)
    jitter_factor: ±20% random variation
    """
    if attempts >= len(BACKOFF_SCHEDULE):
        # Should not happen if max_retries is set correctly, but fail safely
        return BACKOFF_SCHEDULE[-1]

    base_delay = BACKOFF_SCHEDULE[attempts]
    jitter = base_delay * jitter_factor
    return int(base_delay + random.uniform(-jitter, jitter))
```

**Comportement attendu** :
- 1er échec (attempts=0) → retry dans 1s ± 0.2s
- 2e échec (attempts=1) → retry dans 5s ± 1s
- 3e échec (attempts=2) → retry dans 30s ± 6s
- Si le 3e retry échoue → statut "failed" + Telegram

---

## 📱 Notification Telegram

**Message format** (à respecter) :
```
🚨 SaaS RSE — Tâche échouée définitivement

Type: {task_type}
Tentatives: {attempts}/{max_retries}
Erreur: {error_code}
Message: {error_message[:200]}

Payload: {json.dumps(payload, indent=2)[:500]}
Tâche ID: {task_id}
Échouée à: {completed_at}

→ Voir dashboard: http://192.168.0.176:8000/queue/{task_id}
```

**Endpoint Telegram** : `https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage`

---

## 🧪 Critères d'acceptation

### Tests unitaires
- [ ] `test_retry_policy.py` : `compute_next_retry_delay(0)` retourne entre 0.8 et 1.2
- [ ] `test_retry_policy.py` : `compute_next_retry_delay(1)` retourne entre 4 et 6
- [ ] `test_retry_policy.py` : `compute_next_retry_delay(2)` retourne entre 24 et 36
- [ ] `test_queue_service.py` : `enqueue_task()` crée une tâche en BDD avec status='pending'
- [ ] `test_telegram_notifier.py` : `send_telegram_alert()` envoie un POST correct (mock httpx)

### Test E2E (`test_queue_worker_e2e.py`)
- [ ] Démarre le worker
- [ ] Enqueue une tâche qui échoue 3 fois (mock du handler qui raise)
- [ ] Vérifie : 3 attempts, status='failed', Telegram alert envoyé (mock)
- [ ] Vérifie : délai entre les tentatives ≈ 1s, 5s, 30s (±jitter)

### Vérification manuelle
- [ ] Lancer l'API : `uvicorn app.main:app --reload --port 8000`
- [ ] Lancer le worker en parallèle : `python -m app.workers.queue_worker`
- [ ] POST une tâche qui réussit → vérifier status='success' en BDD
- [ ] POST une tâche qui échoue → vérifier 3 retries puis 'failed' + Telegram alert reçu

---

## ⚠️ Points d'attention

1. **Le worker est un process séparé de l'API**. Pas dans le même process (sinon tu bloques l'API quand le worker dort). Utilise `python -m app.workers.queue_worker` en parallèle de l'API.

2. **Concurrence** : un seul worker pour la phase A (suffisant). Si plusieurs workers en parallèle, ajouter un `SELECT ... FOR UPDATE` ou un lock applicatif (sinon double-traitement).

3. **Crash du worker mid-task** : si le worker crash pendant qu'une tâche est en status='running', elle reste bloquée. **Ajoute une routine de recovery au démarrage** : toute tâche en 'running' depuis >5 min est remise en 'pending'.

4. **Backoff persistant** : `next_retry_at` est en BDD, pas en mémoire. Donc même si le worker crash, la tâche sera retentée au bon moment.

5. **Tests de timing** : les tests de backoff doivent être **souple** (accepter 0.8-1.2s pour 1s attendu), pas strict. Sinon flaky en CI.

6. **Telegram rate limit** : Telegram limite à ~30 msg/sec par bot. Pas un problème pour la phase A (volume faible), mais à surveiller.

7. **Idempotence** : si une tâche réussit côté worker mais que le callback Telegram plante, on va re-tenter la tâche. Pour la phase A, c'est OK. Phase B = ajouter un dedup_key par tâche.

8. **Pas de DLQ** (Dead Letter Queue) : les tâches failed restent en BDD, pas dans une file séparée. Suffisant pour la phase A. Phase B = DLQ + replay manuel.

---

## 🔌 Intégration avec les autres blocs

**Ce bloc s'invoque depuis** :
- `bloc-3-generation` : `enqueue_task("generate_text", ...)` et `enqueue_task("generate_image", ...)`
- `bloc-5-extension` (côté backend) : `enqueue_task("publish_post", ...)` quand un post est "validated"

**Ce bloc appelle** :
- `bloc-3-generation` (services LLM + Image)
- `bloc-5-extension` (via callback HTTP/WebSocket — à définir en phase B)

**Pour la phase A, on triche** : le worker appelle les services en local (même process) via import Python. Pas de HTTP entre services. C'est moche mais ça marche et c'est simple.

---

## 🚀 Commandes utiles (pour Mathieu)

```bash
cd /data/home-mathieu/saas-rse/bloc-7-resilience

# Setup
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Lancer l'API
uvicorn app.main:app --reload --port 8000

# Lancer le worker (dans un autre terminal)
python -m app.workers.queue_worker

# Tests
pytest -v
```

---

## ❌ Ce que ce bloc ne fait PAS

- ❌ Circuit breaker (phase B+)
- ❌ Rate limiting intelligent (phase B+)
- ❌ Fallback API officielle (phase B+)
- ❌ Dead Letter Queue (phase B+)
- ❌ Multi-worker coordination (phase B+)
- ❌ Métriques Prometheus (phase B+)
- ❌ Dashboard web des tâches (c'est le bloc 6, minimal : juste un GET /api/v1/queue/stats)

---

## 🤖 Prompt pour Claude Code

```
Lis ce fichier SPEC.md en entier. Implémente le bloc 7 (résilience + queue)
dans /data/home-mathieu/saas-rse/bloc-7-resilience/.

Règles strictes :
1. Worker = process séparé de l'API (pas dans le même process)
2. Backoff schedule = [1, 5, 30] secondes avec jitter ±20%
3. Recovery au démarrage : tâches 'running' depuis >5min → remise en 'pending'
4. Telegram alert UNIQUEMENT après 3 échecs, pas avant
5. Pas de HTTP entre services (import Python direct en phase A)
6. Tests pytest qui marchent vraiment (timing souple: 0.8-1.2s pour 1s)
7. Code self-documenting
8. Logs structurés loguru avec task_id dans le context

Quand tu as fini, liste précisément :
- Les fichiers créés
- Les tests qui passent (avec les temps mesurés)
- Les décisions d'archi prises
- Les limitations connues
- Les instructions de test manuel pour Mathieu
```
