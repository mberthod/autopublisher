import argparse
import asyncio
import json
from pathlib import Path

from app.schemas import CarouselSpec
from app.services.carousel_service import generate_carousel


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate carousel PNGs from a spec JSON")
    parser.add_argument("--spec", required=True, help="Path to CarouselSpec JSON file")
    args = parser.parse_args()

    spec_data = json.loads(Path(args.spec).read_text())
    spec = CarouselSpec.model_validate(spec_data)

    paths = asyncio.run(generate_carousel(spec))
    for p in paths:
        print(p)


if __name__ == "__main__":
    main()
