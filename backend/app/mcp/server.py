import re
from datetime import date
import frontmatter as fm
from fastmcp import FastMCP
from ..services.wiki_service import list_pages, get_page
from ..services.search_service import search, rebuild_index
from ..services import reference_service, wiki_manager

mcp = FastMCP("openwikillm")

_SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9-]*(?:--[a-z0-9][a-z0-9-]*)?$')


@mcp.tool()
def wiki_list_pages() -> list[dict]:
    """Liste toutes les pages du wiki."""
    return [p.model_dump(exclude={"content"}) for p in list_pages()]


@mcp.tool()
def wiki_read_page(slug: str) -> dict | None:
    """Lit le contenu complet d'une page wiki par son slug."""
    page = get_page(slug)
    if page is None:
        return None
    return page.model_dump()


@mcp.tool()
def wiki_search(query: str, limit: int = 10) -> list[dict]:
    """Recherche dans le wiki via FTS5."""
    results = search(query, limit=limit)
    return [r.model_dump() for r in results]


@mcp.tool()
def wiki_rebuild_index() -> dict:
    """Reconstruit l'index de recherche FTS5."""
    count = rebuild_index()
    return {"indexed": count}


@mcp.tool()
def wiki_list_stale() -> list[dict]:
    """Liste toutes les pages wiki marquées comme obsolètes (stale: true)."""
    slugs = reference_service.get_stale_pages()
    return [{"slug": s} for s in slugs]


@mcp.tool()
def wiki_list_references(slug: str) -> dict:
    """
    Retourne les références d'une page wiki :
    - references : sources[] dont dépend cette page
    - referenced_by : pages qui dépendent de ce slug
    """
    return reference_service.get_references(slug)


@mcp.tool()
def wiki_guide() -> str:
    """Retourne l'index structuré du wiki : catégories, slugs disponibles et résumés."""
    return wiki_manager.load_index()


_VALID_TYPES = {"concept", "project", "procedure", "decision", "note", "entity"}
_VALID_STATUSES = {"draft", "reviewed", "validated", "deprecated"}
_VALID_CONFIDENCES = {"low", "medium", "high"}


@mcp.tool()
def wiki_write(
    slug: str,
    title: str,
    content: str,
    page_type: str = "concept",
    status: str = "draft",
    tags: list[str] | None = None,
    confidence: str = "medium",
) -> dict:
    """Crée ou met à jour une page wiki. Le backend assemble le frontmatter YAML automatiquement."""
    if not _SLUG_RE.match(slug):
        return {"slug": slug, "written": False, "error": "format de slug invalide"}
    if page_type not in _VALID_TYPES:
        return {"slug": slug, "written": False, "error": f"type invalide: {page_type}"}
    if status not in _VALID_STATUSES:
        return {"slug": slug, "written": False, "error": f"status invalide: {status}"}
    if confidence not in _VALID_CONFIDENCES:
        return {"slug": slug, "written": False, "error": f"confidence invalide: {confidence}"}

    # Preserve existing sources on update
    existing_sources = wiki_manager.get_existing_sources(slug)

    post = fm.Post(
        content,
        title=title,
        type=page_type,
        status=status,
        confidence=confidence,
        tags=tags or [],
        sources=existing_sources,
        updated_at=date.today().isoformat(),
    )
    try:
        wiki_manager.apply_updates({slug: fm.dumps(post)})
        rebuild_index()
        reference_service.rebuild_references()
    except Exception as e:
        return {"slug": slug, "written": False, "error": str(e)}
    return {"slug": slug, "written": True}


@mcp.tool()
def wiki_delete(slug: str) -> dict:
    """Marque une page wiki comme dépréciée (status: deprecated). La page reste sur le disque."""
    if not _SLUG_RE.match(slug):
        return {"slug": slug, "deprecated": False, "error": "format de slug invalide"}
    deprecated = wiki_manager.set_deprecated(slug)
    if deprecated:
        rebuild_index()
        reference_service.rebuild_references()
    return {"slug": slug, "deprecated": deprecated}
