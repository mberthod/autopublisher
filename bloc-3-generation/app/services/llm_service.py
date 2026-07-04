import json
import re
from typing import Optional

from loguru import logger
from openai import OpenAI
from sqlalchemy import text as sql_text

from app.config import settings
from app.models import Persona


def load_positioning(bu: str) -> dict:
    """Lit le positionnement éditable de la BU (table positionings, DB partagée)."""
    try:
        from app.db import engine
        with engine.connect() as conn:
            row = conn.execute(
                sql_text("SELECT content, keywords FROM positionings WHERE bu = :bu"),
                {"bu": bu},
            ).first()
            if row:
                return {"content": (row[0] or "").strip(), "keywords": (row[1] or "").strip()}
    except Exception as e:
        logger.warning(f"positionnement indisponible pour {bu}: {e}")
    return {"content": "", "keywords": ""}


def _positioning_block(content: str) -> str:
    if not content:
        return ""
    return (
        "\n=== POSITIONNEMENT DE RÉFÉRENCE (source de vérité — appuie-toi dessus) ===\n"
        f"{content}\n"
        "=== FIN POSITIONNEMENT ===\n"
        "Ancre chaque contenu dans ce positionnement : reste fidèle à la cible, à la douleur "
        "concrète, à la différenciation et au ton. Cite des scénarios et chiffres réels. "
        "Ne promets jamais ce qui figure dans l'anti-positionnement.\n"
    )

# ── Platform-specific prompts optimised for engagement ─────────────────────

LINKEDIN_SYSTEM = """Tu es un expert en personal branding LinkedIn pour {bu}.

Cible : {cible}
Besoins : {besoins}
Frustrations : {frustrations}
Charte : ton={ton} | mots interdits={mots_interdits} | emojis={emojis}
{positionnement}
STRUCTURE OBLIGATOIRE (applique-la à la lettre) :

LIGNE 1 — HOOK : 1 seule phrase courte (max 12 mots). Doit stopper le scroll.
  → Formats qui marchent : chiffre frappant · question rhétorique · affirmation contre-intuitive · "Voici ce que personne ne dit sur…"

[ligne vide]

DÉVELOPPEMENT : 3 à 5 blocs courts séparés par des lignes vides.
  → Chaque bloc = 2-3 lignes max, une seule idée, langage direct et concret.
  → Utilise des listes à puces (•) ou numérotées si pertinent.
  → Inclus un anecdote réelle ou un exemple concret.

[ligne vide]

ENSEIGNEMENT : 1-2 phrases qui résument la leçon clé.

[ligne vide]

CALL TO ACTION : 1 question ouverte très courte pour provoquer des commentaires.

RÈGLES :
- Longueur : 1 400 à 2 000 caractères (compte les espaces)
- Jamais de hashtags
- Emojis : 0 à 2 max, uniquement si dans la charte
- Jamais de formules creuses ("Je suis ravi de partager", "N'hésitez pas")
- Jamais de mot interdit : {mots_interdits}"""

INSTAGRAM_SYSTEM = """Tu es un expert en contenu Instagram pour {bu}.

Cible : {cible}
Charte : ton={ton} | emojis={emojis}
{positionnement}
Tu génères UNE caption Instagram + UN texte visuel (pour l'image).

FORMAT DE RÉPONSE — JSON STRICT (rien d'autre) :
{{
  "visual": "phrase courte et percutante pour l'image (max 8 mots, uppercase OK)",
  "caption": "caption Instagram courte et punchy (100-250 chars, ton direct, 1 emoji max, CTA court)\\n\\n#hashtag1 #hashtag2 #hashtag3 #hashtag4 #hashtag5 #hashtag6 #hashtag7"
}}

RÈGLES caption :
- Max 250 caractères hors hashtags
- 1 seul emoji maximum, bien placé
- CTA en 1 phrase courte ("Dis-moi en commentaire…", "Tu vis ça aussi ?")
- 6-10 hashtags ciblés (pas génériques comme #life)
- Mots interdits à bannir : {mots_interdits}"""

IDEAS_SYSTEM = """Tu es un stratège de contenu B2B expert pour {bu}.

Cible : {cible}
Besoins : {besoins}
Frustrations : {frustrations}
{positionnement}
Génère des angles éditoriaux ORIGINAUX et pertinents, ancrés dans la douleur réelle
de la cible et la différenciation du positionnement. Évite les banalités RSE génériques :
chaque angle doit refléter un scénario concret, un chiffre, ou une objection du terrain.
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
        ton = charte.get("ton", "professionnel et direct")
        mots_interdits = ", ".join(charte.get("mots_interdits", []))
        emojis = " ".join(charte.get("emojis", charte.get("emojis_autorises", [])))
        positionnement = _positioning_block(load_positioning(persona.bu)["content"])

        if platform == "instagram":
            system = INSTAGRAM_SYSTEM.format(
                bu=persona.bu,
                cible=persona.cible,
                ton=ton,
                emojis=emojis or "aucun",
                mots_interdits=mots_interdits or "aucun",
                positionnement=positionnement,
            )
            user = f"Angle éditorial : {angle_editorial}\n\nGénère le visual + la caption Instagram."
        else:
            system = LINKEDIN_SYSTEM.format(
                bu=persona.bu,
                cible=persona.cible,
                besoins=persona.besoins,
                frustrations=persona.frustrations,
                ton=ton,
                mots_interdits=mots_interdits or "aucun",
                emojis=emojis or "aucun",
                positionnement=positionnement,
            )
            user = f"Écris un post LinkedIn sur cet angle éditorial : {angle_editorial}"

        logger.bind(persona_id=persona.id, platform=platform).info("LLM text generation started")

        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.82,
        )

        raw = response.choices[0].message.content or ""
        usage = response.usage

        # Parse Instagram JSON response
        visual_headline = ""
        if platform == "instagram":
            try:
                data = json.loads(raw)
                visual_headline = data.get("visual", "")
                text = data.get("caption", raw)
            except Exception:
                m = re.search(r'\{[\s\S]*\}', raw)
                if m:
                    try:
                        data = json.loads(m.group())
                        visual_headline = data.get("visual", "")
                        text = data.get("caption", raw)
                    except Exception:
                        text = raw
                else:
                    text = raw
        else:
            text = raw
            # Extract hook (first non-empty line) as visual headline for LinkedIn
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            visual_headline = lines[0][:90] if lines else angle_editorial[:90]

        logger.bind(persona_id=persona.id, chars=len(text)).info("LLM text generation done")

        return {
            "text": text.strip(),
            "visual_headline": visual_headline,
            "tokens_in": usage.prompt_tokens if usage else 0,
            "tokens_out": usage.completion_tokens if usage else 0,
            "model": self.model,
        }

    def generate_ideas(self, persona: Persona, keywords: str, platform: str, n: int = 10) -> list[dict]:
        pos = load_positioning(persona.bu)
        system = IDEAS_SYSTEM.format(
            bu=persona.bu,
            cible=persona.cible,
            besoins=persona.besoins,
            frustrations=persona.frustrations,
            positionnement=_positioning_block(pos["content"]),
        )
        plat_str = "LinkedIn ET Instagram" if platform == "both" else platform
        # Si l'utilisateur ne fournit pas de mots-clés, on s'appuie sur ceux du positionnement
        keywords = (keywords or "").strip() or pos["keywords"] or persona.cible
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
