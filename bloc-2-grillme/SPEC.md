# Bloc 2 — GrilledMe (multi-agents onboarding)

> **Statut** : SPEC à implémenter par Claude Code
> **Owner** : Mathieu (revieweur), Claude Code (implémenteur)
> **Livrable** : Agent conversationnel qui remplit un schéma Persona par discussion, pas par formulaire

---

## 🎯 Objectif

À l'issue d'une discussion chat avec Mathieu, GrilledMe produit un **Persona structuré** (utilisable par le bloc 3 pour générer des posts) en posant des questions ciblées et en challengant les réponses incomplètes.

**Différenciation** : ce n'est PAS un formulaire déguisé en chat. C'est une vraie discussion où l'IA :
- Pose des questions une par une
- Adapte la question suivante en fonction de la réponse précédente
- Challenge les réponses vagues ou incomplètes ("c'est vague, peux-tu me donner un exemple concret ?")
- Ne passe à l'agent Stratège qu'une fois la matrice 100% remplie

---

## 📥 Inputs

```python
# Endpoint 1: démarrer une session d'onboarding
POST /api/v1/grillme/sessions
Body: { "bu": "noisyless" | "afluxo" | "mbhrep" }
Response: { "session_id": "uuid", "first_question": "..." }

# Endpoint 2: envoyer une réponse
POST /api/v1/grillme/sessions/{session_id}/messages
Body: { "user_message": "..." }
Response: {
  "next_question": "..." | null,  # null = matrice remplie, agent Stratège activé
  "matrix_progress": 0.65,         # 0-1
  "current_field": "cible",        # champ en cours de remplissage
  "is_complete": false
}

# Endpoint 3: récupérer le Persona final (une fois is_complete=true)
GET /api/v1/grillme/sessions/{session_id}/persona
Response: { "persona": {...}, "transcript": [...] }
```

---

## 📤 Outputs (Persona final)

```python
{
  "id": "uuid",
  "bu": "noisyless",
  "nom": "Propriétaire Airbnb stressé par le bruit",
  "besoins": "Réduire les nuisances sonores signalées par les locataires, maintenir une note 4.8+",
  "frustrations": "Messages hostiles des voisins, demandes de remboursement, baisse de classement Airbnb",
  "cible": "Propriétaires de locations courte durée en zone urbaine (Paris, Lyon, Marseille), 1-5 biens, 30-55 ans, sensibles à la qualité de l'expérience voyageur",
  "charte_branding": {
    "ton": "professional_warm",
    "mots_interdits": ["cheap", "pas cher", "disrupt", "révolutionnaire"],
    "emojis_autorises": ["✅", "🔧", "📊", "💡"],
    "structure_phrases": "courtes, max 20 mots, voix active",
    "longueur_cible": 1500,
    "couleurs": ["#FF6B35", "#1A1A1A"]
  },
  "transcript_summary": "5 échanges : BU=Noisyless, cible validée, frustrations détaillées, charte confirmée"
}
```

---

## 🏗️ Architecture cible

