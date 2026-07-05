# Bloc 8 — Intégration & recette

Tests end-to-end du flux complet et **recette** structurée en gates (S1 → S5).

## Contenu

- Tests E2E (17 pytest) validant l'enchaînement GrilledMe → Persona → génération → planification → publication.
- Script de recette : `scripts/run_recette.sh`.

## Recette — gates

```bash
bash scripts/run_recette.sh
```

| Gate | Critère |
|------|---------|
| S1 | GrilledMe produit un Persona exploitable |
| S2 | Génération d'un post publiable (texte + image) |
| S3 | Publication réelle d'1 post test (worker serveur) |
| S4 | 7 posts sur 7 jours planifiés et publiés |
| S5 | 30 posts, < 5 % d'échecs, 0 ban |

## Dépendances

Nécessite les blocs 1 (backend, port 8000), 3 (génération, 8003) et le worker bloc-9 démarrés.
Voir le [README racine](../README.md) pour le démarrage complet.
