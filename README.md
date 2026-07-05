# AutoPublisher — SaaS RSE

Publication automatique et fiable de contenu RSE sur **LinkedIn (pages entreprise)** et
**Instagram (comptes pro)** pour 3 BU : **Noisyless**, **Afluxo**, **MBHREP**.

> **État : STABLE (2026-07-05).** Publication 100 % côté serveur — **le PC peut être éteint**.
> Flux : Dashboard « Publier maintenant » → post `scheduled` → worker serveur (poll 60 s) →
> Instagram (instagrapi) ou LinkedIn page (Unipile) → callback `published`.

---

## Architecture (9 blocs)

| Bloc | Dossier | Port | Rôle | Tests |
|------|---------|------|------|-------|
| 1 — Backend API | `bloc-1-backend` | 8000 | API centrale FastAPI + SQLite (personas, posts, comptes, sessions, positionnement, métriques) | 67 pytest |
| 2 — GrilledMe | `bloc-2-grillme` | 8001 | Onboarding conversationnel LLM adaptatif → persona | 22 pytest |
| 3 — Génération | `bloc-3-generation` | 8003 | Génération texte (LLM) + image (FAL.ai flux/dev) + overlay hook/logo | 19 pytest |
| 4 — Carrousels | `bloc-4-carrousels` | 8004 | Génération PNG (Playwright + Jinja2), template Instagram | 9 pytest |
| 5 — Extension Chrome | `bloc-5-extension` | — | **Capture la session Instagram** (cookies) pour instagrapi — **ne publie plus** | 21 vitest |
| 6 — Dashboard | `bloc-6-dashboard` | 5174* | SvelteKit — Studio de contenu, calendrier, comptes, positionnement, état sessions | manuel |
| 7 — Résilience | `bloc-7-resilience` | 8002 | Queue SQLite + retry + alertes Telegram | 29 pytest |
| 8 — Intégration | `bloc-8-integration` | — | Tests E2E + recette (gates S1–S5) | 17 pytest |
| 9 — Publisher | `bloc-9-publisher` | — | **Worker serveur headless** : publie Instagram (instagrapi) + LinkedIn page (Unipile) | — |

\* Le dashboard tourne sur **5174** (le port 5173 est déjà occupé sur ce serveur).

Serveur : `mathieu@192.168.0.176`, projet dans `/data/home-mathieu/saas-rse/`.
Dépôt : `git@github.com:mberthod/autopublisher.git`.

---

## Modèle de publication (pivot majeur du 2026-07-04/05)

**Décision : ne plus dépendre du PC allumé.** Modèle « Unipile self-hosted ». Après avoir constaté
que rejouer une session LinkedIn hors du navigateur d'origine est bloqué (401/anti-rejeu) et que
l'API officielle LinkedIn n'est pas approuvée, la publication est répartie par plateforme :

- **Instagram** → **instagrapi** (API privée mobile) côté serveur (bloc-9 `ig_publisher.py`).
  `login_by_sessionid()` avec le `sessionid` capturé par l'extension → `photo_upload()`. PC éteint OK.
- **LinkedIn (page entreprise)** → **Unipile** (bloc-9 `li_unipile.py`).
  `POST {UNIPILE_DSN}/api/v1/posts` (multipart) avec `as_organization=<org_id>`. PC éteint OK.

Le worker (`bloc-9-publisher/worker.py`) poll `tasks/pending` toutes les 60 s :
`PUBLISHERS = {instagram: instagrapi, linkedin: unipile}`.
L'**extension Chrome ne publie plus** — elle sert uniquement à synchroniser la session Instagram.

---

## Workflow utilisateur

```
GrilledMe (chat IA adaptatif)                    → Persona (cible, besoins, frustrations, charte)
Persona → Studio /compose → 10 idées IA          → sélection → génération masse (texte + image)
Positionnement (/positionnement, éditable par BU) → injecté dans tous les prompts
Validation + planification (calendrier)          → post scheduled
« Publier maintenant » / créneau planifié        → worker serveur publie → published
```

