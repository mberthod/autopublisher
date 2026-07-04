from typing import Literal, Optional
from pydantic import BaseModel, Field


class CarouselSlide(BaseModel):
    index: int
    title: Optional[str] = None
    body: str
    background: Literal["solid", "gradient", "image"] = "solid"
    background_color: str = "#FFFFFF"
    text_color: str = "#1A1A1A"


class CarouselSpec(BaseModel):
    bu: Literal["noisyless", "afluxo", "mbhrep"]
    theme: Literal["modern", "minimal", "bold", "organic", "instagram"] = "modern"
    slides: list[CarouselSlide] = Field(..., min_length=1, max_length=10)
    width: int = 1080
    height: int = 1080
    output_dir: str = "./data/carousels"
