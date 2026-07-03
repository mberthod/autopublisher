# Bloc 4 — Carrousels (port 8004)

Génère des slides PNG 1080×1080 via Playwright headless + Jinja2.

## Endpoints

```
POST /api/v1/image/generate    → 1 slide PNG (image de post)
POST /api/v1/carousel/generate → N slides PNG
GET  /static/carousels/**      → servir les PNGs générés
```

### POST /api/v1/image/generate

```json
{
  "bu": "noisyless",
  "theme": "modern",
  "title": "Les 3 erreurs…",
  "body": "Texte du post…",
  "background_color": "#1A1A2E",
  "text_color": "#E2E2F0"
}
```

Retourne : `{ "image_url": "http://192.168.0.176:8004/static/carousels/{id}/slide_0.png" }`

## Thèmes disponibles

`modern` `minimal` `bold` `organic`

## Démarrage

```bash
cd bloc-4-carrousels
.venv/bin/uvicorn api_server:app --host 0.0.0.0 --port 8004
```
