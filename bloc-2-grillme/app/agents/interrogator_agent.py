import json
from typing import Optional

from loguru import logger
from openai import OpenAI

from app.agents.base_agent import BaseAgent

INTERROGATOR_SYSTEM = """Tu es GrilledMe, un expert en stratégie de contenu et personas marketing.

Objectif : remplir un schéma de persona pour le BU {bu} via une discussion naturelle.
Le persona final servira à générer des posts ultra-engageants sur LinkedIn et Instagram.

Champs à remplir :
- cible : qui est la personne idéale ? âge, profession, contexte de vie, localisation
- besoins : quels problèmes essaie-t-elle de résoudre ? quels objectifs ?
- frustrations : ses douleurs quotidiennes, ce qui l'empêche de dormir
- charte : directives éditoriales — ton, mots interdits, emojis oui/non, longueur des posts, couleurs

Règles STRICTES :
1. Pose UNE seule question à la fois
2. CHALLENGE les réponses vagues : "C'est encore trop général, tu peux être plus précis ?"
3. Si l'utilisateur répond "je sais pas" ou "je ne sais pas", propose 2-3 exemples concrets
4. Ne passe à un autre champ que quand le précédent est suffisamment précis (min 20 mots)
5. Ne génère JAMAIS de post ici — tu es en mode questionnement uniquement
6. Maximum 12 échanges au total — sois efficace
7. Quand tous les champs sont remplis avec des réponses précises, retourne is_complete=true
8. Pour la charte, pose des sous-questions : ton souhaité, mots à bannir, emojis ok ?, longueur cible

Contexte actuel :
- BU : {bu}
- Matrice : {matrix_json}
- Transcript (dernier échanges) : {transcript_json}
- Échanges utilisés : {exchange_count}/12

IMPORTANT : Retourne UNIQUEMENT un JSON valide, sans markdown, sans texte avant/après :
{{
  "matrix_update": {{"champ": "valeur enrichie et précise"}},
  "next_question": "ta prochaine question" ou null si complet,
  "is_complete": false ou true,
  "reasoning": "pourquoi cette question ou pourquoi c'est complet",
  "matrix_progress": 0.0 à 1.0
}}"""


class InterrogatorAgent(BaseAgent):
    def __init__(self, client: Optional[OpenAI] = None):
        super().__init__(client)

    def start_session(self, bu: str) -> dict:
        """Première question posée au démarrage d'une session."""
        system = INTERROGATOR_SYSTEM.format(
            bu=bu,
            matrix_json="{}",
            transcript_json="[]",
            exchange_count=0,
        )
        user = f"Démarre l'onboarding pour le BU '{bu}'. Pose ta première question pour connaître la cible idéale."
        raw = self.call(system, user)
        result = self.extract_json(raw)
        self._validate(result)
        return result

    def process_message(self, bu: str, matrix: dict, transcript: list, user_message: str) -> dict:
        """Traite une réponse utilisateur et décide de la suite."""
        exchange_count = sum(1 for t in transcript if t.get("role") == "user")
        # Only send last 6 exchanges to keep prompt short
        recent_transcript = transcript[-12:]
        system = INTERROGATOR_SYSTEM.format(
            bu=bu,
            matrix_json=json.dumps(matrix, ensure_ascii=False),
            transcript_json=json.dumps(recent_transcript, ensure_ascii=False),
            exchange_count=exchange_count,
        )
        user = f'L\'utilisateur vient de répondre : "{user_message}"\n\nAnalyse sa réponse. Si précise, extrais la valeur et passe à la suite. Si vague, challenge-le.'
        raw = self.call(system, user)
        result = self.extract_json(raw)
        self._validate(result)
        return result

    def _validate(self, result: dict) -> None:
        required = ["matrix_update", "next_question", "is_complete", "reasoning", "matrix_progress"]
        missing = [k for k in required if k not in result]
        if missing:
            raise ValueError(f"Missing fields in interrogator response: {missing}")
        if result["is_complete"] and result["next_question"] is not None:
            raise ValueError("is_complete=true but next_question is not null")
        if not result["is_complete"] and result["next_question"] is None:
            raise ValueError("is_complete=false but next_question is null")
