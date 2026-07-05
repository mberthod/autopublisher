# Bloc 3 — Génération de posts (texte + image)

Pipeline : Persona + angle éditorial → post draft en BDD (texte LLM + image FAL.ai optionnelle).

## Setup

```bash
cd /data/home-mathieu/saas-rse/bloc-3-generation
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# Ajouter FAL_KEY dans .env si tu veux les images
```

## Lancer

```bash
uvicorn app.main:app --reload --port 8003
# Swagger : http://192.168.0.176:8003/docs
# Images servies : http://192.168.0.176:8003/static/posts/
```

## Tests (LLM et FAL.ai mockés)

```bash
pytest -v
pytest -v --cov=app
```

## Tester la génération réelle

```bash
# Avec un persona existant en DB (créé par bloc 1 ou 2)
curl -s -X POST http://localhost:8003/api/v1/posts/generate \
  -H "Content-Type: application/json" \
  -d '{
    "planning_id": "PLANNING_UUID",
    "persona_id": "PERSONA_UUID",
    "angle_editorial": "Comment Noisyless aide les propriétaires Airbnb à réduire les conflits de voisinage",
    "format": "text_only",
    "platform": "linkedin"
  }' | python3 -m json.tool
```

## Notes

- **LLM** : Ollama `deepseek-v4-flash:cloud` via `http://localhost:11434/v1`
- **Images** : FAL.ai `fal-ai/flux/dev` (negative prompt anti-texte) — skippé si `FAL_KEY` vide
- **Stockage images** : `./data/posts/{post_id}.png` servi en static
- **generation_metadata** : colonne ajoutée à la table `posts` au démarrage (ALTER TABLE idempotent)
- **Carousel** : délegué au bloc 4 (provider=playwright, pas d'image générée ici)

## Post-traitement image (overlay Pillow)

Après génération FAL, `image_service` ajoute : dégradé sombre en bas + **hook** (visual_headline)
blanc bold + barre accent orange + **logo Noisyless** (haut droite). Format IG carré / LinkedIn paysage.

## Positionnement injecté

`llm_service.load_positioning(bu)` injecte le positionnement éditable (table `Positioning`, éditée
via le dashboard `/positionnement`) dans les 3 prompts (idées, LinkedIn, Instagram) via `{positionnement}`.
