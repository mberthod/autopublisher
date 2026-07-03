import pytest
from app.schemas import CarouselSlide
from app.services.template_engine import render_slide_html


SLIDE = CarouselSlide(
    index=0,
    title="Test Title",
    body="Test body content.",
    background_color="#FFFFFF",
    text_color="#000000",
)

CONTEXT = {"slide": SLIDE, "total": 3, "bu": "noisyless", "width": 1080, "height": 1080}


def test_modern_renders():
    html = render_slide_html("modern", CONTEXT)
    assert "Test Title" in html
    assert "Test body content." in html
    assert "01 / 03" in html


def test_minimal_renders():
    html = render_slide_html("minimal", CONTEXT)
    assert "Test body content." in html
    assert "noisyless" in html


def test_bold_renders():
    html = render_slide_html("bold", CONTEXT)
    assert "Test Title" in html


def test_organic_renders():
    html = render_slide_html("organic", CONTEXT)
    assert "Test Title" in html
    assert "blob" in html


def test_all_themes_produce_different_html():
    outputs = [render_slide_html(t, CONTEXT) for t in ["modern", "minimal", "bold", "organic"]]
    assert len(set(outputs)) == 4


def test_slide_without_title():
    slide = CarouselSlide(index=0, body="Body only", background_color="#FFF", text_color="#000")
    ctx = {**CONTEXT, "slide": slide}
    html = render_slide_html("modern", ctx)
    assert "Body only" in html
    assert "<div class=\"title\">" not in html
