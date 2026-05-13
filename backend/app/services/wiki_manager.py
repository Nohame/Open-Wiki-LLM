import re
from pathlib import Path
from ..core.config import settings


def _slug_to_path(slug: str) -> Path:
    if "--" in slug:
        folder, name = slug.split("--", 1)
        return Path(settings.wiki_path) / folder / f"{name}.md"
    return Path(settings.wiki_path) / f"{slug}.md"


def load_index() -> str:
    index_path = Path(settings.wiki_path) / "index.md"
    if not index_path.exists():
        return ""
    return index_path.read_text()


def load_pages(slugs: list[str]) -> dict[str, str]:
    result = {}
    for slug in slugs:
        path = _slug_to_path(slug)
        if path.exists():
            result[slug] = path.read_text()
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
        path.write_text(content)
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

        text = md_file.read_text()
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

    (wiki_root / "index.md").write_text("\n".join(lines) + "\n")


def append_log(entry: str) -> None:
    log_path = Path(settings.wiki_path) / "log.md"
    header = "# Journal des ingestions\n\n"
    if log_path.exists():
        existing = log_path.read_text()
        if existing.startswith("# Journal des ingestions"):
            existing = existing[len("# Journal des ingestions"):].lstrip("\n")
        log_path.write_text(header + entry + "\n" + existing)
    else:
        log_path.write_text(header + entry + "\n")


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
