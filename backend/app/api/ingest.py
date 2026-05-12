from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from ..services.ingest_service import ingest_text, ingest_image
from ..models.ingest import IngestTextRequest, IngestResult
from ..core.auth import verify_api_key

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}

router = APIRouter(prefix="/api", dependencies=[Depends(verify_api_key)])


@router.post("/ingest/text", response_model=IngestResult)
async def ingest_text_endpoint(request: IngestTextRequest) -> IngestResult:
    result = await ingest_text(request.text, request.title, request.tags)
    return IngestResult(**result)


@router.post("/ingest/image", response_model=IngestResult)
async def ingest_image_endpoint(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    tags: str = Form(default=""),
) -> IngestResult:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Type non supporté: {file.content_type}. Formats acceptés: png, jpg, webp, gif",
        )
    image_bytes = await file.read()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    result = await ingest_image(image_bytes, file.filename or "image.png", title, tag_list)
    return IngestResult(**result)
