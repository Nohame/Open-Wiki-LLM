import re
from pathlib import Path
from datetime import date
from .ollama_service import compile_to_markdown, compile_image_to_markdown
from ..core.config import settings


def _slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


async def ingest_text(text: str, title: str | None, tags: list[str]) -> dict:
    today = date.today().isoformat()
    effective_title = title or "Source sans titre"
    slug = _slugify(effective_title)

    raw_path = Path(settings.raw_path) / "imports" / f"{slug}.md"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(text)

    markdown = await compile_to_markdown(text, effective_title, tags, today)

    wiki_path = Path(settings.wiki_path) / "imports" / f"{slug}.md"
    wiki_path.parent.mkdir(parents=True, exist_ok=True)
    wiki_path.write_text(markdown)

    return {
        "slug": f"imports--{slug}",
        "raw_path": str(raw_path),
        "wiki_path": str(wiki_path),
        "title": effective_title,
    }


async def ingest_image(image_bytes: bytes, filename: str, title: str | None, tags: list[str]) -> dict:
    today = date.today().isoformat()
    effective_title = title or Path(filename).stem.replace("-", " ").replace("_", " ").capitalize()
    slug = _slugify(effective_title)
    suffix = Path(filename).suffix.lower()

    raw_path = Path(settings.raw_path) / "imports" / f"{slug}{suffix}"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(image_bytes)

    markdown = await compile_image_to_markdown(image_bytes, effective_title, tags, today)

    wiki_path = Path(settings.wiki_path) / "imports" / f"{slug}.md"
    wiki_path.parent.mkdir(parents=True, exist_ok=True)
    wiki_path.write_text(markdown)

    return {
        "slug": f"imports--{slug}",
        "raw_path": str(raw_path),
        "wiki_path": str(wiki_path),
        "title": effective_title,
    }
