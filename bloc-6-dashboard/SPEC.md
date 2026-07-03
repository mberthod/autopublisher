# Bloc 6 — Dashboard (3 pages : Today / Calendar / Analytics)

> **Statut** : SPEC à implémenter par Claude Code
> **Owner** : Mathieu (revieweur wireframe + UX), Claude Code (implémenteur)
> **Livrable** : Dashboard web 3 pages, ultra-simple, qui consomme l'API du bloc 1

---

## 🎯 Objectif

Dashboard web minimal qui te permet de :
1. **Today** : voir ce qui doit être publié aujourd'hui, sur quel réseau, dans quel état
2. **Calendar** : voir le planning éditorial (N jours) avec tous les posts à venir
3. **Analytics** : voir les stats des posts publiés (likes, comments, vues, reach)

**Pas dans ce scope** (phase B+) : édition de persona, onboarding GrilledMe dans le dashboard (CLI ou API seulement pour la phase A), multi-user, graphiques avancés.

---

## 📥 Inputs

Le dashboard **consomme uniquement l'API du bloc 1** (et indirectement les autres blocs via les statuts des posts).

Endpoints API utilisés :
- `GET /api/v1/posts?status=...&scheduled_for_after=...` (bloc 1)
- `GET /api/v1/personas` (bloc 1)
- `GET /api/v1/plannings` (bloc 1)
- `PATCH /api/v1/posts/{id}` (bloc 1, pour valider un draft)

---

## 📤 Outputs

3 pages HTML rendues côté serveur (ou SPA) :
- `/` → redirige vers `/today`
- `/today` → posts à publier aujourd'hui
- `/calendar` → planning éditorial
- `/analytics` → stats des posts publiés

---

## 🏗️ Architecture cible

### Choix framework : **SvelteKit**

**Pourquoi SvelteKit et pas React/Next.js** :
- Plus léger (compilateur, pas runtime)
- SSR/SSG intégré, parfait pour un dashboard interne
- Syntaxe plus concise (moins de boilerplate)
- Build plus rapide

**Si l'équipe préfère React** : Next.js est OK aussi, mais le SPEC est écrit pour SvelteKit.

### Structure

```
[Navigateur: http://192.168.0.176:8000/dashboard]
    │
    ▼
[SvelteKit frontend (port 5173 dev, ou intégré au backend en prod)]
    │
    ├──► [Page /today]
    │   1. Charger posts où scheduled_for est aujourd'hui et status != 'published'
    │   2. Afficher : BU, plateforme, format, texte, image, bouton "Valider"
    │   3. Bouton "Valider" → PATCH /api/v1/posts/{id} {status: "validated"}
    │
    ├──► [Page /calendar]
    │   1. Charger tous les posts des 30 prochains jours
    │   2. Afficher en grille : colonne = jour, ligne = BU
    │   3. Couleurs par statut : gris (draft), jaune (validated), vert (published), rouge (failed)
    │
    └──► [Page /analytics]
        1. Charger tous les posts status='published'
        2. Afficher tableau : date, BU, plateforme, reach, likes, comments
        3. ⚠️ Phase A : ces données ne sont PAS scrapées (c'est phase B+)
           → Afficher juste un message "Analytics disponibles en phase B"
```

---

## 📁 Structure de fichiers

```
/data/home-mathieu/saas-rse/
└── bloc-6-dashboard/
    ├── SPEC.md
    ├── README.md
    ├── package.json
    ├── svelte.config.js
    ├── vite.config.js
    ├── tsconfig.json                      ← TypeScript
    ├── .env.example
    ├── src/
    │   ├── app.html
    │   ├── app.css
    │   ├── lib/
    │   │   ├── api.ts                     ← client HTTP typé vers l'API bloc 1
    │   │   ├── types.ts                   ← types TypeScript (Persona, Post, etc.)
    │   │   ├── components/
    │   │   │   ├── PostCard.svelte
    │   │   │   ├── PostList.svelte
    │   │   │   ├── StatusBadge.svelte
    │   │   │   ├── PlatformIcon.svelte
    │   │   │   └── NavBar.svelte
    │   │   └── stores/
    │   │       └── posts.ts               ← store Svelte pour les posts
    │   └── routes/
    │       ├── +layout.svelte             ← navbar globale
    │       ├── +page.svelte               ← redirect vers /today
    │       ├── today/
    │       │   └── +page.svelte
    │       ├── calendar/
    │       │   └── +page.svelte
    │       └── analytics/
    │           └── +page.svelte
    └── static/
        └── favicon.png
```

---

## 🛠️ Dépendances

