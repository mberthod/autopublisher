import os
from typing import Optional

import httpx
from loguru import logger

from app.config import settings

IMAGE_PROMPT_TEMPLATE = (
    "Photographie professionnelle RSE, style {ton_visuel}, éclairage naturel, "
    "illustrant : {angle_editorial}. "
    "Couleurs dominantes : {couleurs}. "
    "Pas de texte dans l'image. Pas de logo. Format paysage."
)

FAL_MODEL = "fal-ai/flux/schnell"
FAL_ENDPOINT = f"https://fal.run/{FAL_MODEL}"


class ImageService:
    def __init__(self, fal_key: Optional[str] = None):
        self._fal_key = fal_key or settings.fal_key

    def generate(self, post_id: str, angle_editorial: str, charte: dict) -> Optional[str]:
        if not self._fal_key:
            logger.info("FAL_KEY not set — skipping image generation")
            return None

        ton_visuel = charte.get("ton", "professional").replace("_", " ")
        couleurs = ", ".join(charte.get("couleurs", ["#FFFFFF", "#000000"]))
        prompt = IMAGE_PROMPT_TEMPLATE.format(
            ton_visuel=ton_visuel,
            angle_editorial=angle_editorial,
            couleurs=couleurs,
        )

        logger.bind(post_id=post_id).info("FAL.ai image generation started")

        try:
            response = httpx.post(
                FAL_ENDPOINT,
                headers={"Authorization": f"Key {self._fal_key}"},
                json={"prompt": prompt, "image_size": "landscape_4_3", "num_images": 1},
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            remote_url = data["images"][0]["url"]

            local_path = self._download_image(post_id, remote_url)
            static_url = f"{settings.static_base_url}/static/posts/{os.path.basename(local_path)}"
            logger.bind(post_id=post_id, url=static_url).info("Image downloaded and served locally")
            return static_url

        except Exception as exc:
            logger.bind(post_id=post_id).error(f"Image generation failed: {exc}")
            return None

    def _download_image(self, post_id: str, url: str) -> str:
        os.makedirs("./data/posts", exist_ok=True)
        path = f"./data/posts/{post_id}.png"
        with httpx.stream("GET", url, timeout=60) as r:
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_bytes():
                    f.write(chunk)
        return path
