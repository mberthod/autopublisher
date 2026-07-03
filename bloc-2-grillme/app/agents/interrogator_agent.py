import json
from typing import Any, Optional

from loguru import logger
from openai import OpenAI

from app.agents.base_agent import BaseAgent

MATRIX_FIELDS = ["cible", "besoins", "frustrations", "charte"]

FIELD_QUESTIONS = {
    "cible":       "Qui est ta cible idéale pour ce BU ? (âge, profession, contexte de vie)",
    "besoins":     "Quels sont les principaux besoins ou problèmes que cette personne cherche à résoudre ?",
    "frustrations":"Quelles sont ses frustrations ou douleurs quotidiennes ?",
    "charte":      "Quelle charte éditoriale veux-tu pour tes posts ? (ton, mots à éviter, longueur, emojis oui/non)",
}

EXTRACT_PROMPT = """Tu es un assistant qui extrait et synthétise une information.

Champ à remplir : {field}
Question posée : {question}
Réponse de l'utilisateur : {user_message}

Retourne UNIQUEMENT un JSON avec la valeur synthétisée (entre 10 et 100 mots, en français) :
{{"value": "valeur synthétisée"}}

Si la réponse est vague, enrichis-la avec du contexte pertinent basé sur le BU {bu}.
"""


class InterrogatorAgent(BaseAgent):
    def __init__(self, client: Optional[OpenAI] = None):
        super().__init__(client)

    def get_first_question(self, bu: str) -> str:
        return FIELD_QUESTIONS["cible"]

    def extract_field_value(self, bu: str, field: str, user_message: str) -> str:
        prompt = EXTRACT_PROMPT.format(
            field=field,
            question=FIELD_QUESTIONS[field],
            user_message=user_message,
            bu=bu,
        )
        raw = self.call(prompt, "Extrais et synthétise la valeur.")
        try:
            result = self.extract_json(raw)
            return str(result.get("value", user_message))
        except Exception:
            return user_message

    def get_next_question(self, next_field: str) -> str:
        return FIELD_QUESTIONS.get(next_field, "")
