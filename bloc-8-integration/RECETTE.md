# Recette manuelle — Phase A SaaS RSE

> Procédure à exécuter par Mathieu à la fin de chaque gate hebdomadaire.

---

## Pré-requis

Tous les services doivent tourner :
```bash
# Vérification rapide
bash /data/home-mathieu/saas-rse/bloc-8-integration/scripts/run_recette.sh
```

---

## Gate S1 — Semaine 1 : GrilledMe → Persona qualifié

**Critère de succès** : GrilledMe produit un Persona qui te convainc pour Noisyless.

```bash
# 1. Démarrer une session
SESSION=$(curl -s -X POST http://localhost:8001/api/v1/grillme/sessions \
  -H "Content-Type: application/json" \
  -d '{"bu":"noisyless"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

echo "Session: $SESSION"

# 2. Envoyer un message (répéter 8-12 fois avec tes vraies réponses)
curl -s -X POST "http://localhost:8001/api/v1/grillme/sessions/$SESSION/messages" \
  -H "Content-Type: application/json" \
  -d '{"user_message": "TA RÉPONSE ICI"}'

# 3. Récupérer le persona une fois is_complete=true
curl -s "http://localhost:8001/api/v1/grillme/sessions/$SESSION/persona" | python3 -m json.tool
```

**Validation subjective :**
- [ ] Le `nom` est-il descriptif et précis ?
- [ ] Les `besoins` sont-ils concrets, pas génériques ?
- [ ] Les `frustrations` sont-elles spécifiques à ton marché ?
- [ ] La `charte_branding` est-elle utilisable (ton, mots_interdits, longueur) ?
- [ ] Ce persona te représente-t-il fidèlement ta clientèle cible ?

**Si KO** : itérer sur les prompts de `bloc-2-grillme/app/agents/interrogator_agent.py`.

---

## Gate S2 — Semaine 2 : Persona → Post publiable

**Critère** : 1 post généré est publiable sans modification.

```bash
# Récupère les IDs depuis la BDD
PERSONA_ID=$(curl -s http://localhost:8000/api/v1/personas | python3 -c \
  "import sys,json; ps=json.load(sys.stdin); print(ps[0]['id']) if ps else print('')")
PLANNING_ID=$(curl -s http://localhost:8000/api/v1/plannings | python3 -c \
  "import sys,json; ps=json.load(sys.stdin); print(ps[0]['id']) if ps else print('')")

# Générer un post
curl -s -X POST http://localhost:8003/api/v1/posts/generate \
  -H "Content-Type: application/json" \
  -d "{
    \"planning_id\": \"$PLANNING_ID\",
    \"persona_id\": \"$PERSONA_ID\",
    \"angle_editorial\": \"Les 5 sources de bruit sous-estimées en location courte durée\",
    \"format\": \"image\",
    \"platform\": \"linkedin\"
  }" | python3 -m json.tool
```

**Validation subjective :**
- [ ] Le texte est-il cohérent avec le Persona (ton, vocabulaire, longueur) ?
- [ ] L'image est-elle pertinente (ouvrir l'URL `image_url`) ?
- [ ] Tu publierais ce post tel quel sur ton compte pro ?

---

## Gate S3 — Semaine 3 : Extension publie 1 post sur compte test

**Critère** : l'extension publie automatiquement 1 post LinkedIn (compte TEST, pas BU).

**Prérequis** : créer un compte LinkedIn et un compte Instagram de test.

```bash
# 1. Créer un post scheduled pour aujourd'hui
POST_ID=$(curl -s -X POST http://localhost:8000/api/v1/posts \
  -H "Content-Type: application/json" \
  -d "{
    \"planning_id\": \"$PLANNING_ID\",
    \"persona_id\": \"$PERSONA_ID\",
    \"platform\": \"linkedin\",
    \"format\": \"text_only\",
    \"angle_editorial\": \"Test Gate S3\"
  }" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 2. Lui donner un texte et le scheduler pour maintenant
curl -s -X PATCH "http://localhost:8000/api/v1/posts/$POST_ID" \
  -H "Content-Type: application/json" \
  -d "{
    \"text\": \"Test automatique SaaS RSE — Gate S3 ✅\",
    \"status\": \"scheduled\",
    \"scheduled_for\": \"$(date -u +%Y-%m-%dT%H:%M:%S)\"
  }"

# 3. Dans le popup de l'extension → "Vérifier maintenant"
# 4. Attendre < 5 min → vérifier LinkedIn

# 5. Vérifier en BDD
curl -s "http://localhost:8000/api/v1/posts/$POST_ID" | \
  python3 -c "import sys,json; p=json.load(sys.stdin); print('status:', p['status'], '| url:', p['published_url'])"
```

**Validation :**
- [ ] Le post est visible sur LinkedIn (compte test)
- [ ] `status = "published"` en BDD
- [ ] `published_url` est renseigné

---

## Gate S4 — Semaines 4-5 : 7 posts en 7 jours

**Critère** : 7 posts publiés sur 7 jours en rotation entre les 3 BU.

```bash
# Vérifier l'état des publications
sqlite3 /data/home-mathieu/saas-rse/bloc-1-backend/data/saas_rse.db \
  "SELECT date(published_at), platform, status, COUNT(*) FROM posts
   WHERE status='published'
   GROUP BY date(published_at), platform
   ORDER BY published_at DESC
   LIMIT 20;"
```

**Validation :**
- [ ] 7 entrées en 7 jours dans la requête ci-dessus
- [ ] Au moins 2 BU différentes représentées
- [ ] 0 intervention manuelle sur ces posts

---

## Gate S5 — Semaine 6 : 30 posts, <5% échecs, 0 ban

**Critère final Phase A.**

```bash
bash /data/home-mathieu/saas-rse/bloc-8-integration/scripts/run_recette.sh
```

Ou manuellement :
```bash
DB="/data/home-mathieu/saas-rse/bloc-1-backend/data/saas_rse.db"

sqlite3 "$DB" "
SELECT
  status,
  COUNT(*) as count
FROM posts
GROUP BY status;"

# Vérifier 0 ban :
# → Aller sur linkedin.com et instagram.com avec les comptes BU
# → Vérifier qu'ils sont accessibles et non restreints
```

**Validation Gate S5 :**
- [ ] `published >= 30`
- [ ] `failed / (published + failed) < 5%`
- [ ] Comptes LinkedIn Noisyless, Afluxo, MBHREP : non bannis
- [ ] 0 post publié manuellement (tout passe par l'extension)

**→ Phase A réussie ! Passage en Phase B.**
