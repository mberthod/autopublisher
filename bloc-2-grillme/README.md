# Bloc 2 — GrilledMe (port 8001)

Onboarding conversationnel IA → génère un persona complet en 4 questions.

## Flow

```
POST /api/v1/grillme/sessions           → démarre une session (retourne session_id + 1ère question)
POST /api/v1/grillme/sessions/{id}/messages → envoie une réponse (retourne next_question)
GET  /api/v1/grillme/sessions/{id}/persona  → récupère le persona généré (après is_complete=true)
```

## Champs collectés (dans l'ordre)

1. **cible** — qui est la personne idéale ?
2. **besoins** — quels problèmes cherche-t-elle à résoudre ?
3. **frustrations** — ses douleurs quotidiennes
4. **charte** — ton, mots interdits, longueur, emojis

La progression est contrôlée côté serveur (pas par le LLM) : exactement 4 questions.

## Démarrage

```bash
cd bloc-2-grillme
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001
```
