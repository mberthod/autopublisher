# SaaS RSE Publisher — Extension Chrome

Extension Chrome Manifest V3 qui publie automatiquement des posts depuis le backend SaaS RSE sur LinkedIn et Instagram.

## Chargement (mode développeur)

1. Ouvrir `chrome://extensions/`
2. Activer **Mode développeur** (toggle en haut à droite)
3. Cliquer **Charger l'extension non empaquetée**
4. Sélectionner le dossier `/data/home-mathieu/saas-rse/bloc-5-extension/`
5. L'icône RSE apparaît dans la barre d'extensions

## Prérequis

- Être **connecté à LinkedIn et Instagram** dans le même profil Chrome
- Le backend bloc-1 doit tourner sur `http://192.168.0.176:8000`
- Créer un post avec `status="scheduled"` en BDD pour déclencher la publication

## Paramétrage (URL backend)

Cliquer l'icône → **Paramètres** → modifier l'URL backend → **Sauvegarder**

## Debug

```
chrome://extensions/ → SaaS RSE Publisher → "Inspecter les vues : service worker"
```

Les logs SW sont dans la console du service worker.

Pour les content scripts : ouvrir DevTools sur l'onglet LinkedIn/Instagram.

## Polling manuel

Cliquer **Vérifier maintenant** dans le popup pour forcer un poll immédiat.

Le poll automatique tourne toutes les **5 minutes** via `chrome.alarms`.

## Tests unitaires

```bash
cd bloc-5-extension
npm test
```

6 tests (vitest + jsdom) : human-typer timing + wait-for-element MutationObserver.

## Architecture

```
background/service-worker.js   ← orchestration, polling, alarms
background/api-client.js       ← appels HTTP backend
background/remote-selectors.js ← cache sélecteurs DOM (TTL 6h)
background/task-queue.js       ← queue interne dans chrome.storage.local

content/linkedin-publisher.js  ← publication LinkedIn
content/instagram-publisher.js ← publication Instagram
content/shared/human-typer.js  ← simulation frappe humaine (50-150ms/char)
content/shared/wait-for-element.js ← MutationObserver avec timeout
content/shared/media-uploader.js   ← injection fichier dans <input type="file">

popup/popup.html + .css + .js  ← UI état + "Vérifier maintenant"
```

## Endpoints backend ajoutés (bloc-1-backend)

- `GET  /api/v1/tasks/pending`         ← posts `status=scheduled` dus maintenant
- `POST /api/v1/tasks/{id}/callback`   ← mise à jour succès/échec
- `GET  /api/v1/selectors/latest`      ← sélecteurs DOM version courante
- `GET  /api/v1/selectors/{version}`   ← sélecteurs par version

## Test manuel rapide

```bash
# Créer un post scheduled via l'API
curl -X POST http://192.168.0.176:8000/api/v1/posts \
  -H 'Content-Type: application/json' \
  -d '{
    "planning_id": "<id>",
    "persona_id": "<id>",
    "platform": "linkedin",
    "format": "text_only",
    "angle_editorial": "test",
    "text": "Post de test RSE 🌱",
    "status": "scheduled"
  }'

# Vérifier que l'extension le détecte
# → popup → "Vérifier maintenant"
```

## Limitations connues

- Sélecteurs LinkedIn/Instagram hardcodés pour la locale FR — adapter si compte EN
- Pas de retry dans l'extension (bloc 7 gère les retry côté backend)
- Instagram : flow "Next → Next → Caption" suppose 2 étapes — peut varier selon le layout
- Test sur compte poubelle OBLIGATOIRE avant test sur comptes BU
