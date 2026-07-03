# Bloc 4 — Génération de carrousels (Playwright)

> **Statut** : SPEC à implémenter par Claude Code
> **Owner** : Mathieu (revieweur), Claude Code (implémenteur)
> **Livrable** : Service qui transforme un JSON de slides en N images PNG via Playwright

---

## 🎯 Objectif

À partir d'un JSON structuré décrivant un carrousel (titre, slides avec texte, palette de couleurs), produire N fichiers PNG (1 par slide) prêts à être publiés comme carrousel sur Instagram ou LinkedIn.

**Pourquoi pas Pillow** : trop limité pour faire du beau texte varié, du layout responsive, des images de fond propres. Playwright + HTML/CSS te donne **rendu identique à un dev web**, gratuitement.

---

## 📥 Inputs

```python
# Fonction Python (pas HTTP, c'est un service interne)
async def generate_carousel(spec: CarouselSpec) -> list[str]:
    """
    spec: CarouselSpec (Pydantic)
    returns: liste d'URLs/paths vers les PNG générés
    """
```

```python
# Schéma Pydantic
class CarouselSlide(BaseModel):
    index: int                            # 1-based
    title: str | None                     # optionnel, ex: "3 raisons"
    body: str                             # corps du texte de la slide
    background: Literal["solid", "gradient", "image"] = "solid"
    background_color: str = "#FFFFFF"     # hex, ex: "#FF6B35"
    text_color: str = "#1A1A1A"

class CarouselSpec(BaseModel):
    bu: Literal["noisyless", "afluxo", "mbhrep"]
    theme: Literal["modern", "minimal", "bold", "organic"] = "modern"
    slides: list[CarouselSlide]           # 1 ≤ len ≤ 10
    width: int = 1080                     # px (IG carré)
    height: int = 1080                    # px
    output_dir: str = "./data/carousels"  # où écrire les PNG
```

---

## 📤 Outputs

```python
# list[str] : paths absolus vers les PNG générés
# Ex: ["/data/saas-rse/data/carousels/abc_slide1.png", ".../abc_slide2.png", ...]
```

---

## 🏗️ Architecture cible

```
[Bloc 3 appelle ce service]
    │
    ▼
[CarouselService.generate_carousel(spec)]
    │
    ├──► [TemplateEngine.render_html()]
    │         │
    │         └──► Choisit le template Jinja2 selon `spec.theme`:
    │              - modern → templates/modern.html
    │              - minimal → templates/minimal.html
    │              - bold → templates/bold.html
    │              - organic → templates/organic.html
    │
    ├──► [Loop sur chaque slide]
    │         │
    │         ├──► Construit le HTML pour cette slide (injecte title, body, colors)
    │         │
    │         ├──► [Playwright.launch()]
    │         │     │
    │         │     ├──► new_context(viewport={"width": spec.width, "height": spec.height})
    │         │     ├──► new_page()
    │         │     ├──► page.set_content(html, wait_until="networkidle")
    │         │     ├──► page.screenshot(path=f"{spec.output_dir}/{uuid}_slide{i}.png", full_page=False)
    │         │     └──► context.close()
    │         │
    │         └──► Retourne le path du PNG
    │
    └──► return [paths]
```

---

## 📁 Structure de fichiers

```
/data/home-mathieu/saas-rse/
└── bloc-4-carrousels/
    ├── SPEC.md                        ← ce fichier
    ├── README.md
    ├── pyproject.toml
    ├── .env.example
    ├── app/
    │   ├── __init__.py
    │   ├── main.py                    ← point d'entrée (CLI + FastAPI optional)
    │   ├── config.py
    │   ├── schemas.py                 ← Pydantic: CarouselSpec, CarouselSlide
    │   ├── services/
    │   │   ├── __init__.py
    │   │   ├── carousel_service.py    ← logique principale
    │   │   └── template_engine.py
    │   └── templates/
    │       ├── modern.html
    │       ├── minimal.html
    │       ├── bold.html
    │       └── organic.html
    └── tests/
        ├── test_template_engine.py
        ├── test_carousel_service.py
        └── fixtures/
            └── sample_spec.json
```

---

## 🛠️ Dépendances

```toml
[project]
dependencies = [
  "playwright>=1.48,<2",                # moteur de rendu
  "jinja2>=3.1,<4",                     # templates
  "pydantic>=2.9,<3",
  "pydantic-settings>=2.6,<3",
  "loguru>=0.7,<1",
  "Pillow>=10.4,<11",                   # manipulation image (crop, etc.)
]

[project.optional-dependencies]
dev = ["pytest>=8.3,<9", "pytest-asyncio>=0.24,<1"]
```

**Note Playwright** : après `pip install playwright`, il faut faire `playwright install chromium` (ça télécharge ~300MB).

---

## 🔑 Variables d'environnement

`.env` :
```bash
# Dossier de sortie des PNG
CAROUSELS_OUTPUT_DIR=./data/carousels

# Chromium path (laisser vide pour auto-détection)
PLAYWRIGHT_BROWSERS_PATH=

# Logging
LOG_LEVEL=INFO
```

---

## 🎨 Templates (4 minimum)

### `modern.html` (par défaut)
- Fond blanc, texte noir, accent coloré discret
- Typo sans-serif moderne (Inter ou system-ui)
- Layout centré avec marges généreuses
- Idéal pour : posts corporate, MBHREP

### `minimal.html`
- Fond uni, texte fin, beaucoup d'espace
- Pas d'accent, focus sur le message
- Idéal pour : citations, Afluxo

