from fastapi import APIRouter, HTTPException, Depends
from ..services.wiki_service import list_pages, get_page
from ..services import wiki_manager
from ..models.page import WikiPage, StaleUpdate
from ..core.auth import verify_api_key

router = APIRouter(prefix="/api", dependencies=[Depends(verify_api_key)])


@router.get("/pages", response_model=list[WikiPage])
def get_pages() -> list[WikiPage]:
    return list_pages()


@router.get("/pages/{slug}", response_model=WikiPage)
def get_page_by_slug(slug: str) -> WikiPage:
    page = get_page(slug)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


@router.patch("/pages/{slug}/stale", response_model=WikiPage)
def update_stale(slug: str, body: StaleUpdate) -> WikiPage:
    page = get_page(slug)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    wiki_manager.set_stale(slug, body.stale)
    updated = get_page(slug)
    if updated is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return updated
