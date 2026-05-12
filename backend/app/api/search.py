from fastapi import APIRouter, Depends
from ..services.search_service import search, rebuild_index
from ..models.search import SearchQuery, SearchResult
from ..core.auth import verify_api_key

router = APIRouter(prefix="/api", dependencies=[Depends(verify_api_key)])


@router.post("/search", response_model=list[SearchResult])
def search_pages(query: SearchQuery) -> list[SearchResult]:
    return search(query.q, query.limit)


@router.post("/index/rebuild")
def rebuild() -> dict:
    count = rebuild_index()
    return {"indexed": count}
