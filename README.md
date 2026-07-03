# AutoPublisher — SaaS RSE

Système de publication automatique sur LinkedIn et Instagram pour 3 BUs RSE (Noisyless, Afluxo, MBHREP).

## Architecture

| Bloc | Port | Rôle |
|------|------|------|
| bloc-1-backend | 8000 | API centrale FastAPI + SQLite (personas, posts, plannings) |
| bloc-2-grillme | 8001 | Onboarding conversationnel IA → génération de personas |
| bloc-3-generation | 8003 | Génération texte/image via Ollama (DeepSeek) |
| bloc-4-carrousels | 8004 | Génération PNG carrousels via Playwright |
| bloc-5-extension | — | Extension Chrome MV3 — publication LinkedIn/Instagram |
| bloc-6-dashboard | 5173 | Dashboard SvelteKit — Studio de contenu |
| bloc-7-resilience | 8002 | Queue SQLite + retry + alertes Telegram |
| bloc-8-integration | — | Tests E2E + recette |

## Workflow utilisateur

```
GrilledMe (4 questions IA) → Persona
Persona → Studio /compose → Idées éditoriales (mots-clés)
Idées → Génération masse (texte + image) → Validation → Planification
Extension Chrome → Publication automatique au créneau planifié
```

## Démarrage rapide (dev)

```bash
# Backend
cd bloc-1-backend && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 &
cd bloc-2-grillme && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001 &
cd bloc-3-generation && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8003 &
cd bloc-4-carrousels && .venv/bin/uvicorn api_server:app --host 0.0.0.0 --port 8004 &
cd bloc-7-resilience && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8002 &

# Dashboard
cd bloc-6-dashboard && npm run dev
```

Dashboard : http://192.168.0.176:5173

## Variables d'environnement

```
bloc-3-generation/.env:
  DEEPSEEK_API_KEY=...
  DEEPSEEK_BASE_URL=http://localhost:11434/v1
  DEEPSEEK_MODEL=deepseek-v4-flash:cloud

bloc-6-dashboard/.env:
  PUBLIC_API_URL=http://192.168.0.176:8000/api/v1
  PUBLIC_GRILLME_URL=http://192.168.0.176:8001/api/v1
  PUBLIC_GENERATION_URL=http://192.168.0.176:8003
  PUBLIC_CAROUSEL_URL=http://192.168.0.176:8004
```

## Stack technique

- **Backend** : FastAPI + SQLAlchemy 2 + Pydantic v2 + SQLite partagé
- **LLM** : Ollama local (DeepSeek) — `http://localhost:11434/v1`
- **Images** : Playwright headless (carrousels PNG 1080×1080) + FAL.ai optionnel
- **Extension** : Chrome MV3, Manifest V3, vanilla JS ES modules, `chrome.alarms`
- **Dashboard** : SvelteKit 2 + TypeScript strict + CSS pur (dark mode Studio)
- **Tests** : pytest-asyncio + httpx + Playwright + vitest
