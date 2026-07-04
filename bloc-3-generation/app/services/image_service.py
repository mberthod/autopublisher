import os
from typing import Optional

import httpx
from loguru import logger
from PIL import Image, ImageDraw, ImageFont

from app.config import settings

IMAGE_PROMPT_TEMPLATE = (
    "Clean editorial photograph, {ton_visuel} style, natural lighting, premium and sober mood, "
    "depicting: {angle_editorial}. "
    "Dominant colors: {couleurs}. Empty clean negative space in the lower third. "
    "Absolutely NO text, no letters, no words, no captions, no signage, no writing, "
    "no watermark, no logo, no numbers anywhere in the image. Photorealistic, high quality."
)

FAL_MODEL = "fal-ai/flux/schnell"
FAL_ENDPOINT = f"https://fal.run/{FAL_MODEL}"

# Instagram = carré, LinkedIn = paysage
_IMAGE_SIZE = {"instagram": "square_hd", "linkedin": "landscape_4_3"}

_ASSETS = os.path.join(os.path.dirname(__file__), "..", "..", "assets")
LOGO_PATH = os.path.join(_ASSETS, "noisyless-logo.png")
_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


class ImageService:
    def __init__(self, fal_key: Optional[str] = None):
        self._fal_key = fal_key or settings.fal_key

    def generate(self, post_id: str, angle_editorial: str, charte: dict,
                 headline: str = "", platform: str = "linkedin") -> Optional[str]:
        if not self._fal_key:
            logger.info("FAL_KEY not set — skipping image generation")
            return None

        ton_visuel = charte.get("ton", "professional").replace("_", " ")
        couleurs = ", ".join(charte.get("couleurs", ["#FFFFFF", "#000000"]))
        prompt = IMAGE_PROMPT_TEMPLATE.format(
            ton_visuel=ton_visuel, angle_editorial=angle_editorial, couleurs=couleurs,
        )
        image_size = _IMAGE_SIZE.get(platform, "landscape_4_3")

        logger.bind(post_id=post_id).info("FAL.ai image generation started")
        try:
            response = httpx.post(
                FAL_ENDPOINT,
                headers={"Authorization": f"Key {self._fal_key}"},
                json={"prompt": prompt, "image_size": image_size, "num_images": 1},
                timeout=60,
            )
            response.raise_for_status()
            remote_url = response.json()["images"][0]["url"]

            local_path = self._download_image(post_id, remote_url)
            # Overlay hook + logo Noisyless par-dessus la photo
            try:
                _add_overlay(local_path, headline)
            except Exception as exc:
                logger.warning(f"overlay hook/logo échoué: {exc}")

            static_url = f"{settings.static_base_url}/static/posts/{os.path.basename(local_path)}"
            logger.bind(post_id=post_id, url=static_url).info("Image générée + overlay")
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


def _font(size: int):
    for p in _FONTS:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _wrap(draw, text: str, font, max_w: int) -> list[str]:
    lines, cur = [], ""
    for w in text.split():
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:4]


def _add_overlay(path: str, headline: str) -> None:
    img = Image.open(path).convert("RGBA")
    W, H = img.size
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    # Dégradé sombre en bas : lisibilité du hook + masque le faux texte éventuel
    band = int(H * 0.48)
    for i in range(band):
        a = min(255, int(255 * (i / band) ** 0.75))
        d.line([(0, H - band + i), (W, H - band + i)], fill=(8, 8, 18, a))

    if headline:
        fs = max(20, int(W * 0.052))
        font = _font(fs)
        margin = int(W * 0.05)
        lines = _wrap(d, headline.strip().upper(), font, W - 2 * margin)
        lh = int(fs * 1.18)
        y = H - margin - lh * len(lines)
        # petite barre accent Noisyless
        d.rectangle([margin, y - int(fs * 0.5), margin + int(W * 0.14), y - int(fs * 0.5) + max(4, int(fs * 0.08))],
                    fill=(212, 160, 92, 255))
        for ln in lines:
            d.text((margin, y), ln, font=font, fill=(255, 255, 255, 255))
            y += lh

    img = Image.alpha_composite(img, overlay)

    # Logo Noisyless en haut à droite
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        lw = int(W * 0.13)
        logo = logo.resize((lw, int(logo.height * lw / logo.width)))
        img.alpha_composite(logo, (W - lw - int(W * 0.04), int(W * 0.04)))
    except Exception as exc:
        logger.warning(f"logo introuvable: {exc}")

    img.convert("RGB").save(path, "PNG")
