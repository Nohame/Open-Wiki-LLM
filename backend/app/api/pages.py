from fastapi import APIRouter, HTTPException, Depends
from ..services.wiki_service import list_pages, get_page
from ..models.page import WikiPage
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
