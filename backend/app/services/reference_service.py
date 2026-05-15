import sqlite3
import logging
from pathlib import Path
import frontmatter as fm
from ..core.config import settings

logger = logging.getLogger(__name__)


def _db_path() -> Path:
    return Path(settings.data_path) / "openwikillm.db"


def _path_to_slug(wiki_path: Path, file_path: Path) -> str:
    return str(file_path.relative_to(wiki_path).with_suffix("")).replace("/", "--")


def rebuild_references() -> None:
    wiki_root = Path(settings.wiki_path)
    rows: list[tuple[str, str]] = []
    for md_file in wiki_root.rglob("*.md"):
        if md_file.name in ("index.md", "log.md", "schema.md"):
            continue
        slug = _path_to_slug(wiki_root, md_file)
        try:
            post = fm.load(str(md_file))
            sources = post.metadata.get("sources") or []
        except Exception:
            logger.warning("Frontmatter malformé — ignoré : %s", md_file)
            continue
        for source_slug in sources:
            rows.append((slug, source_slug))
    with sqlite3.connect(str(_db_path())) as conn:
        conn.execute("DELETE FROM page_references")
        conn.executemany("INSERT OR IGNORE INTO page_references VALUES (?, ?)", rows)


def get_references(slug: str) -> dict[str, list[str]]:
    with sqlite3.connect(str(_db_path())) as conn:
        references = [
            row[0]
            for row in conn.execute(
                "SELECT source_slug FROM page_references WHERE page_slug = ?", (slug,)
            ).fetchall()
        ]
        referenced_by = [
            row[0]
            for row in conn.execute(
                "SELECT page_slug FROM page_references WHERE source_slug = ?", (slug,)
            ).fetchall()
        ]
    return {"references": references, "referenced_by": referenced_by}


def get_stale_pages() -> list[str]:
    wiki_root = Path(settings.wiki_path)
    stale: list[str] = []
    for md_file in wiki_root.rglob("*.md"):
        if md_file.name in ("index.md", "log.md", "schema.md"):
            continue
        try:
            post = fm.load(str(md_file))
            if post.metadata.get("stale", False):
                stale.append(_path_to_slug(wiki_root, md_file))
        except Exception:
            logger.warning("Frontmatter malformé — ignoré : %s", md_file)
    return stale