```json
// package.json
{
  "name": "saas-rse-dashboard",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite dev",
    "build": "vite build",
    "preview": "vite preview",
    "check": "svelte-kit sync && svelte-check --tsconfig ./tsconfig.json"
  },
  "devDependencies": {
    "@sveltejs/adapter-auto": "^3.0.0",
    "@sveltejs/kit": "^2.0.0",
    "@sveltejs/vite-plugin-svelte": "^3.0.0",
    "svelte": "^4.0.0",
    "svelte-check": "^3.6.0",
    "typescript": "^5.0.0",
    "vite": "^5.0.0",
    "tslib": "^2.4.1"
  },
  "dependencies": {
    "date-fns": "^3.0.0"
  }
}
```

---

## 🔑 Variables d'environnement

`.env` :
```bash
# URL de l'API backend (bloc 1)
PUBLIC_API_URL=http://localhost:8000/api/v1

# En dev, le frontend tourne sur 5173 et appelle l'API en 8000
# En prod (build), on intègre le frontend dans le backend (ou reverse proxy)
```

---

## 🎨 Wireframes (ASCII)

### Page `/today`
```
┌────────────────────────────────────────────────────┐
│ SaaS RSE        [Today] [Calendar] [Analytics]    │
├────────────────────────────────────────────────────┤
│ Aujourd'hui : 15 juillet 2026                      │
│ 3 posts à publier                                 │
│                                                    │
│ ┌────────────────────────────────────────────┐  │
│ │ [Noisyless] [LinkedIn] [Image]    [draft]  │  │
│ │ "5 sources de bruit que vos locataires..." │  │
│ │ [Voir image]  [Valider] [Modifier] [Suppr] │  │
│ └────────────────────────────────────────────┘  │
│                                                    │
│ ┌────────────────────────────────────────────┐  │
│ │ [Afluxo] [Instagram] [Carousel] [draft]    │  │
│ │ "3 métriques que les retailers oublient"   │  │
│ │ [Voir carrousel]  [Valider] [Modifier]     │  │
│ └────────────────────────────────────────────┘  │
│                                                    │
│ ┌────────────────────────────────────────────┐  │
│ │ [MBHREP] [LinkedIn] [Text only] [failed]   │  │
│ │ "Bureau d'études hardware : nos 5 services" │  │
│ │ ⚠️ Erreur: AUTH_REQUIRED                   │  │
│ │ [Voir erreur]  [Retry] [Suppr]             │  │
│ └────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────┘
```

### Page `/calendar`
```
┌────────────────────────────────────────────────────────────┐
│ SaaS RSE        [Today] [Calendar] [Analytics]           │
├────────────────────────────────────────────────────────────┤
│ Planning : 1-30 juillet 2026                                │
│ Filtres : BU=All | Plateforme=All | Statut=All             │
│                                                             │
│              Lun 15  Mar 16  Mer 17  Jeu 18  Ven 19       │
│ Noisyless   [📷L]  [📝L]  [ ]    [📷I]  [ ]              │
│ Afluxo      [ ]    [📝L]  [📸I]  [ ]    [ ]              │
│ MBHREP      [📷L]  [ ]    [ ]    [ ]    [📝L]             │
│                                                             │
│ Légende : 📝=text 📷=image 📸=carousel                     │
│           L=LinkedIn  I=Instagram                          │
│           [ ]=draft [V]=validated [P]=published [F]=failed │
└────────────────────────────────────────────────────────────┘
```

### Page `/analytics`
```
┌────────────────────────────────────────────────────┐
│ SaaS RSE        [Today] [Calendar] [Analytics]    │
├────────────────────────────────────────────────────┤
│ Posts publiés (30 derniers jours)                  │
│                                                    │
│ ⚠️ Analytics scraping disponible en phase B        │
│                                                    │
│ Pour l'instant, voici la liste des posts publiés :│
│                                                    │
│ Date       BU          Plateforme   Statut         │
│ 10/07      Noisyless   LinkedIn     ✓ Publié      │
│ 12/07      Afluxo      Instagram    ✓ Publié      │
│ 14/07      MBHREP      LinkedIn     ✗ Échec       │
│                                                    │
│ [Export CSV]                                       │
└────────────────────────────────────────────────────┘
```

---

## 🧪 Critères d'acceptation

### Tests manuels (pas de tests automatisés requis pour la phase A)

- [ ] `npm run dev` démarre le serveur sur `http://localhost:5173`
- [ ] Page `/` redirige vers `/today`
- [ ] Page `/today` charge et affiche les posts du jour (3 BU × 1 post = 3 cards)
- [ ] Cliquer "Valider" sur un post → status passe à "validated" en BDD
- [ ] Page `/calendar` affiche la grille 30 jours × 3 BU
- [ ] Cliquer un post dans le calendar → ouvre une modale avec détails
- [ ] Page `/analytics` affiche un message "phase B" + tableau des posts publiés
- [ ] Navigation entre les 3 pages fonctionne (navbar cliquable)
- [ ] Les erreurs API sont affichées proprement (toast ou alert)
- [ ] TypeScript compile sans erreur (`npm run check`)

