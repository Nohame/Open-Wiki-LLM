from fastapi import APIRouter, Depends
from ..services import reference_service
from ..models.references import PageReferences
from ..core.auth import verify_api_key

router = APIRouter(prefix="/api", dependencies=[Depends(verify_api_key)])


@router.get("/pages/{slug}/references", response_model=PageReferences)
def get_page_references(slug: str) -> PageReferences:
    refs = reference_service.get_references(slug)
    return PageReferences(slug=slug, **refs)
