from fastapi import APIRouter, HTTPException, Depends, Response
from ..services.wiki_service import list_pages, get_page
from ..services import wiki_manager, git_service
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


@router.delete("/pages/{slug}", status_code=204)
def delete_page(slug: str) -> Response:
    deleted = wiki_manager.delete_page(slug)
    if not deleted:
        raise HTTPException(status_code=404, detail="Page not found")
    git_service.commit_edit(slug, "delete")
    return Response(status_code=204)


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