Contenu : posts LinkedIn (hook 1400–2000 car. + storytelling + CTA), posts Instagram
(JSON `{visual, caption}` + hashtags), images FAL flux/dev avec overlay hook + logo Noisyless.

---

## Démarrage

```bash
# Blocs backend (1,2,3,4,7) en une commande
bash /data/home-mathieu/saas-rse/start_all.sh

# Dashboard
cd bloc-6-dashboard && npm run dev            # http://192.168.0.176:5174

# Worker de publication serveur (Instagram + LinkedIn)
bash bloc-9-publisher/start.sh                # log : /tmp/bloc9.log
```

> **À faire** : passer bloc-9 en **service systemd** pour survivre au reboot.

---

## Configuration (.env, non versionnés)

```
bloc-3-generation/.env
  DEEPSEEK_BASE_URL=http://localhost:11434/v1
  DEEPSEEK_MODEL=deepseek-v4-flash:cloud
  FAL_KEY=...                                  # requis pour les vraies images IA

bloc-6-dashboard/.env
  PUBLIC_API_URL=http://192.168.0.176:8000/api/v1
  PUBLIC_GRILLME_URL=http://192.168.0.176:8001/api/v1
  PUBLIC_GENERATION_URL=http://192.168.0.176:8003
  PUBLIC_CAROUSEL_URL=http://192.168.0.176:8004

bloc-9-publisher/.env                          # chmod 600
  BACKEND_URL=http://192.168.0.176:8000
  POLL_INTERVAL=60
  UNIPILE_DSN=https://api17.unipile.com:14715
  UNIPILE_API_KEY=...
  UNIPILE_LINKEDIN_ACCOUNT_ID=-53P70FMSeqz_6UNOCvjdg
```

Comptes Unipile : LinkedIn `-53P70FMSeqz_6UNOCvjdg`, Instagram `hfXAX-rSQUehZV97QhOADw`.
Org LinkedIn Noisyless = **115871126**.

---

## Données

- **SQLite partagé** : `bloc-1-backend/data/saas_rse.db` (chemin absolu, utilisé par tous les blocs).
- Migrations idempotentes au démarrage (`app/migrations.py`, appelées par `init_db`).
- Tables clés : `Persona`, `Post`, `Account` (personal / company_page / business_account),
  `Session` (cookies par plateforme, jamais loggés), `Positioning` (par BU), `PostMetrics`.

---

## Stack technique

- **Backend** : FastAPI + SQLAlchemy 2 + Pydantic v2 + SQLite partagé
- **LLM** : DeepSeek via Ollama local (`http://localhost:11434/v1`)
- **Images** : FAL.ai (`fal-ai/flux/dev`, negative prompt anti-texte) + overlay Pillow (hook + logo) ;
  carrousels via Playwright headless
- **Publication** : instagrapi (Instagram) + Unipile (LinkedIn page) — 100 % serveur
- **Extension** : Chrome MV3, vanilla JS ES modules, `chrome.alarms` (sync session Instagram)
- **Dashboard** : SvelteKit 2 + TypeScript strict + CSS pur (Studio dark)
- **Tests** : pytest-asyncio + httpx + Playwright + vitest

---

## Recette (gates S1–S5)

```bash
bash bloc-8-integration/scripts/run_recette.sh
```

S1 (GrilledMe→Persona) → S2 (génération post publiable) → S3 (1 post test publié) →
S4 (7 posts / 7 jours) → S5 (30 posts, < 5 % d'échecs, 0 ban).

---

## Reste à faire

- **systemd** pour le worker bloc-9 (survie au reboot)
- Alerte Telegram sur session Instagram expirée
- Nettoyer le code de capture/publication LinkedIn inutilisé dans l'extension (voies internes abandonnées)
- Choix du compte cible par post dans `/compose` (`account_id`)
- TikTok (vidéo), auth multi-utilisateur, packaging Chrome Web Store, docker-compose

---

Historique détaillé des décisions et itérations : voir [`evolution_saas.md`](evolution_saas.md).
