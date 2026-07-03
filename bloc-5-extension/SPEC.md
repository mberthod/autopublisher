# Bloc 5 — Extension Chrome (LinkedIn + Instagram Noisyless)

> **Statut** : SPEC à implémenter par Claude Code
> **Owner** : Mathieu (revieweur), Claude Code (implémenteur)
> **Livrable** : Extension Chrome Manifest V3 qui publie un post draft depuis la queue backend sur LinkedIn et Instagram

---

## 🎯 Objectif

Extension Chrome qui :
1. **Poll** le backend toutes les 5 min pour récupérer les posts à publier (`GET /api/v1/tasks/pending`)
2. Pour chaque tâche, **ouvre un onglet masqué** sur la plateforme cible
3. **Injecte un content script** qui manipule le DOM pour publier le post (texte + média)
4. **Notifie le backend** du succès/échec (`POST /api/v1/tasks/{id}/callback`)
5. **Ferme l'onglet** une fois publié

**Distribution phase A** : unpacked (.crx chargé manuellement via `chrome://extensions` en mode développeur)
**Distribution phase B** : packaging Chrome Web Store (pas dans ce scope)

---

## 📥 Inputs (depuis le backend)

```python
# GET /api/v1/tasks/pending
# Response: 200 OK
{
  "tasks": [
    {
      "task_id": "uuid",
      "post_id": "uuid",
      "platform": "linkedin" | "instagram",
      "format": "text_only" | "image" | "carousel",
      "text": "Le texte du post à publier...",
      "media_urls": [
        "https://backend.example.com/static/posts/abc.png"
      ],
      "scheduled_for": "2026-07-15T09:00:00Z",
      "selectors_version": "2026-07-12-v3"  # version des remote selectors à utiliser
    }
  ]
}
```

---

## 📤 Outputs (vers le backend)

```python
# POST /api/v1/tasks/{task_id}/callback
# Body: succès
{
  "status": "success",
  "post_url": "https://linkedin.com/posts/mathieu-mathieu-abc...",  # URL du post publié
  "published_at": "2026-07-15T09:03:42Z"
}

# Body: échec
{
  "status": "failed",
  "error_code": "AUTH_REQUIRED" | "RATE_LIMIT" | "SELECTOR_NOT_FOUND" | "MEDIA_UPLOAD_FAILED" | "UNKNOWN",
  "error_message": "Human-readable error",
  "screenshot_url": "https://backend.example.com/static/errors/abc.png"  # screenshot de l'erreur
}
```

---

## 🏗️ Architecture de l'extension

```
saas-rse-extension/
├── manifest.json                       ← Manifest V3
├── background/
│   ├── service-worker.js               ← SW principal (polling, orchestration)
│   ├── remote-selectors.js             ← gestion du cache des sélecteurs
│   ├── task-queue.js                   ← queue interne des tâches
│   └── api-client.js                   ← appels au backend
├── content/
│   ├── linkedin-publisher.js           ← Content Script LinkedIn
│   ├── instagram-publisher.js          ← Content Script Instagram
│   └── shared/
│       ├── human-typer.js              ← simulation frappe humaine
│       ├── media-uploader.js           ← injection fichier dans <input type="file">
│       └── wait-for-element.js         ← waitFor robuste (MutationObserver)
├── offscreen/
│   └── offscreen.html + .js            ← pour opérations DOM complexes
├── popup/
│   ├── popup.html
│   ├── popup.css
│   └── popup.js                        ← UI de l'extension (état, dernière tâche)
├── icons/
│   ├── 16.png
│   ├── 48.png
│   └── 128.png
└── README.md
```

---

## 📋 manifest.json (V3)

```json
{
  "manifest_version": 3,
  "name": "SaaS RSE Publisher",
  "version": "0.1.0",
  "description": "Publishes pre-generated posts to LinkedIn and Instagram",
  "permissions": [
    "alarms",
    "storage",
    "tabs",
    "scripting",
    "offscreen"
  ],
  "host_permissions": [
    "https://www.linkedin.com/*",
    "https://www.instagram.com/*",
    "https://backend.example.com/*"
  ],
  "background": {
    "service_worker": "background/service-worker.js",
    "type": "module"
  },
  "content_scripts": [
    {
      "matches": ["https://www.linkedin.com/*"],
      "js": ["content/linkedin-publisher.js"],
      "run_at": "document_idle",
      "all_frames": false
    },
    {
      "matches": ["https://www.instagram.com/*"],
      "js": ["content/instagram-publisher.js"],
      "run_at": "document_idle",
      "all_frames": false
    }
  ],
  "action": {
    "default_popup": "popup/popup.html",
    "default_icon": {
      "16": "icons/16.png",
      "48": "icons/48.png",
      "128": "icons/128.png"
    }
  },
  "web_accessible_resources": [
    {
      "resources": ["offscreen/offscreen.html"],
      "matches": ["<all_urls>"]
    }
  ]
}
```

---

## 🔑 Remote Selectors (CRITIQUE)

