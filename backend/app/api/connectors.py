from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from ..core.auth import verify_api_key
from ..core.config import settings
from ..core import config_store
from ..models.ingest import IngestResult
from ..services.connectors.google_drive import (
    build_auth_url,
    exchange_code,
    refresh_token_if_needed,
    list_files,
    download_file,
)
from ..services.file_extractor import extract_text
from ..services.ingest_service import ingest_text

MAX_FILE_SIZE = 10 * 1024 * 1024

router = APIRouter(prefix="/api/connectors/google-drive")


def _redirect_uri() -> str:
    return f"{settings.backend_url}/api/connectors/google-drive/callback"


@router.get("/auth-url", dependencies=[Depends(verify_api_key)])
async def get_auth_url() -> dict:
    cfg = config_store.load().connectors.google_drive
    if not cfg.client_id or not cfg.client_secret:
        raise HTTPException(
            status_code=400,
            detail="Configurez d'abord vos credentials Google Drive dans les Paramètres",
        )
    url = build_auth_url(cfg.client_id, _redirect_uri())
    return {"url": url}


@router.get("/callback")
async def oauth_callback(code: str | None = None, error: str | None = None) -> RedirectResponse:
    if error or not code:
        return RedirectResponse(
            f"{settings.app_url}/settings?error=google-drive-denied", status_code=302
        )
    full = config_store.load()
    cfg = full.connectors.google_drive
    try:
        new_cfg = await exchange_code(code, cfg.client_id, cfg.client_secret, _redirect_uri())
    except Exception:
        return RedirectResponse(
            f"{settings.app_url}/settings?error=google-drive-denied", status_code=302
        )
    full.connectors.google_drive = cfg.model_copy(update={
        "access_token": new_cfg.access_token,
        "refresh_token": new_cfg.refresh_token,
        "token_expiry": new_cfg.token_expiry,
    })
    config_store.save(full)
    return RedirectResponse(
        f"{settings.app_url}/settings?connected=google-drive", status_code=302
    )


@router.delete("", status_code=204, dependencies=[Depends(verify_api_key)])
async def disconnect() -> None:
    full = config_store.load()
    gd = full.connectors.google_drive
    full.connectors.google_drive = gd.model_copy(update={
        "access_token": "",
        "refresh_token": "",
        "token_expiry": "",
    })
    config_store.save(full)


@router.get("/files", dependencies=[Depends(verify_api_key)])
async def get_files(folder_id: str = "root") -> dict:
    cfg = config_store.load().connectors.google_drive
    if not cfg.access_token:
        raise HTTPException(
            status_code=401,
            detail="Session Google Drive expirée, reconnectez-vous",
        )
    try:
        refreshed = await refresh_token_if_needed(cfg)
        if refreshed.access_token != cfg.access_token:
            full = config_store.load()
            full.connectors.google_drive = full.connectors.google_drive.model_copy(update={
                "access_token": refreshed.access_token,
                "token_expiry": refreshed.token_expiry,
            })
            config_store.save(full)
        cfg = refreshed
        files = await list_files(cfg, folder_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Google Drive : {e}")
    return {"files": files, "folder_id": folder_id}


class GoogleDriveIngestRequest(BaseModel):
    file_id: str
    file_name: str
    mime_type: str
    title: str | None = None
    tags: list[str] = []


@router.post("/ingest", response_model=IngestResult, dependencies=[Depends(verify_api_key)])
async def ingest_drive_file(body: GoogleDriveIngestRequest) -> IngestResult:
    cfg = config_store.load().connectors.google_drive
    if not cfg.access_token:
        raise HTTPException(
            status_code=401,
            detail="Session Google Drive expirée, reconnectez-vous",
        )
    try:
        refreshed = await refresh_token_if_needed(cfg)
        if refreshed.access_token != cfg.access_token:
            full = config_store.load()
            full.connectors.google_drive = full.connectors.google_drive.model_copy(update={
                "access_token": refreshed.access_token,
                "token_expiry": refreshed.token_expiry,
            })
            config_store.save(full)
        cfg = refreshed
        file_bytes, filename = await download_file(
            cfg, body.file_id, body.file_name, body.mime_type
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Google Drive : {e}")

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (max 10 Mo)")

    try:
        text = await extract_text(file_bytes, filename)
    except ValueError as e:
        raise HTTPException(status_code=415, detail=str(e))

    if not text.strip():
        raise HTTPException(status_code=422, detail="Aucun texte extractible")

    effective_title = body.title or body.file_name
    result = await ingest_text(text, effective_title, body.tags)
    return IngestResult(**result)
