# Bloc 5 — Extension Chrome (capture de session Instagram)

Extension Chrome Manifest V3.

> **⚠️ L'extension NE PUBLIE PLUS.** Depuis le pivot « publication côté serveur »
> (2026-07-04/05), toute la publication est faite par le worker serveur `bloc-9-publisher`
> (Instagram via instagrapi, LinkedIn page via Unipile). L'extension sert **uniquement** à
> **capturer la session Instagram** (cookies / `sessionid`) et à la remonter au backend,
> pour qu'instagrapi puisse se connecter sans mot de passe, PC éteint.

## Rôle actuel

- Lit les cookies de session Instagram via `chrome.cookies.getAll`
  (`SESSION_DOMAINS` = instagram.com, + linkedin/facebook conservés).
- Les envoie au backend : `POST /api/v1/sessions` (upsert, cookies jamais loggés).
- Déclenché : bouton popup « Synchroniser mes sessions », alarme 30 min, au démarrage.

## Chargement (mode développeur)

1. `chrome://extensions/` → activer **Mode développeur**
2. **Charger l'extension non empaquetée** → dossier `bloc-5-extension/`
3. Être **connecté à Instagram** dans le même profil Chrome
4. Cliquer l'icône → **« Synchroniser mes sessions »**

## Tests unitaires

```bash
cd bloc-5-extension
npm test          # 21 tests (vitest + jsdom)
```

## Architecture (actuelle)

```
background/service-worker.js   ← orchestration, syncSession/syncAllSessions, alarmes
background/api-client.js       ← appels HTTP backend (POST /sessions)
popup/*                        ← UI + bouton « Synchroniser mes sessions »
```

## Endpoints backend utilisés

- `POST /api/v1/sessions`                 ← upsert de la session capturée
- `POST /api/v1/sessions/{platform}/invalidate`

## Code hérité (inutilisé — à nettoyer)

Les voies de publication internes ont toutes été abandonnées et le code correspondant
n'est plus actif :
- `content/linkedin-publisher.js` (API interne Voyager / GraphQL — bloqué 400 anti-automatisation)
- `content/li-capture.js` + `li-capture-relay.js` (intercepteur de payload LinkedIn — debug)
- content scripts de publication DOM Instagram (puits sans fond — remplacés par instagrapi)

`pollAndProcess` est désormais un no-op. À supprimer lors d'un nettoyage ultérieur.