```
[Mathieu: POST /grillme/sessions {bu: "noisyless"}]
    │
    ▼
[GrillMeService.start_session()]
    │
    ├──► [Crée une session en BDD]
    │   - session_id
    │   - bu
    │   - matrix (JSON vide à remplir)
    │   - transcript (liste vide)
    │   - status: "in_progress"
    │
    └──► [Agent Interrogateur — 1er appel]
         │
         ├──► System prompt: "Tu es GrilledMe, expert en personas marketing.
         │    Tu dois remplir un schéma strict pour {{bu}} : cible, besoins, frustrations, charte.
         │    Tu poses UNE question à la fois.
         │    Tu CHALLENGES les réponses vagues ou incomplètes.
         │    Tu ne passes à la suite que si la réponse est satisfaisante.
         │    Si l'utilisateur dit 'je sais pas', propose 2-3 options."
         │
         ├──► User prompt: "Démarre l'onboarding pour le BU {{bu}}."
         │
         ├──► Appel DeepSeek V4
         │
         └──► Retourne: first_question (str)
              Sauvegarde dans session.transcript
              Retourne au client

[Mathieu répond → POST /grillme/sessions/{id}/messages]
    │
    ▼
[GrillMeService.handle_message()]
    │
    ├──► [Charge la session + transcript]
    │
    ├──► [Agent Interrogateur — 2e appel]
    │   - System prompt: (idem)
    │   - User prompt: "Voici le transcript: ... Quelle est la prochaine question OU la matrice est-elle complète ?"
    │   - Format de sortie demandé (JSON):
    │     {
    │       "matrix_update": {"cible": "..."}  # champ à mettre à jour
    │       "next_question": "..." | null
    │       "is_complete": false | true
    │       "reasoning": "Pourquoi cette question / pourquoi c'est complet"
    │     }
    │
    ├──► [Parse la réponse, update matrix]
    │
    ├──► [Si is_complete=false] → sauvegarde transcript, retourne next_question
    │
    └──► [Si is_complete=true]
         │
         ├──► [Agent Stratège — appelé]
         │   - System prompt: "Tu es un stratège marketing. À partir de cette matrice brute:
         │     {{matrix}}, produis un Persona final structuré et une charte de branding.
         │     Sois précis, concret, actionnable. Pas de généralités."
         │   - User prompt: matrix complète
         │   - Output: Persona JSON structuré
         │
         ├──► [Sauvegarde Persona en BDD via persona_service]
         │
         └──► [Marque session status: "completed", retourne PersonaRead + transcript]
```

---

## 📁 Structure de fichiers

```
/data/home-mathieu/saas-rse/
└── bloc-2-grillme/
    ├── SPEC.md
    ├── README.md
    ├── pyproject.toml
    ├── .env.example
    ├── app/
    │   ├── __init__.py
    │   ├── main.py                       ← FastAPI app (intègre routes GrilledMe)
    │   ├── config.py
    │   ├── models.py                     ← GrilledMeSession
    │   ├── schemas.py                    ← GrilledMeSessionCreate, etc.
    │   ├── db.py
    │   ├── api/
    │   │   ├── __init__.py
    │   │   └── grillme_routes.py
    │   ├── services/
    │   │   ├── __init__.py
    │   │   ├── grillme_service.py        ← orchestration agents
    │   │   └── persona_service.py        ← hérite du bloc 1
    │   └── agents/
    │       ├── __init__.py
    │       ├── base_agent.py             ← wrapper LLM commun
    │       ├── interrogator_agent.py     ← pose les questions
    │       └── strategist_agent.py       ← finalise le Persona
    └── tests/
        ├── conftest.py
        ├── test_interrogator_agent.py    ← tests unitaires
        ├── test_strategist_agent.py
        └── test_grillme_e2e.py           ← bout-en-bout avec LLM mock
```

---

## 🛠️ Dépendances

Ce bloc **dépend du bloc 1** (modèles Persona, services). Réutilise les modèles.

```toml
[project]
name = "saas-rse-grillme"
version = "0.1.0"
description = "Module GrilledMe : onboarding conversationnel multi-agents"
requires-python = ">=3.11,<3.13"
dependencies = [
  "fastapi>=0.115,<1",
  "uvicorn[standard]>=0.32,<1",
  "sqlalchemy>=2.0,<3",
  "pydantic>=2.9,<3",
  "pydantic-settings>=2.6,<3",
  "openai>=1.54,<2",                      # SDK OpenAI pour DeepSeek (compatible)
  "httpx>=0.28,<1",
  "loguru>=0.7,<1",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3,<9",
  "pytest-asyncio>=0.24,<1",
  "pytest-mock>=3.14,<4",
]

[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"
```

---

## 🔑 Variables d'environnement

`.env` (à créer) :
```bash
# DeepSeek
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-v4

# Database (réutilise la DB du bloc 1)
DATABASE_URL=sqlite:///./data/saas_rse.db

# Logging
LOG_LEVEL=INFO
```