Les sélecteurs DOM sont dans un JSON servi par le backend, **pas hardcodés dans l'extension**. Le SW charge ce JSON au démarrage et toutes les 6h.

**Endpoint** : `GET /api/v1/selectors/{version}`

**Format** :
```json
{
  "version": "2026-07-12-v3",
  "updated_at": "2026-07-12T10:00:00Z",
  "min_extension_version": "0.1.0",
  "platforms": {
    "linkedin": {
      "btn_open_compose": "button[aria-label='Commencer un post']",
      "text_editor": "div[role='textbox'][aria-label*=" éditeur "]",
      "file_input": "input[type='file'][accept*='image']",
      "btn_submit": "button.share-actions__primary-action",
      "btn_post_publish": "button[aria-label='Publier']",
      "success_toast": "div[role='alert']"
    },
    "instagram": {
      "btn_new_post": "svg[aria-label='Nouvelle publication']",
      "btn_select_file": "button:has-text('Sélectionner depuis l'ordinateur')",
      "file_input": "input[type='file']",
      "next_button": "button:has-text('Suivant')",
      "caption_editor": "textarea[aria-label='Écrire une légende']",
      "share_button": "button:has-text('Partager')"
    }
  }
}
```

**Cache local** : `chrome.storage.local` avec TTL de 6h. Si le backend est down, l'extension garde les anciens sélecteurs et continue à fonctionner (degraded mode).

---

## 🎭 Anti-détection (simulation humaine)

**Fichier** : `content/shared/human-typer.js`

**Comportement** :
- Tape caractère par caractère (pas de copier-coller)
- Délai aléatoire entre 50ms et 150ms par caractère
- Pauses de 1-3s entre chaque action majeure (clic, modal, upload)
- Déplace la souris de manière non-linéaire (bezier curves) avant chaque clic
- Scroll léger de la page après chargement

**⚠️ Ne pas** :
- Cliquer instantanément après un délai fixe
- Faire des actions trop rapides (humain moyen = 200-400ms entre actions)
- Ouvrir directement l'URL de publication (passer par feed d'abord)

---

## ⏱️ Flow complet d'une publication

```
1. [SW] Polling toutes les 5min → GET /api/v1/tasks/pending
2. [SW] Pour chaque tâche:
   a. Charge les remote selectors (cache 6h)
   b. Crée un onglet masqué: chrome.tabs.create({ url: platform_home, active: false })
   c. Attend que l'onglet soit chargé
   d. Injecte le content script publisher via chrome.scripting.executeScript
   e. Le content script:
      - Vérifie la session (sélecteur "feed" présent?)
      - Si non: POST callback error AUTH_REQUIRED, ferme l'onglet, FIN
      - Si oui: navigue vers la page de création de post
      - Clique le bouton "Commencer un post" (sélector btn_open_compose)
      - Attend l'éditeur de texte (waitFor(text_editor))
      - Tape le texte via human-typer
      - Upload le média via media-uploader
      - Clique "Publier" (sélector btn_submit)
      - Attend le toast de succès (success_toast)
      - Récupère l'URL du post (si visible)
   f. Le content script renvoie le résultat au SW via chrome.runtime.sendMessage
   g. Le SW POST callback au backend avec status
   h. Le SW ferme l'onglet: chrome.tabs.remove(tabId)
3. [SW] End of queue, attend le prochain polling
```

---

## 🛠️ Stack technique

**Pas de build tooling** : JavaScript vanilla (ES modules), pas de React/Vue. C'est une extension, pas une webapp.

**Dépendances tierces** (à éviter si possible) :
- ❌ jQuery, lodash → trop gros pour une extension
- ✅ Utiliser les APIs Chrome natives + vanilla JS
- ✅ Si besoin d'un test framework : `vitest` ou `jest` (en dev uniquement, pas bundlé)

**Pas de bundler** : Chrome charge les .js directement. Si tu veux modulariser, utilise ES modules (`import`/`export`) avec `"type": "module"` dans manifest.

---

## 🧪 Critères d'acceptation

### Tests unitaires (à faire avec vitest ou jest en local)
- [ ] `test_human-typer.js` : tape un texte de 50 chars en 2.5s-7.5s (délai 50-150ms × 50)
- [ ] `test_wait-for-element.js` : résout un élément qui apparaît après 1s en < 1.5s
- [ ] `test_wait-for-element.js` : timeout si l'élément n'apparaît pas en 10s

### Test E2E manuel (Mathieu)
- [ ] Charger l'extension en mode développeur (`chrome://extensions` → "Load unpacked")
- [ ] Vérifier : l'icône apparaît, le popup s'ouvre, montre "1 tâche en attente"
- [ ] **Test LinkedIn text-only** : 
  - Créer manuellement un post draft dans la BDD backend
  - L'extension doit le publier sur LinkedIn en < 60s
  - Vérifier le post sur linkedin.com
  - Vérifier le callback SUCCESS en BDD
