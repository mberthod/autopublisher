# Bloc 6 — Dashboard SvelteKit (port 5173)

Interface utilisateur du système AutoPublisher.

## Pages

| Route | Description |
|-------|-------------|
| `/compose` | **Studio** — génère idées (IA) + publications en masse + planification |
| `/today` | Posts à publier aujourd'hui |
| `/calendar` | Calendrier 30 jours des publications |
| `/analytics` | Tableau des publications + export CSV |
| `/personas` | Gestion des personas (créer, modifier, supprimer) |
| `/grillme` | Créer un persona via 4 questions IA |

## Variables d'env

```env
PUBLIC_API_URL=http://192.168.0.176:8000/api/v1
PUBLIC_GRILLME_URL=http://192.168.0.176:8001/api/v1
PUBLIC_GENERATION_URL=http://192.168.0.176:8003
PUBLIC_CAROUSEL_URL=http://192.168.0.176:8004
```

## Dev

```bash
npm install
npm run dev
```

## Workflow Studio (/compose)

1. Saisir des mots-clés → **Générer 10 idées** (IA)
2. Sélectionner les idées + choisir plateformes (LinkedIn / Instagram)
3. Choisir le format (Texte / Image / Carrousel) + intervalle
4. **Générer en masse** → cartes de preview avec image générée
5. Ajouter un commentaire optionnel → **Regénérer** ou **Valider**
6. L'extension Chrome publie automatiquement aux horaires planifiés
