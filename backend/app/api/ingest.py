from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ..core.auth import verify_api_key
from ..models.ingest import IngestResult, IngestTextRequest
from ..services.file_extractor import ALLOWED_EXTENSIONS, extract_text
from ..services.ingest_service import ingest_image, ingest_text

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}

ALLOWED_MIME_TYPES = {
    "text/plain",
    "text/markdown",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",  # some browsers send this for .md/.docx
    "",  # some environments omit content-type
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

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


@router.post("/ingest/file", response_model=IngestResult)
async def ingest_file_endpoint(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    tags: str = Form(default=""),
) -> IngestResult:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS or file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Type non supporté: {file.content_type or 'inconnu'}. Formats acceptés: .md, .txt, .pdf, .docx",
        )
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (max 10 Mo)")
    try:
        text = await extract_text(file_bytes, file.filename or "")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not text.strip():
        raise HTTPException(status_code=422, detail="Aucun texte extractible")
    effective_title = title or Path(file.filename or "").stem
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    result = await ingest_text(text, effective_title, tag_list)
    return IngestResult(**result)
