import json
from typing import Any, Optional

from loguru import logger
from openai import OpenAI

from app.agents.base_agent import BaseAgent

MATRIX_FIELDS = ["cible", "besoins", "frustrations", "charte"]

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
  "matrix_update": { "champ": "valeur mise à jour" },
  "next_question": "ta prochaine question" | null,
  "is_complete": false | true,
  "reasoning": "pourquoi cette question OU pourquoi c'est complet",
  "matrix_progress": 0.0
}

Contexte actuel :
- Matrice partielle : {{matrix}}
- Transcript : {{transcript}}
"""


class InterrogatorAgent(BaseAgent):
    def __init__(self, client: Optional[OpenAI] = None):
        super().__init__(client)

    def _build_system_prompt(self, bu: str, matrix: dict, transcript: list) -> str:
        return (
            INTERROGATOR_SYSTEM_PROMPT
            .replace("{{bu}}", bu)
            .replace("{{matrix}}", json.dumps(matrix, ensure_ascii=False))
            .replace("{{transcript}}", json.dumps(transcript, ensure_ascii=False))
        )

    def start_session(self, bu: str) -> dict[str, Any]:
        system_prompt = self._build_system_prompt(bu, {}, [])
        user_prompt = f"Démarre l'onboarding pour le BU {bu}. Pose ta première question."
        logger.bind(bu=bu).info("Interrogator: starting session")
        raw = self.call(system_prompt, user_prompt)
        result = self.extract_json(raw)
        logger.bind(bu=bu, is_complete=result.get("is_complete")).info("Interrogator: session started")
        return result

    def process_message(self, bu: str, matrix: dict, transcript: list, user_message: str) -> dict[str, Any]:
        transcript_with_new = transcript + [{"role": "user", "content": user_message}]
        system_prompt = self._build_system_prompt(bu, matrix, transcript_with_new)
        user_prompt = f"L'utilisateur a répondu : {user_message}\n\nQuelle est ta prochaine action ?"
        logger.bind(bu=bu, matrix_keys=list(matrix.keys())).info("Interrogator: processing message")
        raw = self.call(system_prompt, user_prompt)
        result = self.extract_json(raw)
        logger.bind(bu=bu, is_complete=result.get("is_complete"), progress=result.get("matrix_progress")).info("Interrogator: message processed")
        return result
