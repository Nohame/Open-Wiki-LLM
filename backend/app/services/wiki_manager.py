import logging
import re
from pathlib import Path
import frontmatter as fm
from ..core.config import settings

logger = logging.getLogger(__name__)


def _slug_to_path(slug: str) -> Path:
    # slug format: "category--name" (exactly one "--" separator)
    if "--" in slug:
        folder, name = slug.split("--", 1)
        return Path(settings.wiki_path) / folder / f"{name}.md"
    return Path(settings.wiki_path) / f"{slug}.md"


def page_exists(slug: str) -> bool:
    return _slug_to_path(slug).exists()


def get_existing_sources(slug: str) -> list[str]:
    path = _slug_to_path(slug)
    if not path.exists():
        return []
    try:
        post = fm.load(str(path))
        return post.metadata.get("sources") or []
    except Exception:
        return []


def set_stale(slug: str, stale: bool) -> None:
    path = _slug_to_path(slug)
    if not path.exists():
        logger.warning("set_stale: slug introuvable : %s", slug)
        return
    try:
        post = fm.load(str(path))
    except Exception:
        logger.warning("set_stale: frontmatter malformé pour %s", slug)
        return
    post.metadata["stale"] = stale
    path.write_text(fm.dumps(post), encoding="utf-8")


def set_deprecated(slug: str) -> bool:
    path = _slug_to_path(slug)
    if not path.exists():
        logger.warning("set_deprecated: slug introuvable : %s", slug)
        return False
    try:
        post = fm.load(str(path))
    except Exception:
        logger.warning("set_deprecated: frontmatter malformé pour %s", slug)
        return False
    post.metadata["status"] = "deprecated"
    path.write_text(fm.dumps(post), encoding="utf-8")
    return True


def delete_page(slug: str) -> bool:
    path = _slug_to_path(slug)
    if not path.exists():
        logger.warning("delete_page: slug introuvable : %s", slug)
        return False
    path.unlink()
    return True


def load_index() -> str:
    index_path = Path(settings.wiki_path) / "index.md"
    if not index_path.exists():
        return ""
    return index_path.read_text(encoding="utf-8")


def load_pages(slugs: list[str]) -> dict[str, str]:
    result = {}
    for slug in slugs:
        path = _slug_to_path(slug)
        if path.exists():
            result[slug] = path.read_text(encoding="utf-8")
    return result


def parse_xml_updates(xml: str) -> dict[str, str]:
    pattern = re.compile(r'<page\s+slug="([^"]+)">(.*?)</page>', re.DOTALL)
    matches = pattern.findall(xml)
    if not matches:
        raise ValueError("Aucune balise <page> trouvée dans la réponse XML")
    return {slug: content.strip() for slug, content in matches}


def apply_updates(updates: dict[str, str]) -> list[str]:
    written = []
    for slug, content in updates.items():
        path = _slug_to_path(slug)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(slug)
    return written


def rebuild_index_file() -> None:
    wiki_root = Path(settings.wiki_path)
    categories: dict[str, list[tuple[str, str, str]]] = {}

    for md_file in sorted(wiki_root.rglob("*.md")):
        if md_file.name in ("index.md", "log.md", "schema.md"):
            continue
        rel = md_file.relative_to(wiki_root)
        parts = rel.parts
        category = parts[0] if len(parts) > 1 else "root"
        name = md_file.stem
        slug = f"{parts[0]}--{name}" if len(parts) > 1 else name

        text = md_file.read_text(encoding="utf-8")
        title = _extract_frontmatter_title(text) or name
        summary = _extract_resume_first_line(text) or ""
        categories.setdefault(category, []).append((slug, title, summary))

    lines = [
        "# Index du wiki",
        "",
        "<!-- Mis à jour automatiquement — ne pas modifier manuellement -->",
    ]
    for category, pages in sorted(categories.items()):
        lines.append(f"\n## {category}\n")
        lines.append("| Page | Résumé |")
        lines.append("|------|--------|")
        for slug, title, summary in pages:
            path_ref = slug.replace("--", "/")
            lines.append(f"| [{slug}]({path_ref}.md) | {summary} |")

    (wiki_root / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_log() -> str:
    log_path = Path(settings.wiki_path) / "log.md"
    if not log_path.exists():
        return ""
    return log_path.read_text(encoding="utf-8")


def append_log(entry: str) -> None:
    log_path = Path(settings.wiki_path) / "log.md"
    header = "# Journal des ingestions\n\n"
    if log_path.exists():
        existing = log_path.read_text(encoding="utf-8")
        if existing.startswith("# Journal des ingestions"):
            _, _, existing = existing.partition("\n")
            existing = existing.lstrip("\n")
        log_path.write_text(header + entry + "\n" + existing, encoding="utf-8")
    else:
        log_path.write_text(header + entry + "\n", encoding="utf-8")


def _extract_frontmatter_title(text: str) -> str | None:
    match = re.search(r"^title:\s*(.+)$", text, re.MULTILINE)
    if match:
        return match.group(1).strip().strip('"').strip("'")
    return None


def _extract_resume_first_line(text: str) -> str | None:
    match = re.search(r"##\s+Résumé\s*\n+(.*?)(?:\n\n|\n##|\Z)", text, re.DOTALL)
    if match:
        content = match.group(1).strip()
        if not content:
            return ""
        return content.splitlines()[0][:100]
    return None
