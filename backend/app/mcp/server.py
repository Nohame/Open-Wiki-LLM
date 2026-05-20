from fastmcp import FastMCP
from ..services.wiki_service import list_pages, get_page
from ..services.search_service import search, rebuild_index
from ..services import reference_service

mcp = FastMCP("openwikillm")


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
