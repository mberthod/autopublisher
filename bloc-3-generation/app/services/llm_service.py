import json
import re
from typing import Optional

from loguru import logger
from openai import OpenAI

from app.config import settings
from app.models import Persona

PLATFORM_LENGTH = {
    "linkedin": "1300 à 2000 caractères",
    "instagram": "200 à 500 caractères",
}

SYSTEM_PROMPT_TEMPLATE = """Tu es un community manager RSE expert pour {bu}.

Tu écris pour cette cible : {cible}

Persona — besoins : {besoins}
Persona — frustrations : {frustrations}

Charte éditoriale :
- Ton : {ton}
- Mots INTERDITS (ne jamais utiliser) : {mots_interdits}
- Emojis autorisés : {emojis_autorises}
- Structure des phrases : {structure_phrases}

Règles strictes :
1. N'utilise JAMAIS les mots interdits
2. Utilise uniquement les emojis autorisés, avec parcimonie
3. Le texte doit parler directement à la cible, pas d'elle
4. Pas de hashtags génériques (#RSE #développementdurable)
5. Termine par un appel à l'action concret et court"""

USER_PROMPT_TEMPLATE = """Écris un post {platform} sur cet angle éditorial : {angle_editorial}

Longueur cible : {longueur} caractères.
Format du post : {format}.

Retourne UNIQUEMENT le texte du post, sans explication ni commentaire."""

IDEAS_SYSTEM = """Tu es un stratège de contenu RSE expert pour {bu}.

Cible : {cible}
Besoins : {besoins}
Frustrations : {frustrations}

Génère des angles éditoriaux originaux, concrets et engageants.
Réponds UNIQUEMENT avec ce JSON (rien d'autre, pas de markdown) :
{{"ideas": [{{"angle": "titre accrocheur en 1 phrase percutante", "rationale": "pourquoi ça engage cette cible", "platform": "linkedin"}}]}}
"""


class LLMService:
    def __init__(self, client: Optional[OpenAI] = None):
        self._client = client or OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
        self.model = settings.deepseek_model

    def generate_text(self, persona: Persona, angle_editorial: str, platform: str, format: str) -> dict:
        charte = persona.charte_branding or {}
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            bu=persona.bu,
            cible=persona.cible,
            besoins=persona.besoins,
            frustrations=persona.frustrations,
            ton=charte.get("ton", "professional"),
            mots_interdits=", ".join(charte.get("mots_interdits", [])),
            emojis_autorises=" ".join(charte.get("emojis_autorises", [])),
            structure_phrases=charte.get("structure_phrases", "phrases courtes"),
        )
        user_prompt = USER_PROMPT_TEMPLATE.format(
            platform=platform,
            angle_editorial=angle_editorial,
            longueur=PLATFORM_LENGTH.get(platform, "1000 à 1500"),
            format=format,
        )

        logger.bind(persona_id=persona.id, platform=platform).info("LLM text generation started")

        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.8,
        )

        text = response.choices[0].message.content or ""
        usage = response.usage

        logger.bind(persona_id=persona.id, chars=len(text)).info("LLM text generation done")

        return {
            "text": text.strip(),
            "tokens_in": usage.prompt_tokens if usage else 0,
            "tokens_out": usage.completion_tokens if usage else 0,
            "model": self.model,
        }

    def generate_ideas(self, persona: Persona, keywords: str, platform: str, n: int = 10) -> list[dict]:
        system = IDEAS_SYSTEM.format(
            bu=persona.bu,
            cible=persona.cible,
            besoins=persona.besoins,
            frustrations=persona.frustrations,
        )
        plat_str = "LinkedIn ET Instagram" if platform == "both" else platform
        user = (
            f"Génère exactement {n} angles éditoriaux pour les mots-clés : {keywords}\n"
            f"Adapte pour : {plat_str}\n"
            f"Chaque angle doit être distinct, actionnable et parlant pour la cible.\n"
            f"Retourne EXACTEMENT {n} idées dans le tableau JSON."
        )
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.95,
        )
        raw = response.choices[0].message.content or ""
        logger.bind(n=n, raw_len=len(raw)).info("LLM ideas generation done")
        try:
            data = json.loads(raw)
        except Exception:
            m = re.search(r'\{[\s\S]*\}', raw)
            if not m:
                return []
            try:
                data = json.loads(m.group())
            except Exception:
                return []
        return data.get("ideas", [])
