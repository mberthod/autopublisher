from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def render_slide_html(template_name: str, context: dict) -> str:
    tpl = _env.get_template(f"{template_name}.html")
    return tpl.render(**context)
