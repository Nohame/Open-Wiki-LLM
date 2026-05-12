from pathlib import Path
import frontmatter
from ..models.page import WikiPage


def _path_to_slug(wiki_path: Path, file_path: Path) -> str:
    return str(file_path.relative_to(wiki_path).with_suffix("")).replace("/", "--")


def load_page(file_path: Path, wiki_path: Path) -> WikiPage:
    post = frontmatter.load(str(file_path))
    return WikiPage(
        slug=_path_to_slug(wiki_path, file_path),
        title=post.metadata.get("title", file_path.stem),
        type=post.metadata.get("type", "note"),
        status=post.metadata.get("status", "draft"),
        confidence=post.metadata.get("confidence", "medium"),
        sources=post.metadata.get("sources", []),
        updated_at=str(post.metadata.get("updated_at", "")),
        tags=post.metadata.get("tags", []),
        content=post.content,
    )


def list_pages(wiki_path: Path) -> list[WikiPage]:
    pages = []
    for file_path in sorted(wiki_path.rglob("*.md")):
        if file_path.name == "index.md":
            continue
        pages.append(load_page(file_path, wiki_path))
    return pages


def get_page(slug: str, wiki_path: Path) -> WikiPage | None:
    for file_path in wiki_path.rglob("*.md"):
        if _path_to_slug(wiki_path, file_path) == slug:
            return load_page(file_path, wiki_path)
    return None
