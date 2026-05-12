from pathlib import Path
from .wiki_service import list_pages
from ..storage.search import SearchIndex
from ..models.search import SearchResult
from ..core.config import settings


def _get_index() -> SearchIndex:
    return SearchIndex(Path(settings.data_path) / "openwikillm.db")


def rebuild_index() -> int:
    pages = list_pages()
    index = _get_index()
    index.rebuild([
        {
            "slug": p.slug,
            "title": p.title,
            "content": p.content,
            "tags": p.tags,
        }
        for p in pages
    ])
    return len(pages)


def search(query: str, limit: int = 10) -> list[SearchResult]:
    import sqlite3
    import re
    # Sanitize query for FTS5: remove special characters that cause syntax errors
    tokens = re.sub(r'[^\w\s]', ' ', query, flags=re.UNICODE).split()
    if not tokens:
        return []
    # Use OR semantics so partial term matches still return results
    safe_query = " OR ".join(tokens)
    index = _get_index()
    try:
        results = index.search(safe_query, limit=limit)
    except sqlite3.OperationalError:
        return []
    return [
        SearchResult(
            slug=r["slug"],
            title=r["title"],
            snippet=r["snippet"],
            score=r["score"],
        )
        for r in results
    ]
