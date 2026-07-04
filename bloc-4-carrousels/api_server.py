import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from app.schemas import CarouselSpec, CarouselSlide
from app.services.carousel_service import generate_carousel


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs("./data/carousels", exist_ok=True)
    yield


app = FastAPI(title="Carrousels — SaaS RSE", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://192.168.0.176:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QuickImageRequest(BaseModel):
    bu: str = "noisyless"
    theme: Optional[str] = None          # auto si None : instagram → "instagram", linkedin → "bold"
    platform: str = "linkedin"
    title: Optional[str] = None
    body: str = ""
    background_color: str = "#1A1A2E"
    text_color: str = "#E2E2F0"


@app.post("/api/v1/image/generate", tags=["image"])
async def generate_image(req: QuickImageRequest):
    req_id = str(uuid.uuid4())[:12]
    output_dir = f"./data/carousels/{req_id}"
    theme = req.theme or ("instagram" if req.platform == "instagram" else "bold")
    spec = CarouselSpec(
        bu=req.bu,  # type: ignore[arg-type]
        theme=theme,  # type: ignore[arg-type]
        slides=[
            CarouselSlide(
                index=0,
                title=req.title,
                body=req.body[:350] if req.platform == "instagram" else req.body[:200],
                background="solid",
                background_color=req.background_color,
                text_color=req.text_color,
            )
        ],
        output_dir=output_dir,
    )
    paths = await generate_carousel(spec)
    filename = os.path.basename(paths[0]) if paths else ""
    url = f"http://192.168.0.176:8004/static/carousels/{req_id}/{filename}"
    return {"image_url": url, "req_id": req_id}


@app.post("/api/v1/carousel/generate", tags=["carousel"])
async def generate_carousel_endpoint(spec: CarouselSpec):
    req_id = str(uuid.uuid4())[:12]
    spec.output_dir = f"./data/carousels/{req_id}"
    paths = await generate_carousel(spec)
    urls = [
        f"http://192.168.0.176:8004/static/carousels/{req_id}/{os.path.basename(p)}"
        for p in paths
    ]
    return {"image_urls": urls}


app.mount("/static/carousels", StaticFiles(directory="./data/carousels"), name="carousels")