---

## 📝 Modèle de données additionnel

Le bloc 2 a besoin d'**un seul modèle** en plus : `GrilledMeSession`. Les autres modèles (Persona, etc.) sont dans le bloc 1.

```python
# app/models.py (à ajouter au modèle du bloc 1)
from sqlalchemy import Column, String, Text, DateTime, JSON, Float

class GrilledMeSession(Base):
    __tablename__ = "grillme_sessions"

    id = Column(String, primary_key=True, default=gen_uuid)
    bu = Column(String, nullable=False)
    status = Column(String, default="in_progress", nullable=False)
    # "in_progress" | "completed" | "abandoned"
    matrix = Column(JSON, default=dict, nullable=False)
    # {"cible": "...", "besoins": "...", "frustrations": "...", "charte": {...}}
    transcript = Column(JSON, default=list, nullable=False)
    # [{"role": "user"|"assistant", "content": "...", "timestamp": "..."}]
    persona_id = Column(String, ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
```

---

## 🤖 System Prompts (CRITIQUES — à ne pas modifier)

### Agent Interrogateur

```python
INTERROGATOR_SYSTEM_PROMPT = """Tu es GrilledMe, un assistant expert en personas marketing.

Objectif : remplir un schéma de persona pour le BU {{bu}} via une discussion.
Le persona final servira à générer des posts sur les réseaux sociaux.

Champs à remplir :
- cible (qui est la personne idéale ?)
- besoins (quels problèmes essaie-t-elle de résoudre ?)
- frustrations (quelles sont ses douleurs quotidiennes ?)
- charte (directives éditoriales : ton, mots interdits, emojis, structure)

Règles strictes :
1. Tu poses UNE seule question à la fois
2. Tu CHALLENGES les réponses vagues : "Peux-tu me donner un exemple concret ?", "Tu peux être plus précis ?"
3. Tu refuses de passer à un autre champ tant que le précédent n'est pas validé
4. Si l'utilisateur dit "je sais pas", propose 2-3 options concrètes pour l'aider
5. Tu ne génères JAMAIS de post ici, tu n'es qu'en mode questionnement
6. Tu ne dépasses JAMAIS 12 échanges au total (sois efficace)
7. Quand la matrice est 100% remplie, retourne is_complete=true avec next_question=null

Format de réponse JSON STRICT :
{
  "matrix_update": { "champ": "valeur mise à jour" } | {},
  "next_question": "ta prochaine question" | null,
  "is_complete": false | true,
  "reasoning": "pourquoi cette question OU pourquoi c'est complet",
  "matrix_progress": 0.0-1.0
}

Contexte actuel :
- Matrice partielle : {{matrix}}
- Transcript : {{transcript}}
"""
```

### Agent Stratège

```python
STRATEGIST_SYSTEM_PROMPT = """Tu es un stratège marketing senior.
À partir de la matrice brute ci-dessous, produis un Persona final structuré et actionnable.

Règles :
- Sois PRÉCIS et CONCRET. Pas de généralités du type "les gens veulent être heureux".
- Le Persona doit être immédiatement utilisable pour générer du contenu RSE.
- La charte de branding doit être cohérente avec le BU {{bu}}.
- longueur_cible : nombre de caractères cible par post (ex: 1500 pour LinkedIn, 500 pour Instagram)
- couleurs : 2-3 couleurs hex dominantes du branding

Format de sortie JSON STRICT (rien d'autre) :
{
  "nom": "Titre court et descriptif du persona (max 100 chars)",
  "besoins": "3-5 besoins concrets, séparés par des points-virgules",
  "frustrations": "3-5 frustrations concrètes, séparées par des points-virgules",
  "cible": "Description démographique ET psychographique (qui, où, âge, comportement)",
  "charte_branding": {
    "ton": "ex: professional_warm | direct | inspirant | technique",
    "mots_interdits": ["liste de mots à ne JAMAIS utiliser"],
    "emojis_autorises": ["liste d'emojis autorisés"],
    "structure_phrases": "ex: courtes max 20 mots voix active",
    "longueur_cible": 1500,
    "couleurs": ["#FF6B35", "#1A1A1A"]
  },
  "transcript_summary": "Résumé en 1 phrase de la discussion"
}

Matrice brute :
{{matrix}}
"""
```

