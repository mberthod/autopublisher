import asyncio
import pytest
from pathlib import Path
from app.schemas import CarouselSpec, CarouselSlide
from app.services.carousel_service import generate_carousel


def make_spec(theme: str, output_dir: str) -> CarouselSpec:
    return CarouselSpec(
        bu="noisyless",
        theme=theme,
        output_dir=output_dir,
        slides=[
            CarouselSlide(index=0, title="Slide A", body="First slide content.", background_color="#0D0D0D", text_color="#F5F5F5"),
            CarouselSlide(index=1, title="Slide B", body="Second slide content.", background_color="#0D0D0D", text_color="#F5F5F5"),
            CarouselSlide(index=2, title="Slide C", body="Third slide content.", background_color="#0D0D0D", text_color="#F5F5F5"),
        ],
    )


@pytest.mark.asyncio
async def test_modern_generates_three_pngs(tmp_path):
    spec = make_spec("modern", str(tmp_path))
    paths = await generate_carousel(spec)
    assert len(paths) == 3
    for p in paths:
        assert p.exists()
        assert p.stat().st_size > 5_000


@pytest.mark.asyncio
async def test_themes_produce_different_bytes(tmp_path):
    results = {}
    for theme in ["modern", "minimal", "bold", "organic"]:
        out = tmp_path / theme
        spec = make_spec(theme, str(out))
        paths = await generate_carousel(spec)
        results[theme] = paths[0].read_bytes()

    unique = set(results.values())
    assert len(unique) == 4, "All 4 themes should produce visually different PNGs"


@pytest.mark.asyncio
async def test_single_slide(tmp_path):
    spec = CarouselSpec(
        bu="afluxo",
        theme="minimal",
        output_dir=str(tmp_path),
        slides=[CarouselSlide(index=0, body="Solo slide.", background_color="#FAFAFA", text_color="#111111")],
    )
    paths = await generate_carousel(spec)
    assert len(paths) == 1
    assert paths[0].stat().st_size > 5_000