### Vérification visuelle

- [ ] Le design est propre, lisible, professionnel
- [ ] Les couleurs de statut sont cohérentes (gris/jaune/vert/rouge)
- [ ] Les icônes de plateforme (LinkedIn bleu, Instagram gradient) sont reconnaissables
- [ ] Le dashboard est utilisable sur mobile (responsive, breakpoints simples)

---

## ⚠️ Points d'attention

1. **Pas d'auth dans ce bloc** : on est en LAN mono-user, pas de login. Si le user a accès à l'IP, il voit le dashboard.

2. **CORS** : le frontend (port 5173) doit pouvoir appeler l'API (port 8000). Configure CORS dans le backend (bloc 1) :
   ```python
   # Dans bloc-1-backend/app/main.py
   from fastapi.middleware.cors import CORSMiddleware

   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:5173", "http://192.168.0.176:5173"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

3. **Pas d'édition de persona dans ce bloc** : pour la phase A, tu utilises GrilledMe via curl/API. L'édition via dashboard est phase B.

4. **Pas d'onboarding GrilledMe dans ce bloc** : idem, c'est CLI/API pour la phase A. Phase B = page chat dans le dashboard.

5. **Analytics placeholder** : la page analytics est vide pour la phase A. Affiche juste un message "disponible en phase B" + un tableau des posts publiés (sans stats).

6. **Pas de state management complexe** : utilise les stores Svelte natifs. Pas de Redux/Zustand/Pinia.

7. **Pas de router guards** : pas d'auth, pas de guards.

8. **Pas de tests E2E** (Playwright, Cypress) : trop de complexité pour la phase A. Validation manuelle suffit.

9. **Build de production** : `npm run build` produit un dossier `build/` que tu peux servir via un reverse proxy (Caddy/Nginx). Pour la phase A, le dev mode suffit.

10. **Hot reload** : en dev, SvelteKit hot-reload automatiquement. Tu vois les changements en direct.

---

## 🔌 Intégration avec les autres blocs

**Ce bloc dépend de** :
- **Bloc 1** : endpoints `/api/v1/posts`, `/api/v1/personas`, `/api/v1/plannings`

**Ce bloc est utilisé par** :
- Toi (Mathieu) pour la visu
- **Bloc 8 (intégration)** : tests de bout-en-bout

**Ce bloc n'utilise PAS** : bloc 2 (GrilledMe), 3 (génération), 4 (carrousels), 5 (extension), 7 (queue)

---

## 🚀 Commandes utiles (pour Mathieu)

```bash
cd /data/home-mathieu/saas-rse/bloc-6-dashboard

# Setup
npm install

# Dev
npm run dev
# Ouvre http://localhost:5173

# Type check
npm run check

# Build de prod
npm run build
npm run preview
```

---

## ❌ Ce que ce bloc ne fait PAS

- ❌ Édition de persona (phase B)
- ❌ Onboarding GrilledMe via chat (phase B)
- ❌ Scraping analytics (phase B+)
- ❌ Auth, multi-user (phase B)
- ❌ Notifications temps réel (SSE/WebSocket, phase B)
- ❌ Drag-and-drop de posts dans le calendar (phase B)
- ❌ Preview des carrousels Instagram (phase B)
- ❌ Tests E2E automatisés (phase B)

---

## 🤖 Prompt pour Claude Code

```
Lis ce fichier SPEC.md en entier. Implémente le bloc 6 (dashboard SvelteKit 3 pages)
dans /data/home-mathieu/saas-rse/bloc-6-dashboard/.

Règles strictes :
1. SvelteKit + TypeScript strict
2. Demande confirmation avant toute décision d'archi non couverte
3. 3 pages : /today, /calendar, /analytics (wireframes dans le SPEC)
4. Consomme l'API du bloc 1 (URL via PUBLIC_API_URL)
5. Pas d'auth, pas de router guards
6. Hot reload fonctionnel (vite dev)
7. CORS doit être géré côté backend (note dans le README, pas dans ce bloc)
8. TypeScript types stricts pour Persona, Post, Planning
9. Design propre et responsive (utilise Tailwind ou CSS pur au choix, JUSTIFIE)
10. Pas de tests automatisés (validation manuelle suffit phase A)

Quand tu as fini, liste précisément :
- Les fichiers créés
- Le design framework utilisé (Tailwind / CSS pur) et pourquoi
- Les 3 pages livrées (description visuelle)
- Les décisions d'archi prises
- Les limitations connues
- Les instructions de test manuel pour Mathieu
```