---

## 🧪 Critères d'acceptation

### Tests unitaires

**`test_interrogator_agent.py`** :
- [ ] Avec un transcript vide, l'agent retourne une première question non vide
- [ ] Avec un transcript où la matrice est 25% remplie, l'agent pose la question suivante
- [ ] Avec une matrice complète, l'agent retourne `is_complete=true, next_question=null`
- [ ] Le format de sortie est bien parsable en JSON
- [ ] Le system prompt contient bien le nom du BU

**`test_strategist_agent.py`** :
- [ ] Avec une matrice brute, l'agent retourne un Persona structuré valide
- [ ] Le Persona contient tous les champs obligatoires (nom, besoins, frustrations, cible, charte_branding)
- [ ] La charte_branding contient `ton`, `mots_interdits`, `emojis_autorises`, `structure_phrases`, `longueur_cible`, `couleurs`
- [ ] Le Persona est sauvegardé en BDD (vérifier via DB query)

**`test_grillme_e2e.py`** :
- [ ] POST `/api/v1/grillme/sessions` avec `bu="noisyless"` → 201, session_id + first_question
- [ ] POST message avec "je sais pas" → reçoit 2-3 options (challenge behavior)
- [ ] POST message avec réponse vague ("les gens") → reçoit challenge ("plus précis ?")
- [ ] Enchaîne 8-10 messages en remplissant la matrice → reçoit is_complete=true
- [ ] GET `/grillme/sessions/{id}/persona` après completion → retourne PersonaRead + transcript

### Vérification manuelle

```bash
cd /data/home-mathieu/saas-rse/bloc-2-grillme

# Setup
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# ⚠️ Ce bloc a besoin que le bloc 1 soit fait et la DB initialisée
# Soit tu copies la DB du bloc 1, soit tu importes les modèles du bloc 1

# Lancer
uvicorn app.main:app --reload --port 8001

# Test conversationnel via curl
SESSION_ID=$(curl -s -X POST http://localhost:8001/api/v1/grillme/sessions \
  -H "Content-Type: application/json" \
  -d '{"bu": "noisyless"}' | jq -r .session_id)

# Premier message
curl -X POST http://localhost:8001/api/v1/grillme/sessions/$SESSION_ID/messages \
  -H "Content-Type: application/json" \
  -d '{"user_message": "Je veux cibler les propriétaires Airbnb urbains"}'

# ... continuer la conversation ...

# Quand is_complete=true
curl http://localhost:8001/api/v1/grillme/sessions/$SESSION_ID/persona
```

### Test de qualité (subjectif mais critique)

- [ ] Tu fais un onboarding complet pour Noisyless (~10 messages)
- [ ] Le Persona final te **convainc** : tu le jugerais utilisable par un CM humain ?
- [ ] La charte de branding est cohérente avec le ton que tu utiliserais vraiment
- [ ] Les frustrations sont spécifiques, pas génériques

---

## ⚠️ Points d'attention

1. **Le bloc 1 doit être fait avant**. Ce bloc réutilise les modèles `Persona` du bloc 1. Soit tu importes (`from bloc_1_backend.app.models import Persona`), soit tu copies les modèles (moins propre mais plus simple pour Claude Code).

2. **Coût LLM** : chaque échange = 1 appel LLM. Un onboarding de 10 messages = 11 appels (10 interrogateur + 1 stratège). À $0.001-0.003 par appel, c'est ~$0.02 par onboarding. Négligeable.

3. **Latence** : chaque appel DeepSeek prend 1-3s. Un onboarding complet = ~20-30s. Acceptable.

