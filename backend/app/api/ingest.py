from fastapi import APIRouter, Depends
from ..services.ingest_service import ingest_text
from ..models.ingest import IngestTextRequest, IngestResult
from ..core.auth import verify_api_key

router = APIRouter(prefix="/api", dependencies=[Depends(verify_api_key)])


@router.post("/ingest/text", response_model=IngestResult)
async def ingest_text_endpoint(request: IngestTextRequest) -> IngestResult:
    result = await ingest_text(request.text, request.title, request.tags)
    return IngestResult(**result)