- [ ] **Test LinkedIn avec image** :
  - Même chose mais avec une image
  - Vérifier que l'image est uploadée et visible
- [ ] **Test Instagram carrousel** :
  - 3 images en carrousel
  - Vérifier la publication
- [ ] **Test erreur** :
  - Se déconnecter de LinkedIn
  - Créer un post draft
  - L'extension doit renvoyer error AUTH_REQUIRED
  - Vérifier le statut "failed" en BDD

### Vérification visuelle du popup
- [ ] Affiche : "X tâches en attente", "Dernière tâche : succès/échec il y a Y min"
- [ ] Bouton "Force check now" qui déclenche un polling immédiat

---

## ⚠️ Points d'attention CRITIQUES

1. **Chrome Web Store = interdit pour ce use case**. Google rejette les extensions qui automatisent des plateformes tierces. Distribution **unpacked obligatoire** en phase A, **CWS en phase B** avec nom/description neutres (et migration possible de la base users si rejet).

2. **Service Worker se fait unload** : en MV3, le SW peut être déchargé après 30s d'inactivité. C'est OK pour le polling toutes les 5 min (chrome.alarms gère ça), mais le state doit être persistant (`chrome.storage.local`).

3. **Content Scripts isolés** : chaque content script a son propre monde JS. Communication avec le SW via `chrome.runtime.sendMessage`. Communication entre content scripts (rare) via `window.postMessage` (plus complexe).

4. **Rate limiting des plateformes** : LinkedIn bloque les publications trop rapides. Implémente un délai minimum de 4h entre 2 posts pour le même compte.

5. **Erreurs silencieuses** : si un sélecteur ne match pas, le content script peut attendre 30s puis timeout. Toujours avoir un timeout strict et un fallback.

6. **Pas de credentials en clair** : jamais de mot de passe dans le code. Le SW utilise les sessions actives du navigateur (l'utilisateur doit être déjà connecté à LinkedIn/IG dans le même profil Chrome).

7. **Médias = download avant upload** : pour contourner les CORS, le content script doit télécharger le média depuis le backend via `fetch`, le convertir en `Blob`, puis l'injecter dans `<input type="file">` via `DataTransfer`.

8. **Test sur un compte poubelle** : ne JAMAIS tester sur ton compte BU Noisyless (risque de ban). Crée un compte test LinkedIn et un compte test Instagram.

---

## 🔐 Sécurité

- **Pas de cookies manipulés** : tout est via les sessions actives
- **Pas de credentials en clair** : jamais dans le code, jamais dans chrome.storage
- **API token** : stocké dans `chrome.storage.local`, chiffré via `chrome.identity` API si possible
- **Backend URL** : configurable via popup, par défaut `http://localhost:8000`

---

## 🚀 Commandes utiles (pour Mathieu)

```bash
# Charger l'extension
# 1. Ouvrir chrome://extensions/
# 2. Activer "Mode développeur"
# 3. "Charger l'extension non empaquetée" → sélectionner /data/home-mathieu/saas-rse/bloc-5-extension/

# Voir les logs
# chrome://extensions/ → SaaS RSE Publisher → "Inspect views: service worker"

# Recharger après modif
# Bouton circulaire de rechargement dans chrome://extensions/

# Tests (si vitest configuré)
cd /data/home-mathieu/saas-rse/bloc-5-extension
npm test
```

---

## ❌ Ce que ce bloc ne fait PAS

- ❌ Génération de texte/image (bloc 3, 4)
- ❌ Retry intelligent sur 3 tentatives (bloc 7 — mais l'extension fait 1 tentative et remonte l'erreur)
- ❌ Scraping des analytics (phase B+)
- ❌ Publication sur X/Facebook (phase B+)
- ❌ Packaging Chrome Web Store (phase B+)
- ❌ Auth utilisateur (c'est juste un token API, pas de login UI)

---

## 🤖 Prompt pour Claude Code

```
Lis ce fichier SPEC.md en entier. Implémente le bloc 5 (extension Chrome)
dans /data/home-mathieu/saas-rse/bloc-5-extension/.

Règles strictes :
1. Manifest V3 strict (pas de V2, pas de background permanent)
2. JavaScript vanilla ES modules, PAS de React/Vue/Webpack
3. Demande confirmation avant toute décision d'archi non couverte
4. Remote selectors via fetch depuis le backend, cache chrome.storage.local
5. human-typer : délais aléatoires 50-150ms par char, pauses 1-3s entre actions
6. wait-for-element : MutationObserver avec timeout strict
7. Les content scripts ne communiquent JAMAIS entre eux, uniquement via le SW
8. Toute erreur remonte au SW qui appelle le callback backend
9. Tests unitaires avec vitest OU jest (au choix), pas les deux
10. README avec procédure de chargement unpacked + debug

Quand tu as fini, liste précisément :
- Les fichiers créés
- Les tests qui passent
- Les décisions d'archi prises
- Les limitations connues
- Les instructions de test manuel pour Mathieu
```
