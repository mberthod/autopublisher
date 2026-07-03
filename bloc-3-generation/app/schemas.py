from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class PostGenerateRequest(BaseModel):
    planning_id: str
    persona_id: str
    angle_editorial: str = Field(..., min_length=10)
    format: Literal["text_only", "image", "carousel"]
    platform: Literal["linkedin", "instagram"]


class PostGenerateResponse(BaseModel):
    post_id: str
    status: str
    text: str
    image_url: Optional[str] = None
    carousel_urls: Optional[list[str]] = None
    generation_metadata: dict


class PostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    planning_id: str
    persona_id: str
    platform: str
    angle_editorial: str
    format: str
    text: Optional[str]
    image_url: Optional[str]
    carousel_urls: Optional[list[str]]
    status: str
    generation_metadata: Optional[dict]
    created_at: datetime
    updated_at: datetime
