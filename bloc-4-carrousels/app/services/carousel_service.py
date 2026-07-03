import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from app.schemas import CarouselSpec
from app.services.template_engine import render_slide_html


async def generate_carousel(spec: CarouselSpec) -> list[Path]:
    output_dir = Path(spec.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    total = len(spec.slides)
    png_paths: list[Path] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        ctx = await browser.new_context(
            viewport={"width": spec.width, "height": spec.height},
            device_scale_factor=1,
        )
        page = await ctx.new_page()

        for slide in spec.slides:
            html = render_slide_html(
                spec.theme,
                {
                    "slide": slide,
                    "total": total,
                    "bu": spec.bu,
                    "width": spec.width,
                    "height": spec.height,
                },
            )
            await page.set_content(html, wait_until="networkidle")
            out = output_dir / f"slide_{slide.index:02d}.png"
            await page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": spec.width, "height": spec.height})
            png_paths.append(out)

        await browser.close()

    return png_paths