4. **Validation de la complétude** : c'est l'agent qui décide, pas du code. Donc l'agent peut se tromper (matrice incomplète mais is_complete=true). Phase B = ajouter une vérification post-hoc (regex ou LLM léger).

5. **Max 12 échanges** : l'agent a une consigne stricte de 12 max. Mais c'est dans le system prompt, donc l'agent peut la dépasser. Phase B = hard cap dans le code (refuse le 13e message).

6. **Transcript** : stocke tout le transcript en JSON en BDD. Utile pour debug et pour entraîner des versions futures.

7. **Pas de state machine complexe** : pour la phase A, l'état de la session est en BDD (matrix + transcript). Pas de state machine type XState. Suffisant.

8. **Testing des LLM** : les tests unitaires des agents doivent **mocker l'appel LLM** (pas de vrais appels en CI). Mais le test E2E peut faire un vrai appel (c'est un test d'intégration).

9. **Multi-utilisateurs** : pour la phase A mono-user, pas besoin d'auth ni d'isolation par user. Phase B = ajouter `user_id` à la session.

10. **Pas d'historique de versions** : si tu refais un onboarding pour le même BU, l'ancien Persona est remplacé. Phase B = versioning.

---

## 🔌 Intégration avec les autres blocs

**Ce bloc dépend de** :
- **Bloc 1** : modèles `Persona`, `persona_service.create()`

**Ce bloc est utilisé par** :
- **Bloc 6 (Dashboard)** : page "Onboarding GrilledMe" qui appelle `/api/v1/grillme/sessions`

**Ce bloc n'utilise PAS** : bloc 3, 4, 5, 7 (GrilledMe est en amont de la chaîne de génération)

---

## 🚀 Commandes utiles (pour Mathieu)

```bash
cd /data/home-mathieu/saas-rse/bloc-2-grillme

# Setup
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Importer la DB du bloc 1
# (si bloc-1-backend est déjà fait)
cp ../bloc-1-backend/data/saas_rse.db ./data/saas_rse.db

# Lancer
uvicorn app.main:app --reload --port 8001

# Tests
pytest -v
pytest -v --cov=app

# Test conversationnel
# Voir la section "Vérification manuelle" ci-dessus
```

---

## ❌ Ce que ce bloc ne fait PAS

- ❌ Génération de posts (bloc 3)
- ❌ Génération d'images (bloc 4)
- ❌ Publication (bloc 5)
- ❌ Queue, retry (bloc 7)
- ❌ UI chat (bloc 6, dashboard, mais un simple textarea suffit)
- ❌ Multi-utilisateurs (phase B)
- ❌ Versioning des Personas (phase B)
- ❌ Hard cap des échanges (phase B)
- ❌ Validation post-hoc de la complétude (phase B)

---

## 🤖 Prompt pour Claude Code

```
Lis ce fichier SPEC.md en entier. Implémente le bloc 2 (GrilledMe multi-agents)
dans /data/home-mathieu/saas-rse/bloc-2-grillme/.

Règles strictes :
1. Le bloc 1 (backend + modèles) DOIT être fait avant. Si ce n'est pas le cas,
   copie les modèles Persona dans ce bloc (avec mention en commentaire)
2. Les system prompts du SPEC sont STRICTS — ne les modifie pas
3. Format JSON strict en sortie des agents (parsing obligatoire)
4. Tests unitaires MOCKENT l'appel LLM (pas de vrais appels en CI)
5. Test E2E peut faire un vrai appel LLM (c'est un test d'intégration)
6. Logs structurés loguru avec session_id dans le contexte
7. Pas de state machine, juste BDD (matrix + transcript)
8. README avec procédure de test conversationnel manuel

Quand tu as fini, liste précisément :
- Les fichiers créés
- Les tests qui passent
- Les décisions d'archi prises
- Les limitations connues
- Un exemple de transcript complet (réel) pour validation
```