### `bold.html`
- Fond coloré vif, texte contrasté
- Typo large et épaisse
- Idéal pour : Instagram Noisyless, posts qui doivent arrêter le scroll

### `organic.html`
- Dégradés subtils, formes arrondies
- Couleurs douces
- Idéal pour : bien-être, location courte durée

**Les 4 templates DOIVENT être créés.** Pas juste un squelette.

---

## 🧪 Critères d'acceptation

### Tests unitaires
- [ ] `test_template_engine.py` : `render_html(slide, theme="modern")` retourne du HTML non vide contenant `{{slide.body}}` (résolu)
- [ ] `test_template_engine.py` : la couleur de fond du HTML résolu contient `{{slide.background_color}}`

### Tests d'intégration (`test_carousel_service.py`)
- [ ] `test_generate_carousel_simple` : un spec de 3 slides produit 3 fichiers PNG
- [ ] Les PNG font bien 1080×1080 pixels (vérifier avec Pillow)
- [ ] Les PNG ne sont pas vides (taille > 5KB chacun)
- [ ] `test_generate_carousel_themes` : les 4 thèmes produisent des PNG visuellement différents (test simple : bytes différents)

### Test E2E
- [ ] Lancer : `python -m app.main --spec tests/fixtures/sample_spec.json`
- [ ] Vérifier visuellement les PNG générés : ouvrir dans un viewer
- [ ] Les 4 thèmes sont visuellement cohérents et propres

### Vérification manuelle
- [ ] Lancer avec un vrai cas : un carrousel Noisyless 5 slides sur "5 sources de bruit dans une location Airbnb"
- [ ] Vérifier : c'est joli, c'est lisible, c'est publiable

---

## ⚠️ Points d'attention

1. **Performance** : Playwright lance un navigateur par slide, c'est lent. Pour 10 slides, ~20-30s. Pour la phase A ça va, mais si tu fais 30 posts/jour × 5 slides = 150 PNG/jour = 1h de génération. Envisage de réutiliser un seul contexte Playwright pour toutes les slides d'un carrousel.

2. **Mémoire** : Playwright consomme ~300MB par contexte. Ferme bien les contextes après usage (`context.close()`).

3. **Async** : `playwright.async_api` est plus performant que sync. Utilise-le.

4. **Erreurs de rendu** : si un template Jinja a une erreur, le service doit remonter une exception claire, pas planter silencieusement.

5. **Cache des templates** : charge les templates Jinja UNE fois au démarrage, pas à chaque génération. Utilise `jinja2.Environment(loader=FileSystemLoader(...))` avec `cache_size=100`.

6. **Cleanup** : les PNG générés doivent être nettoyés après X jours (cron) ou stockés sur S3. Pour la phase A, garde tout dans `./data/carousels/`.

7. **Pas de web fonts externes** : pas de Google Fonts dans les templates (ça peut être bloqué en local). Utilise des `font-family: system-ui, -apple-system, sans-serif`.

---

## 📝 Exemple de spec d'entrée

```json
{
  "bu": "noisyless",
  "theme": "bold",
  "slides": [
    {
      "index": 1,
      "title": "5 sources de bruit",
      "body": "que vos locataires détestent",
      "background": "solid",
      "background_color": "#FF6B35",
      "text_color": "#FFFFFF"
    },
    {
      "index": 2,
      "title": null,
      "body": "1. Les pas des voisins du dessus",
      "background": "solid",
      "background_color": "#F7F7F7",
      "text_color": "#1A1A1A"
    },
    {
      "index": 3,
      "title": null,
      "body": "2. La rue passante la nuit",
      "background": "solid",
      "background_color": "#F7F7F7",
      "text_color": "#1A1A1A"
    }
  ],
  "width": 1080,
  "height": 1080,
  "output_dir": "./data/carousels"
}
```

---

## 🚀 Commandes utiles (pour Mathieu)

```bash
cd /data/home-mathieu/saas-rse/bloc-4-carrousels

# Setup
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium

# Test CLI avec un spec
python -m app.main --spec tests/fixtures/sample_spec.json

# Test programmatique
python -c "from app.services.carousel_service import CarouselService; ..."

# Tests
pytest -v
```

---

## ❌ Ce que ce bloc ne fait PAS

- ❌ Génération du texte des slides (c'est le bloc 3, LLM)
- ❌ Publication sur Instagram/LinkedIn (c'est l'extension, bloc 5)
- ❌ Retry en cas d'échec (c'est le bloc 7)
- ❌ Interface web de preview (c'est le bloc 6, dashboard)
- ❌ Templates avancés (vidéo, animation, GIF)

---

## 🤖 Prompt pour Claude Code

```
Lis ce fichier SPEC.md en entier. Implémente le bloc 4 (génération de carrousels)
dans /data/home-mathieu/saas-rse/bloc-4-carrousels/.

Règles strictes :
1. Demande confirmation avant toute décision d'archi non couverte par le SPEC
2. Les 4 templates Jinja2 DOIVENT être créés et visuellement différents
3. Utilise playwright.async_api (PAS sync)
4. Ferme les contextes après usage (pas de fuite mémoire)
5. Un seul environnement Jinja2 partagé, chargé au démarrage (pas de re-load)
6. Tests pytest qui marchent vraiment (pas des squelettes)
7. Code self-documenting, pas de commentaires évidents
8. Le CLI doit accepter --spec (path JSON) et produire les PNG

Quand tu as fini, liste précisément :
- Les fichiers créés
- Les 4 templates HTML livrés (description visuelle courte)
- Les tests qui passent
- Les décisions d'archi prises
- Les limitations connues
- Un exemple de PNG généré pour vérification visuelle
```
