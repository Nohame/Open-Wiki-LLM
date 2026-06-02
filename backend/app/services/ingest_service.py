import re
import time
from pathlib import Path
from datetime import date
from .ollama_service import compile_image_to_markdown, identify_related_pages, compile_multi_page
from . import wiki_manager, schema_service, reference_service, git_service
from .search_service import rebuild_index
from ..core.config import settings
from ..core import config_store


def _slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


async def ingest_text(text: str, title: str | None, tags: list[str]) -> dict:
    start = time.monotonic()
    today = date.today().isoformat()
    effective_title = title or "Source sans titre"
    text = text[:config_store.load().ingest.max_text_chars]
    slug = _slugify(effective_title)
    new_slug = f"imports--{slug}"

    raw_path = Path(settings.raw_path) / "imports" / f"{slug}.md"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(text, encoding="utf-8")

    schema = schema_service.load_or_create()
    index_content = wiki_manager.load_index()

    related_slugs = await identify_related_pages(text, effective_title, index_content)
    related_pages = wiki_manager.load_pages(related_slugs)

    xml_output = await compile_multi_page(
        text, effective_title, tags, today, schema, related_pages, new_slug
    )

    updates = wiki_manager.parse_xml_updates(xml_output)
    written_slugs = wiki_manager.apply_updates(updates)

    concepts_created = [s for s in written_slugs if s.startswith("concept--")]
    entities_created = [s for s in written_slugs if s.startswith("entity--")]
    known_prefixes = ("concept--", "entity--", "imports--")
    pages_updated = [
        s for s in written_slugs
        if (s.startswith("imports--") and s != new_slug)
        or not s.startswith(known_prefixes)
    ]

    wiki_manager.rebuild_index_file()
    rebuild_index()

    # Clear stale sur les pages mises à jour par le LLM
    for s in written_slugs:
        wiki_manager.set_stale(s, False)

    # Rebuild graph de références
    reference_service.rebuild_references()

    # Marquer stale les pages dépendantes non mises à jour
    stale_marked: list[str] = []
    for source_slug in written_slugs:
        refs = reference_service.get_references(source_slug)
        for dependent_slug in refs["referenced_by"]:
            if dependent_slug not in written_slugs and dependent_slug not in stale_marked:
                wiki_manager.set_stale(dependent_slug, True)
                stale_marked.append(dependent_slug)

    wiki_path = Path(settings.wiki_path) / "imports" / f"{slug}.md"
    duration_s = round(time.monotonic() - start)
    wiki_manager.append_log(
        f"## [{today}] ingest | {slug}\n"
        f"- Source : {new_slug}\n"
        f"- Concepts : {', '.join(concepts_created) or '—'}\n"
        f"- Entités : {', '.join(entities_created) or '—'}\n"
        f"- Tags : {', '.join(tags) or '—'}\n"
        f"- Durée : {duration_s}s\n"
    )

    git_service.commit_ingest(slug, written_slugs, [])

    return {
        "slug": new_slug,
        "raw_path": str(raw_path),
        "wiki_path": str(wiki_path),
        "title": effective_title,
        "pages_updated": pages_updated,
        "concepts_created": concepts_created,
        "entities_created": entities_created,
        "stale_marked": stale_marked,
    }


# Image ingest does not append to wiki/log.md — only text ingest is logged.
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
    wiki_path.write_text(markdown, encoding="utf-8")

    return {
        "slug": f"imports--{slug}",
        "raw_path": str(raw_path),
        "wiki_path": str(wiki_path),
        "title": effective_title,
        "pages_updated": [],
        "concepts_created": [],
        "entities_created": [],
        "stale_marked": [],
    }
