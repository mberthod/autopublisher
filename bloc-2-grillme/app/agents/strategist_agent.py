import json
from typing import Any, Optional

from loguru import logger
from openai import OpenAI

from app.agents.base_agent import BaseAgent

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


class StrategistAgent(BaseAgent):
    def __init__(self, client: Optional[OpenAI] = None):
        super().__init__(client)

    def create_persona(self, bu: str, matrix: dict) -> dict[str, Any]:
        system_prompt = STRATEGIST_SYSTEM_PROMPT.replace("{{bu}}", bu).replace(
            "{{matrix}}", json.dumps(matrix, ensure_ascii=False, indent=2)
        )
        user_prompt = "Génère le Persona final à partir de cette matrice."
        logger.bind(bu=bu).info("Strategist: creating persona from matrix")
        raw = self.call(system_prompt, user_prompt)
        result = self.extract_json(raw)

        required_fields = ["nom", "besoins", "frustrations", "cible", "charte_branding"]
        missing = [f for f in required_fields if f not in result]
        if missing:
            raise ValueError(f"Strategist output missing fields: {missing}")

        required_branding = ["ton", "mots_interdits", "emojis_autorises", "structure_phrases", "longueur_cible", "couleurs"]
        missing_branding = [f for f in required_branding if f not in result.get("charte_branding", {})]
        if missing_branding:
            raise ValueError(f"Strategist charte_branding missing fields: {missing_branding}")

        logger.bind(bu=bu, persona_nom=result.get("nom")).info("Strategist: persona created")
        return result
