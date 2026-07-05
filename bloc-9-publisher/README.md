# bloc-9-publisher — Worker de publication serveur

Publie les posts planifiés **100 % côté serveur** — **le PC de l'utilisateur peut être éteint**.

> **Historique** : la première version utilisait Playwright headless + rejeu des cookies.
> **Abandonné** : rejouer une session LinkedIn hors du navigateur d'origine est bloqué
> (401 / anti-rejeu). Remplacé par une API privée (Instagram) et un service tiers (LinkedIn).

## Répartition par plateforme

| Plateforme | Méthode | Fichier |
|------------|---------|---------|
| **Instagram** | **instagrapi** — `login_by_sessionid()` (session capturée par l'extension) → `photo_upload()` | `ig_publisher.py` |
| **LinkedIn (page entreprise)** | **Unipile** — `POST {DSN}/api/v1/posts` multipart, `as_organization=<org_id>` | `li_unipile.py` |

`worker.py` : `PUBLISHERS = {instagram: instagrapi, linkedin: unipile}`.

## Flux
1. L'extension capture la session Instagram → `POST /api/v1/sessions`.
2. Le worker poll `GET /api/v1/tasks/pending` (toutes les `POLL_INTERVAL` s).
3. Pour chaque post : publie via le publisher de sa plateforme, puis
   `POST /api/v1/tasks/{id}/callback` (published / failed).
4. Session Instagram absente/invalide → callback `AUTH_REQUIRED` + invalidation.

## Setup
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Configuration — `.env` (non versionné, chmod 600)
```
BACKEND_URL=http://192.168.0.176:8000
POLL_INTERVAL=60
UNIPILE_DSN=https://api17.unipile.com:14715
UNIPILE_API_KEY=...
UNIPILE_LINKEDIN_ACCOUNT_ID=-53P70FMSeqz_6UNOCvjdg
```
Org LinkedIn Noisyless = `115871126`.

## Lancement
```bash
bash start.sh                 # source le .env puis lance worker.py — log : /tmp/bloc9.log
```

## Test d'une publication unique
```bash
.venv/bin/python run_once.py <task_id>
```

## À faire
- Passer en **service systemd** (survie au reboot).
- Alerte Telegram sur session Instagram expirée.
