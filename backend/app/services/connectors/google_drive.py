from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

import httpx

from ...models.settings import GoogleDriveConfig

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_DRIVE_API = "https://www.googleapis.com/drive/v3"
SCOPES = "https://www.googleapis.com/auth/drive.readonly"
GOOGLE_DOCS_MIME = "application/vnd.google-apps.document"
EXPORT_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
SUPPORTED_MIMES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    EXPORT_MIME,
    GOOGLE_DOCS_MIME,
}
FOLDER_MIME = "application/vnd.google-apps.folder"


def build_auth_url(client_id: str, redirect_uri: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code(
    code: str, client_id: str, client_secret: str, redirect_uri: str
) -> GoogleDriveConfig:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        data = resp.json()
    expiry = (
        datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600))
    ).isoformat()
    return GoogleDriveConfig(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token", ""),
        token_expiry=expiry,
    )


async def refresh_token_if_needed(cfg: GoogleDriveConfig) -> GoogleDriveConfig:
    if not cfg.token_expiry:
        return cfg
    try:
        expiry = datetime.fromisoformat(cfg.token_expiry)
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
    except ValueError:
        return cfg
    if expiry > datetime.now(timezone.utc) + timedelta(seconds=60):
        return cfg
    if not cfg.refresh_token:
        return cfg
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": cfg.client_id,
                "client_secret": cfg.client_secret,
                "refresh_token": cfg.refresh_token,
                "grant_type": "refresh_token",
            },
        )
        resp.raise_for_status()
        data = resp.json()
    expiry_new = (
        datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600))
    ).isoformat()
    return cfg.model_copy(update={
        "access_token": data["access_token"],
        "token_expiry": expiry_new,
    })


async def list_files(cfg: GoogleDriveConfig, folder_id: str = "root") -> list[dict]:
    mime_filter = " or ".join(
        f"mimeType='{m}'" for m in [*SUPPORTED_MIMES, FOLDER_MIME]
    )
    params = {
        "q": f"'{folder_id}' in parents and trashed=false and ({mime_filter})",
        "fields": "files(id,name,mimeType,size,modifiedTime)",
        "pageSize": 100,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{GOOGLE_DRIVE_API}/files",
            params=params,
            headers={"Authorization": f"Bearer {cfg.access_token}"},
        )
        resp.raise_for_status()
        data = resp.json()
    result = []
    for f in data.get("files", []):
        mime = f["mimeType"]
        if mime != FOLDER_MIME and mime not in SUPPORTED_MIMES:
            continue
        result.append({
            "id": f["id"],
            "name": f["name"],
            "mimeType": mime,
            "size": int(f["size"]) if f.get("size") else None,
            "modifiedTime": f.get("modifiedTime", ""),
            "isFolder": mime == FOLDER_MIME,
        })
    return result


async def download_file(
    cfg: GoogleDriveConfig, file_id: str, file_name: str, mime_type: str
) -> tuple[bytes, str]:
    async with httpx.AsyncClient(timeout=30) as client:
        if mime_type == GOOGLE_DOCS_MIME:
            resp = await client.get(
                f"{GOOGLE_DRIVE_API}/files/{file_id}/export",
                params={"mimeType": EXPORT_MIME},
                headers={"Authorization": f"Bearer {cfg.access_token}"},
            )
            resp.raise_for_status()
            return resp.content, f"{file_name}.docx"
        resp = await client.get(
            f"{GOOGLE_DRIVE_API}/files/{file_id}",
            params={"alt": "media"},
            headers={"Authorization": f"Bearer {cfg.access_token}"},
        )
        resp.raise_for_status()
        return resp.content, file_name
