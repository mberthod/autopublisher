# bloc-9-publisher — Publication serveur (Playwright headless)

Publie les posts planifiés **côté serveur**, en rejouant la session de l'utilisateur
(cookies capturés par l'extension). Fonctionne PC de l'utilisateur éteint.

## Flux
1. L'extension capture les cookies (`POST /api/v1/sessions`).
2. Ce worker poll `GET /api/v1/tasks/pending`.
3. Pour chaque post LinkedIn : récupère la session, lance Chromium headless,
   injecte les cookies, publie, puis `POST /api/v1/tasks/{id}/callback`.

## Setup
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
# navigateurs déjà installés (partagés avec bloc-4) ; sinon :
# .venv/bin/playwright install chromium
```

## Lancement
```bash
BACKEND_URL=http://192.168.0.176:8000 POLL_INTERVAL=60 nohup .venv/bin/python worker.py > /tmp/bloc9.log 2>&1 &
```

## Test d'une publication unique
```bash
.venv/bin/python run_once.py <task_id>
```
