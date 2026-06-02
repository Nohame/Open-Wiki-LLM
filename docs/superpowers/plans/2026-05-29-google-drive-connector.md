# Google Drive Connector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Google Drive connector so users can configure OAuth credentials in Settings and browse/ingest Drive files from the Ingest page.

**Architecture:** OAuth full-page redirect flow — backend exposes 5 routes under `/api/connectors/google-drive/`. Credentials (`client_id`, `client_secret`) are stored in `config.json` alongside existing LLM config via `config_store`. Tokens are masked in GET responses using the same `"****"` pattern as API keys. Drive files are browsed via Google Drive API v3, downloaded via httpx (no SDK), then fed into the existing `ingest_text` pipeline.

**Tech Stack:** Python 3.11, FastAPI, httpx (no Google SDK), Pydantic v2, Nuxt 3, TypeScript, Tailwind CSS, lucide-vue-next.

---

## File Map

**Created:**
- `backend/app/services/connectors/__init__.py`
- `backend/app/services/connectors/google_drive.py`
- `backend/app/api/connectors.py`
- `backend/tests/test_google_drive_service.py`
- `backend/tests/test_api_connectors.py`
- `frontend/composables/useGoogleDrive.ts`
- `frontend/components/settings/ConnectorsSettings.vue`
- `frontend/components/ingest/GoogleDriveTab.vue`

**Modified:**
- `backend/app/models/settings.py` — add `GoogleDriveConfig`, `ConnectorsConfig`, extend `AppSettings`
- `backend/app/core/config.py` — add `app_url`, `backend_url` fields
- `backend/app/api/settings.py` — extend `_mask` / `_merge_keys` for Drive token fields
- `backend/app/main.py` — register connectors router
- `frontend/types/api.ts` — add `GoogleDriveConfig`, `ConnectorsConfig`, extend `AppSettings`, add `GoogleDriveFile`, `GoogleDriveListResponse`
- `frontend/pages/settings.vue` — add Connectors section, detect OAuth callback query params
- `frontend/pages/ingest.vue` — add Google Drive tab

---

### Task 1: Backend models, config, and masking

**Files:**
- Modify: `backend/app/models/settings.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/api/settings.py`
- Test: `backend/tests/test_api_settings.py` (extend existing)

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_api_settings.py`:

```python
def test_get_settings_includes_connectors(client_settings):
    response = client_settings.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "connectors" in data
    assert "google_drive" in data["connectors"]
    gd = data["connectors"]["google_drive"]
    assert gd["client_id"] == ""
    assert gd["client_secret"] == ""
    assert gd["access_token"] == ""
    assert gd["refresh_token"] == ""
    assert gd["token_expiry"] == ""


def test_get_settings_masks_drive_tokens(client_settings, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_path", str(tmp_path))
    s = AppSettings()
    s.connectors.google_drive.client_secret = "GOCSPX-secret"
    s.connectors.google_drive.access_token = "ya29.access"
    s.connectors.google_drive.refresh_token = "1//refresh"
    config_store.save(s)
    response = client_settings.get("/api/settings")
    gd = response.json()["connectors"]["google_drive"]
    assert gd["client_secret"] == "****"
    assert gd["access_token"] == "****"
    assert gd["refresh_token"] == "****"
    assert gd["client_id"] == ""
    assert gd["token_expiry"] == ""


def test_put_settings_preserves_drive_tokens_when_masked(client_settings, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_path", str(tmp_path))
    s = AppSettings()
    s.connectors.google_drive.client_secret = "GOCSPX-secret"
    s.connectors.google_drive.access_token = "ya29.access"
    s.connectors.google_drive.refresh_token = "1//refresh"
    config_store.save(s)

    payload = {
        "llm": {
            "provider": "ollama",
            "ollama": {"base_url": "http://host.docker.internal:11434", "model": "mistral", "vision_model": "llava"},
            "openai": {"api_key": "", "model": "gpt-4o", "vision_model": "gpt-4o"},
            "gemini": {"api_key": "", "model": "gemini-1.5-pro", "vision_model": "gemini-1.5-pro"},
            "anthropic": {"api_key": "", "model": "claude-opus-4-7", "vision_model": "claude-opus-4-7"},
            "custom": {"base_url": "", "api_key": "", "model": "", "vision_model": ""},
        },
        "ingest": {"max_text_chars": 30000},
        "connectors": {
            "google_drive": {
                "client_id": "client-id",
                "client_secret": "****",
                "access_token": "****",
                "refresh_token": "****",
                "token_expiry": "",
            }
        },
    }
    client_settings.put("/api/settings", json=payload)
    saved = config_store.load()
    assert saved.connectors.google_drive.client_secret == "GOCSPX-secret"
    assert saved.connectors.google_drive.access_token == "ya29.access"
    assert saved.connectors.google_drive.refresh_token == "1//refresh"
    assert saved.connectors.google_drive.client_id == "client-id"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend
python -m pytest tests/test_api_settings.py::test_get_settings_includes_connectors tests/test_api_settings.py::test_get_settings_masks_drive_tokens tests/test_api_settings.py::test_put_settings_preserves_drive_tokens_when_masked -v
```

Expected: FAIL — `AppSettings` has no `connectors` field.

- [ ] **Step 3: Extend `backend/app/models/settings.py`**

```python
from typing import Literal
from pydantic import BaseModel


class OllamaConfig(BaseModel):
    base_url: str = "http://host.docker.internal:11434"
    model: str = "mistral"
    vision_model: str = "llava"


class OpenAIConfig(BaseModel):
    api_key: str = ""
    model: str = "gpt-4o"
    vision_model: str = "gpt-4o"


class GeminiConfig(BaseModel):
    api_key: str = ""
    model: str = "gemini-1.5-pro"
    vision_model: str = "gemini-1.5-pro"


class AnthropicConfig(BaseModel):
    api_key: str = ""
    model: str = "claude-opus-4-7"
    vision_model: str = "claude-opus-4-7"


class CustomConfig(BaseModel):
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    vision_model: str = ""


class LLMConfig(BaseModel):
    provider: Literal["ollama", "openai", "gemini", "anthropic", "custom"] = "ollama"
    ollama: OllamaConfig = OllamaConfig()
    openai: OpenAIConfig = OpenAIConfig()
    gemini: GeminiConfig = GeminiConfig()
    anthropic: AnthropicConfig = AnthropicConfig()
    custom: CustomConfig = CustomConfig()


class IngestConfig(BaseModel):
    max_text_chars: int = 30000


class GoogleDriveConfig(BaseModel):
    client_id: str = ""
    client_secret: str = ""
    access_token: str = ""
    refresh_token: str = ""
    token_expiry: str = ""


class ConnectorsConfig(BaseModel):
    google_drive: GoogleDriveConfig = GoogleDriveConfig()


class AppSettings(BaseModel):
    llm: LLMConfig = LLMConfig()
    ingest: IngestConfig = IngestConfig()
    connectors: ConnectorsConfig = ConnectorsConfig()
```

- [ ] **Step 4: Add `app_url` and `backend_url` to `backend/app/core/config.py`**

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="OPENWIKILLM_",
        extra="ignore",
    )

    app_env: str = "local"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8088

    raw_path: str = "/app/raw"
    wiki_path: str = "/app/wiki"
    data_path: str = "/app/data"

    app_url: str = Field(default="http://localhost:3000", validation_alias="OPENWIKILLM_APP_URL")
    backend_url: str = Field(default="http://localhost:8088", validation_alias="OPENWIKILLM_BACKEND_URL")

    ollama_base_url: str = Field(
        default="http://host.docker.internal:11434",
        validation_alias="OLLAMA_BASE_URL",
    )
    ollama_model: str = Field(
        default="mistral",
        validation_alias="OLLAMA_MODEL",
    )
    ollama_vision_model: str = Field(
        default="llava",
        validation_alias="OLLAMA_VISION_MODEL",
    )

    api_key: str = Field(
        default="",
        validation_alias="API_KEY",
    )


settings = Settings()
```

- [ ] **Step 5: Extend masking in `backend/app/api/settings.py`**

```python
from fastapi import APIRouter, Depends
from ..core.auth import verify_api_key
from ..core import config_store
from ..models.settings import AppSettings

router = APIRouter(prefix="/api", dependencies=[Depends(verify_api_key)])

_MASKED = "****"
_MASKED_PROVIDERS = ("openai", "gemini", "anthropic", "custom")
_MASKED_DRIVE_FIELDS = ("client_secret", "access_token", "refresh_token")


def _mask(s: AppSettings) -> AppSettings:
    data = s.model_dump()
    for p in _MASKED_PROVIDERS:
        if data["llm"][p]["api_key"]:
            data["llm"][p]["api_key"] = _MASKED
    gd = data["connectors"]["google_drive"]
    for field in _MASKED_DRIVE_FIELDS:
        if gd[field]:
            gd[field] = _MASKED
    return AppSettings.model_validate(data)


def _merge_keys(existing: AppSettings, incoming: AppSettings) -> AppSettings:
    data = incoming.model_dump()
    for p in _MASKED_PROVIDERS:
        if data["llm"][p]["api_key"] == _MASKED:
            data["llm"][p]["api_key"] = getattr(existing.llm, p).api_key
    gd_in = data["connectors"]["google_drive"]
    gd_ex = existing.connectors.google_drive
    for field in _MASKED_DRIVE_FIELDS:
        if gd_in[field] == _MASKED:
            gd_in[field] = getattr(gd_ex, field)
    return AppSettings.model_validate(data)


@router.get("/settings", response_model=AppSettings)
def get_settings() -> AppSettings:
    return _mask(config_store.load())


@router.put("/settings", response_model=AppSettings)
def update_settings(body: AppSettings) -> AppSettings:
    existing = config_store.load()
    merged = _merge_keys(existing, body)
    config_store.save(merged)
    return _mask(merged)
```

- [ ] **Step 6: Run the new tests**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend
python -m pytest tests/test_api_settings.py -v
```

Expected: All pass (existing + 3 new).

- [ ] **Step 7: Run full test suite to check no regressions**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend
python -m pytest -v
```

Expected: All pass.

- [ ] **Step 8: Commit**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm
git add backend/app/models/settings.py backend/app/core/config.py backend/app/api/settings.py backend/tests/test_api_settings.py
git commit -m "feat: add GoogleDriveConfig, ConnectorsConfig, app_url/backend_url, Drive field masking"
```

---

### Task 2: Google Drive service

**Files:**
- Create: `backend/app/services/connectors/__init__.py`
- Create: `backend/app/services/connectors/google_drive.py`
- Create: `backend/tests/test_google_drive_service.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_google_drive_service.py`:

```python
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.settings import GoogleDriveConfig
from app.services.connectors import google_drive


def _make_cfg(**kw) -> GoogleDriveConfig:
    defaults = {
        "client_id": "client-id",
        "client_secret": "client-secret",
        "access_token": "ya29.valid",
        "refresh_token": "1//refresh",
        "token_expiry": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    }
    defaults.update(kw)
    return GoogleDriveConfig(**defaults)


def _mock_http_response(json_data: dict, status: int = 200):
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.json.return_value = json_data
    mock_resp.raise_for_status.return_value = None
    mock_resp.content = b"file-bytes"
    return mock_resp


def _mock_client(get_resp=None, post_resp=None):
    mock_client = AsyncMock()
    if get_resp is not None:
        mock_client.get.return_value = get_resp
    if post_resp is not None:
        mock_client.post.return_value = post_resp
    return mock_client


# --- build_auth_url ---

def test_build_auth_url_contains_client_id():
    url = google_drive.build_auth_url("my-client-id", "http://localhost:8088/callback")
    assert "my-client-id" in url
    assert "accounts.google.com" in url
    assert "drive.readonly" in url
    assert "offline" in url


# --- exchange_code ---

def test_exchange_code_returns_config():
    resp = _mock_http_response({
        "access_token": "ya29.new",
        "refresh_token": "1//newrefresh",
        "expires_in": 3600,
    })
    client = _mock_client(post_resp=resp)
    with patch("app.services.connectors.google_drive.httpx.AsyncClient") as MockCls:
        MockCls.return_value.__aenter__ = AsyncMock(return_value=client)
        MockCls.return_value.__aexit__ = AsyncMock(return_value=None)
        cfg = asyncio.run(
            google_drive.exchange_code("auth-code", "cid", "csecret", "http://cb")
        )
    assert cfg.access_token == "ya29.new"
    assert cfg.refresh_token == "1//newrefresh"
    assert cfg.token_expiry != ""


# --- refresh_token_if_needed ---

def test_refresh_not_needed_when_token_fresh():
    cfg = _make_cfg()  # expires in 1 hour
    result = asyncio.run(google_drive.refresh_token_if_needed(cfg))
    assert result.access_token == "ya29.valid"


def test_refresh_called_when_token_expired():
    expired = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    cfg = _make_cfg(token_expiry=expired)
    resp = _mock_http_response({
        "access_token": "ya29.refreshed",
        "expires_in": 3600,
    })
    client = _mock_client(post_resp=resp)
    with patch("app.services.connectors.google_drive.httpx.AsyncClient") as MockCls:
        MockCls.return_value.__aenter__ = AsyncMock(return_value=client)
        MockCls.return_value.__aexit__ = AsyncMock(return_value=None)
        result = asyncio.run(google_drive.refresh_token_if_needed(cfg))
    assert result.access_token == "ya29.refreshed"


# --- list_files ---

def test_list_files_returns_files_and_folders():
    files_resp = _mock_http_response({
        "files": [
            {"id": "f1", "name": "doc.pdf", "mimeType": "application/pdf",
             "size": "1024", "modifiedTime": "2026-01-01T00:00:00Z"},
            {"id": "f2", "name": "folder", "mimeType": "application/vnd.google-apps.folder",
             "modifiedTime": "2026-01-01T00:00:00Z"},
        ]
    })
    client = _mock_client(get_resp=files_resp)
    with patch("app.services.connectors.google_drive.httpx.AsyncClient") as MockCls:
        MockCls.return_value.__aenter__ = AsyncMock(return_value=client)
        MockCls.return_value.__aexit__ = AsyncMock(return_value=None)
        cfg = _make_cfg()
        result = asyncio.run(google_drive.list_files(cfg, "root"))
    assert len(result) == 2
    pdf_file = next(f for f in result if f["name"] == "doc.pdf")
    folder = next(f for f in result if f["name"] == "folder")
    assert pdf_file["isFolder"] is False
    assert pdf_file["size"] == 1024
    assert folder["isFolder"] is True


def test_list_files_filters_unsupported_types():
    files_resp = _mock_http_response({
        "files": [
            {"id": "s1", "name": "sheet", "mimeType": "application/vnd.google-apps.spreadsheet",
             "modifiedTime": "2026-01-01T00:00:00Z"},
            {"id": "d1", "name": "doc.pdf", "mimeType": "application/pdf",
             "size": "100", "modifiedTime": "2026-01-01T00:00:00Z"},
        ]
    })
    client = _mock_client(get_resp=files_resp)
    with patch("app.services.connectors.google_drive.httpx.AsyncClient") as MockCls:
        MockCls.return_value.__aenter__ = AsyncMock(return_value=client)
        MockCls.return_value.__aexit__ = AsyncMock(return_value=None)
        result = asyncio.run(google_drive.list_files(_make_cfg(), "root"))
    assert len(result) == 1
    assert result[0]["name"] == "doc.pdf"


# --- download_file ---

def test_download_file_plain():
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status.return_value = None
    resp.content = b"hello world"
    client = _mock_client(get_resp=resp)
    with patch("app.services.connectors.google_drive.httpx.AsyncClient") as MockCls:
        MockCls.return_value.__aenter__ = AsyncMock(return_value=client)
        MockCls.return_value.__aexit__ = AsyncMock(return_value=None)
        data, fname = asyncio.run(
            google_drive.download_file(_make_cfg(), "file-id", "report.pdf", "application/pdf")
        )
    assert data == b"hello world"
    assert fname == "report.pdf"


def test_download_file_google_doc_exports_as_docx():
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status.return_value = None
    resp.content = b"docx-bytes"
    client = _mock_client(get_resp=resp)
    with patch("app.services.connectors.google_drive.httpx.AsyncClient") as MockCls:
        MockCls.return_value.__aenter__ = AsyncMock(return_value=client)
        MockCls.return_value.__aexit__ = AsyncMock(return_value=None)
        data, fname = asyncio.run(
            google_drive.download_file(
                _make_cfg(), "doc-id", "My Doc",
                "application/vnd.google-apps.document"
            )
        )
    assert data == b"docx-bytes"
    assert fname == "My Doc.docx"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend
python -m pytest tests/test_google_drive_service.py -v
```

Expected: FAIL — module `app.services.connectors.google_drive` does not exist.

- [ ] **Step 3: Create `backend/app/services/connectors/__init__.py`**

Create an empty file:

```python
```

- [ ] **Step 4: Create `backend/app/services/connectors/google_drive.py`**

```python
import secrets
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
        "state": secrets.token_urlsafe(16),
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code(
    code: str, client_id: str, client_secret: str, redirect_uri: str
) -> GoogleDriveConfig:
    async with httpx.AsyncClient() as client:
        resp = client.post(
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
    async with httpx.AsyncClient() as client:
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
    async with httpx.AsyncClient() as client:
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
    async with httpx.AsyncClient() as client:
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
```

- [ ] **Step 5: Run the tests**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend
python -m pytest tests/test_google_drive_service.py -v
```

Expected: All pass.

- [ ] **Step 6: Run full test suite**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend
python -m pytest -v
```

Expected: All pass.

- [ ] **Step 7: Commit**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm
git add backend/app/services/connectors/__init__.py backend/app/services/connectors/google_drive.py backend/tests/test_google_drive_service.py
git commit -m "feat: add Google Drive service (OAuth, list_files, download_file)"
```

---

### Task 3: Connectors API routes

**Files:**
- Create: `backend/app/api/connectors.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_api_connectors.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_api_connectors.py`:

```python
import pytest
import tempfile
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core import config_store
from app.models.settings import AppSettings, GoogleDriveConfig


@pytest.fixture
def client_conn(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setattr(settings, "data_path", tmp)
        monkeypatch.setattr(settings, "api_key", "")
        monkeypatch.setattr(settings, "app_url", "http://localhost:3000")
        monkeypatch.setattr(settings, "backend_url", "http://localhost:8088")
        yield TestClient(app, follow_redirects=False)


def _save_drive_cfg(tmp_path_str: str, **kw):
    s = AppSettings()
    for k, v in kw.items():
        setattr(s.connectors.google_drive, k, v)
    import tempfile, os
    config_store.save(s)


# --- GET /auth-url ---

def test_auth_url_requires_credentials(client_conn):
    response = client_conn.get("/api/connectors/google-drive/auth-url")
    assert response.status_code == 400
    assert "credentials" in response.json()["detail"].lower()


def test_auth_url_returns_google_url(client_conn, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_path", str(tmp_path))
    s = AppSettings()
    s.connectors.google_drive.client_id = "cid"
    s.connectors.google_drive.client_secret = "csecret"
    config_store.save(s)
    response = client_conn.get("/api/connectors/google-drive/auth-url")
    assert response.status_code == 200
    url = response.json()["url"]
    assert "accounts.google.com" in url
    assert "cid" in url


# --- GET /callback ---

def test_callback_error_redirects_to_frontend(client_conn):
    response = client_conn.get("/api/connectors/google-drive/callback?error=access_denied")
    assert response.status_code in (302, 307)
    assert "error=google-drive-denied" in response.headers["location"]


def test_callback_success_saves_tokens_and_redirects(client_conn, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_path", str(tmp_path))
    s = AppSettings()
    s.connectors.google_drive.client_id = "cid"
    s.connectors.google_drive.client_secret = "csecret"
    config_store.save(s)

    fake_cfg = GoogleDriveConfig(
        client_id="cid",
        client_secret="csecret",
        access_token="ya29.new",
        refresh_token="1//refresh",
        token_expiry="2026-12-01T00:00:00",
    )
    with patch(
        "app.api.connectors.google_drive.exchange_code",
        new=AsyncMock(return_value=fake_cfg),
    ):
        response = client_conn.get("/api/connectors/google-drive/callback?code=auth-code")
    assert response.status_code in (302, 307)
    assert "connected=google-drive" in response.headers["location"]
    saved = config_store.load()
    assert saved.connectors.google_drive.access_token == "ya29.new"


# --- DELETE /google-drive ---

def test_disconnect_clears_tokens(client_conn, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_path", str(tmp_path))
    s = AppSettings()
    s.connectors.google_drive.client_id = "cid"
    s.connectors.google_drive.client_secret = "csecret"
    s.connectors.google_drive.access_token = "ya29.token"
    s.connectors.google_drive.refresh_token = "1//refresh"
    s.connectors.google_drive.token_expiry = "2026-01-01T00:00:00"
    config_store.save(s)

    response = client_conn.delete("/api/connectors/google-drive")
    assert response.status_code == 204
    saved = config_store.load()
    assert saved.connectors.google_drive.access_token == ""
    assert saved.connectors.google_drive.refresh_token == ""
    assert saved.connectors.google_drive.token_expiry == ""
    assert saved.connectors.google_drive.client_id == "cid"
    assert saved.connectors.google_drive.client_secret == "csecret"


# --- GET /files ---

def test_files_requires_access_token(client_conn):
    response = client_conn.get("/api/connectors/google-drive/files")
    assert response.status_code == 401


def test_files_returns_file_list(client_conn, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_path", str(tmp_path))
    s = AppSettings()
    s.connectors.google_drive.access_token = "ya29.valid"
    s.connectors.google_drive.refresh_token = "1//r"
    s.connectors.google_drive.token_expiry = "2099-01-01T00:00:00+00:00"
    config_store.save(s)

    fake_files = [{"id": "f1", "name": "doc.pdf", "mimeType": "application/pdf",
                   "size": 100, "modifiedTime": "2026-01-01T00:00:00Z", "isFolder": False}]
    with patch(
        "app.api.connectors.google_drive.list_files",
        new=AsyncMock(return_value=fake_files),
    ), patch(
        "app.api.connectors.google_drive.refresh_token_if_needed",
        new=AsyncMock(side_effect=lambda c: c),
    ):
        response = client_conn.get("/api/connectors/google-drive/files?folder_id=root")
    assert response.status_code == 200
    body = response.json()
    assert body["folder_id"] == "root"
    assert len(body["files"]) == 1


# --- POST /ingest ---

def test_ingest_requires_access_token(client_conn):
    body = {"file_id": "f1", "file_name": "doc.pdf", "mime_type": "application/pdf"}
    response = client_conn.post("/api/connectors/google-drive/ingest", json=body)
    assert response.status_code == 401


def test_ingest_file_too_large(client_conn, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_path", str(tmp_path))
    s = AppSettings()
    s.connectors.google_drive.access_token = "ya29.valid"
    s.connectors.google_drive.token_expiry = "2099-01-01T00:00:00+00:00"
    config_store.save(s)

    big = b"x" * (10 * 1024 * 1024 + 1)
    with patch(
        "app.api.connectors.google_drive.refresh_token_if_needed",
        new=AsyncMock(side_effect=lambda c: c),
    ), patch(
        "app.api.connectors.google_drive.download_file",
        new=AsyncMock(return_value=(big, "big.pdf")),
    ):
        body = {"file_id": "f1", "file_name": "big.pdf", "mime_type": "application/pdf"}
        response = client_conn.post("/api/connectors/google-drive/ingest", json=body)
    assert response.status_code == 413
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend
python -m pytest tests/test_api_connectors.py -v
```

Expected: FAIL — module / routes not found.

- [ ] **Step 3: Create `backend/app/api/connectors.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from ..core.auth import verify_api_key
from ..core.config import settings
from ..core import config_store
from ..models.settings import GoogleDriveConfig
from ..services.connectors import google_drive
from ..services.connectors.google_drive import (
    build_auth_url,
    exchange_code,
    refresh_token_if_needed,
    list_files,
    download_file,
)
from ..services.file_extractor import extract_text
from ..services.ingest_service import ingest_text
from ..models.ingest import IngestResult

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
    if error:
        return RedirectResponse(
            f"{settings.app_url}/settings?error=google-drive-denied", status_code=302
        )
    if not code:
        return RedirectResponse(
            f"{settings.app_url}/settings?error=google-drive-denied", status_code=302
        )
    cfg = config_store.load().connectors.google_drive
    try:
        new_cfg = await exchange_code(code, cfg.client_id, cfg.client_secret, _redirect_uri())
    except Exception:
        return RedirectResponse(
            f"{settings.app_url}/settings?error=google-drive-denied", status_code=302
        )
    full = config_store.load()
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
        cfg = await refresh_token_if_needed(cfg)
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
        cfg = await refresh_token_if_needed(cfg)
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
```

- [ ] **Step 4: Register the router in `backend/app/main.py`**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.health import router as health_router
from .api.pages import router as pages_router
from .api.search import router as search_router
from .api.ingest import router as ingest_router
from .api.answer import router as answer_router
from .api.log import router as log_router
from .api.references import router as references_router
from .api.settings import router as settings_router
from .api.connectors import router as connectors_router
from .mcp.server import mcp

_mcp_http = mcp.http_app(transport="streamable-http")
_mcp_sse = mcp.http_app(transport="sse")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    async with _mcp_http.lifespan(app):
        yield


app = FastAPI(title="OpenWikiLLM", version="0.1.0", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(pages_router)
app.include_router(search_router)
app.include_router(ingest_router)
app.include_router(answer_router)
app.include_router(log_router)
app.include_router(references_router)
app.include_router(settings_router)
app.include_router(connectors_router)

app.mount("/mcp", _mcp_http)
app.mount("/mcp-sse", _mcp_sse)
```

- [ ] **Step 5: Run the connector API tests**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend
python -m pytest tests/test_api_connectors.py -v
```

Expected: All pass.

- [ ] **Step 6: Run full test suite**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend
python -m pytest -v
```

Expected: All pass.

- [ ] **Step 7: Commit**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm
git add backend/app/api/connectors.py backend/app/main.py backend/tests/test_api_connectors.py
git commit -m "feat: add Google Drive connector API (auth-url, callback, files, ingest, disconnect)"
```

---

### Task 4: Frontend types and useGoogleDrive composable

**Files:**
- Modify: `frontend/types/api.ts`
- Create: `frontend/composables/useGoogleDrive.ts`

- [ ] **Step 1: Update `frontend/types/api.ts`**

Append the following to the existing file (after the existing `AppSettings` interface — replace `AppSettings` and add new interfaces):

```typescript
export interface GoogleDriveConfig {
  client_id: string
  client_secret: string
  access_token: string
  refresh_token: string
  token_expiry: string
}

export interface ConnectorsConfig {
  google_drive: GoogleDriveConfig
}

export interface AppSettings {
  llm: LLMConfig
  ingest: IngestConfig
  connectors: ConnectorsConfig
}

export interface GoogleDriveFile {
  id: string
  name: string
  mimeType: string
  size?: number
  modifiedTime: string
  isFolder: boolean
}

export interface GoogleDriveListResponse {
  files: GoogleDriveFile[]
  folder_id: string
}
```

The existing `AppSettings` interface (lines 103–106) must be replaced with the new one that includes `connectors`. The file after the edit should end with the `GoogleDriveListResponse` interface.

- [ ] **Step 2: Create `frontend/composables/useGoogleDrive.ts`**

```typescript
import { useApi } from '~/composables/useApi'
import type { GoogleDriveListResponse, IngestResult } from '~/types/api'

export function useGoogleDrive() {
  const { get, post, del } = useApi()

  async function getAuthUrl(): Promise<string> {
    const data = await get<{ url: string }>('/api/connectors/google-drive/auth-url')
    return data.url
  }

  async function disconnect(): Promise<void> {
    await del('/api/connectors/google-drive')
  }

  async function listFiles(folderId = 'root'): Promise<GoogleDriveListResponse> {
    return get<GoogleDriveListResponse>(
      `/api/connectors/google-drive/files?folder_id=${encodeURIComponent(folderId)}`
    )
  }

  async function ingestFile(
    fileId: string,
    fileName: string,
    mimeType: string,
    title?: string,
    tags: string[] = [],
  ): Promise<IngestResult> {
    return post<IngestResult>('/api/connectors/google-drive/ingest', {
      file_id: fileId,
      file_name: fileName,
      mime_type: mimeType,
      title,
      tags,
    })
  }

  return { getAuthUrl, disconnect, listFiles, ingestFile }
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/frontend
npx nuxi typecheck 2>&1 | head -30
```

Expected: No errors related to the new types or composable.

- [ ] **Step 4: Commit**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm
git add frontend/types/api.ts frontend/composables/useGoogleDrive.ts
git commit -m "feat(frontend): add Google Drive types and useGoogleDrive composable"
```

---

### Task 5: ConnectorsSettings component and settings page update

**Files:**
- Create: `frontend/components/settings/ConnectorsSettings.vue`
- Modify: `frontend/pages/settings.vue`

- [ ] **Step 1: Create `frontend/components/settings/ConnectorsSettings.vue`**

```vue
<template>
  <div class="space-y-4">
    <div class="p-4 border border-gray-700 rounded-lg space-y-4">
      <div class="flex items-center justify-between">
        <span class="text-sm font-medium text-white">Google Drive</span>
        <span
          :class="[
            'text-xs px-2 py-0.5 rounded-full font-medium',
            isConnected ? 'bg-green-900 text-green-300' : 'bg-gray-800 text-gray-400',
          ]"
        >
          {{ isConnected ? 'Connecté' : 'Non connecté' }}
        </span>
      </div>

      <div class="space-y-2">
        <div>
          <label class="block text-xs text-gray-400 mb-1">Client ID</label>
          <input
            v-model="local.client_id"
            type="text"
            placeholder="xxx.apps.googleusercontent.com"
            class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
            @input="emit('update:modelValue', { ...local })"
          />
        </div>
        <div>
          <label class="block text-xs text-gray-400 mb-1">Client Secret</label>
          <div class="relative">
            <input
              v-model="local.client_secret"
              :type="showSecret ? 'text' : 'password'"
              placeholder="GOCSPX-..."
              class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500 pr-10"
              @input="emit('update:modelValue', { ...local })"
            />
            <button
              type="button"
              class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
              @click="showSecret = !showSecret"
            >
              <component :is="showSecret ? EyeOff : Eye" class="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      <div class="flex gap-2">
        <button
          v-if="!isConnected"
          class="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm rounded-lg transition-colors"
          :disabled="connecting"
          @click="handleConnect"
        >
          {{ connecting ? 'Redirection…' : 'Connecter à Google Drive' }}
        </button>
        <button
          v-else
          class="px-3 py-1.5 bg-red-700 hover:bg-red-600 text-white text-sm rounded-lg transition-colors"
          @click="emit('disconnect')"
        >
          Déconnecter
        </button>
      </div>

      <p v-if="connectError" class="text-xs text-red-400">{{ connectError }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, computed, ref, watch } from 'vue'
import { Eye, EyeOff } from 'lucide-vue-next'
import type { ConnectorsConfig } from '~/types/api'

const props = defineProps<{ modelValue: ConnectorsConfig }>()
const emit = defineEmits<{
  'update:modelValue': [ConnectorsConfig]
  'connect': []
  'disconnect': []
}>()

const local = reactive({ ...props.modelValue, google_drive: { ...props.modelValue.google_drive } })
watch(() => props.modelValue, (v) => {
  Object.assign(local, v)
  Object.assign(local.google_drive, v.google_drive)
})

const showSecret = ref(false)
const connecting = ref(false)
const connectError = ref<string | null>(null)

const isConnected = computed(() => local.google_drive.access_token === '****')

function handleConnect() {
  if (!local.google_drive.client_id || !local.google_drive.client_secret) {
    connectError.value = 'Enregistrez d\'abord vos credentials Google Drive'
    return
  }
  connectError.value = null
  connecting.value = true
  emit('connect')
}
</script>
```

- [ ] **Step 2: Update `frontend/pages/settings.vue`**

```vue
<template>
  <div class="max-w-2xl mx-auto py-10 px-6 space-y-8">
    <div>
      <h1 class="text-xl font-bold text-white">
        {{ isSetupMode ? 'Configuration initiale' : 'Paramètres' }}
      </h1>
      <p v-if="isSetupMode" class="text-sm text-gray-400 mt-1">
        Configurez votre provider LLM pour commencer à utiliser OpenWikiLLM.
      </p>
    </div>

    <div v-if="settings" class="space-y-8">
      <section class="p-4 bg-gray-900 border border-gray-800 rounded-xl space-y-4">
        <h2 class="text-sm font-semibold text-gray-300 uppercase tracking-wider">LLM</h2>
        <SettingsLLMSettings v-model="settings.llm" />
      </section>

      <section class="p-4 bg-gray-900 border border-gray-800 rounded-xl space-y-4">
        <h2 class="text-sm font-semibold text-gray-300 uppercase tracking-wider">Ingestion</h2>
        <SettingsIngestSettings v-model="settings.ingest" />
      </section>

      <section class="p-4 bg-gray-900 border border-gray-800 rounded-xl space-y-4">
        <h2 class="text-sm font-semibold text-gray-300 uppercase tracking-wider">Connecteurs</h2>
        <SettingsConnectorsSettings
          v-model="settings.connectors"
          @connect="handleConnect"
          @disconnect="handleDisconnect"
        />
      </section>

      <div class="flex items-center gap-4">
        <button
          :disabled="saving"
          class="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
          @click="handleSave"
        >
          {{ saving ? 'Enregistrement…' : 'Enregistrer' }}
        </button>
        <p v-if="saved" class="text-green-400 text-sm">Paramètres enregistrés.</p>
        <p v-if="saveError" class="text-red-400 text-sm">{{ saveError }}</p>
      </div>
    </div>

    <div v-else class="text-gray-400 text-sm">Chargement…</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const { settings, saving, saveError, fetchSettings, saveSettings, isConfigured } = useSettings()
const { getAuthUrl, disconnect } = useGoogleDrive()
const router = useRouter()
const route = useRoute()
const saved = ref(false)
const isSetupMode = computed(() => !isConfigured())

onMounted(async () => {
  await fetchSettings()
  if (route.query.connected === 'google-drive') {
    await fetchSettings()
    saved.value = true
    await router.replace('/settings')
  }
  if (route.query.error === 'google-drive-denied') {
    await router.replace('/settings')
  }
})

async function handleSave() {
  if (!settings.value) return
  saved.value = false
  const wasSetupMode = isSetupMode.value
  try {
    await saveSettings(settings.value)
    const llmReady = useState('llm-ready', () => false)
    llmReady.value = true
    saved.value = true
    if (wasSetupMode) {
      await router.push('/chat')
    }
  } catch {
    // saveError is handled in useSettings
  }
}

async function handleConnect() {
  if (!settings.value) return
  try {
    await saveSettings(settings.value)
    const url = await getAuthUrl()
    window.location.href = url
  } catch {
    // error displayed by ConnectorsSettings component
  }
}

async function handleDisconnect() {
  try {
    await disconnect()
    await fetchSettings()
  } catch {
    // ignore
  }
}
</script>
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/frontend
npx nuxi typecheck 2>&1 | head -30
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm
git add frontend/components/settings/ConnectorsSettings.vue frontend/pages/settings.vue
git commit -m "feat(frontend): add ConnectorsSettings component and OAuth flow in settings page"
```

---

### Task 6: GoogleDriveTab component and ingest page update

**Files:**
- Create: `frontend/components/ingest/GoogleDriveTab.vue`
- Modify: `frontend/pages/ingest.vue`

- [ ] **Step 1: Create `frontend/components/ingest/GoogleDriveTab.vue`**

```vue
<template>
  <div class="space-y-4">
    <!-- Not connected -->
    <div v-if="!isConnected" class="text-center py-12 space-y-3">
      <p class="text-gray-400 text-sm">Google Drive n'est pas connecté.</p>
      <NuxtLink to="/settings" class="text-blue-400 hover:text-blue-300 text-sm underline">
        Configurer dans les Paramètres
      </NuxtLink>
    </div>

    <!-- Connected -->
    <div v-else class="space-y-4">
      <!-- Breadcrumb -->
      <nav class="flex items-center gap-1 text-sm text-gray-400 flex-wrap">
        <button
          class="hover:text-white transition-colors"
          @click="navigateTo('root', 'Mon Drive', 0)"
        >
          Mon Drive
        </button>
        <template v-for="(crumb, i) in breadcrumb" :key="crumb.id">
          <span class="text-gray-600">/</span>
          <button
            class="hover:text-white transition-colors"
            @click="navigateTo(crumb.id, crumb.name, i + 1)"
          >
            {{ crumb.name }}
          </button>
        </template>
      </nav>

      <!-- Loading -->
      <div v-if="loading" class="text-gray-400 text-sm text-center py-8">Chargement…</div>

      <!-- Error -->
      <p v-else-if="listError" class="text-red-400 text-sm">{{ listError }}</p>

      <!-- File list -->
      <ul v-else class="divide-y divide-gray-800">
        <li
          v-for="file in files"
          :key="file.id"
          class="flex items-center justify-between py-3 gap-4"
        >
          <div class="flex items-center gap-3 min-w-0">
            <component
              :is="file.isFolder ? Folder : FileText"
              class="w-4 h-4 shrink-0 text-gray-400"
            />
            <button
              v-if="file.isFolder"
              class="text-sm text-white hover:text-blue-400 transition-colors truncate text-left"
              @click="openFolder(file)"
            >
              {{ file.name }}
            </button>
            <span v-else class="text-sm text-white truncate">{{ file.name }}</span>
          </div>

          <div v-if="!file.isFolder" class="flex items-center gap-3 shrink-0">
            <!-- Ingest result inline -->
            <div v-if="ingestResults[file.id]" class="text-xs text-green-400">
              {{ ingestResults[file.id].slug }} ingéré
            </div>
            <div v-if="ingestErrors[file.id]" class="text-xs text-red-400">
              {{ ingestErrors[file.id] }}
            </div>
            <button
              :disabled="!!ingestingIds[file.id]"
              class="px-3 py-1 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs rounded-lg transition-colors shrink-0"
              @click="handleIngest(file)"
            >
              {{ ingestingIds[file.id] ? 'Ingestion…' : 'Ingérer' }}
            </button>
          </div>
        </li>

        <li v-if="files.length === 0" class="py-8 text-center text-gray-500 text-sm">
          Dossier vide
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { Folder, FileText } from 'lucide-vue-next'
import type { GoogleDriveFile, IngestResult } from '~/types/api'

const { fetchSettings, settings } = useSettings()
const { listFiles, ingestFile } = useGoogleDrive()

const isConnected = computed(
  () => settings.value?.connectors?.google_drive?.access_token === '****'
)

interface Crumb { id: string; name: string }

const breadcrumb = ref<Crumb[]>([])
const files = ref<GoogleDriveFile[]>([])
const loading = ref(false)
const listError = ref<string | null>(null)
const currentFolderId = ref('root')

const ingestingIds = reactive<Record<string, boolean>>({})
const ingestResults = reactive<Record<string, IngestResult>>({})
const ingestErrors = reactive<Record<string, string>>({})

onMounted(async () => {
  await fetchSettings()
  if (isConnected.value) {
    await loadFiles('root')
  }
})

async function loadFiles(folderId: string) {
  loading.value = true
  listError.value = null
  currentFolderId.value = folderId
  try {
    const resp = await listFiles(folderId)
    files.value = resp.files
  } catch (e: unknown) {
    listError.value = e instanceof Error ? e.message : 'Erreur lors du chargement'
  } finally {
    loading.value = false
  }
}

async function openFolder(file: GoogleDriveFile) {
  breadcrumb.value.push({ id: file.id, name: file.name })
  await loadFiles(file.id)
}

async function navigateTo(folderId: string, _name: string, crumbIndex: number) {
  if (folderId === 'root') {
    breadcrumb.value = []
  } else {
    breadcrumb.value = breadcrumb.value.slice(0, crumbIndex)
  }
  await loadFiles(folderId)
}

async function handleIngest(file: GoogleDriveFile) {
  ingestingIds[file.id] = true
  delete ingestErrors[file.id]
  delete ingestResults[file.id]
  try {
    const result = await ingestFile(file.id, file.name, file.mimeType, file.name)
    ingestResults[file.id] = result
  } catch (e: unknown) {
    ingestErrors[file.id] = e instanceof Error ? e.message : 'Erreur lors de l\'ingestion'
  } finally {
    ingestingIds[file.id] = false
  }
}
</script>
```

- [ ] **Step 2: Update `frontend/pages/ingest.vue`**

```vue
<template>
  <div class="p-6 max-w-2xl mx-auto space-y-6">
    <h2 class="text-lg font-semibold text-white">Ingestion</h2>

    <div class="flex border-b border-gray-800">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        :class="[
          'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
          activeTab === tab.id
            ? 'border-blue-500 text-blue-400'
            : 'border-transparent text-gray-400 hover:text-white',
        ]"
        @click="activeTab = tab.id"
      >
        <component :is="tab.icon" class="inline w-4 h-4 mr-1" />
        {{ tab.label }}
      </button>
    </div>

    <IngestText v-if="activeTab === 'text'" />
    <IngestImage v-else-if="activeTab === 'image'" />
    <IngestFile v-else-if="activeTab === 'file'" />
    <IngestGoogleDriveTab v-else-if="activeTab === 'gdrive'" />
  </div>
</template>

<script setup lang="ts">
import { FileText, ImageIcon, FolderOpen, HardDrive } from 'lucide-vue-next'
import IngestFile from '~/components/ingest/IngestFile.vue'

const activeTab = ref<'text' | 'image' | 'file' | 'gdrive'>('text')
const tabs = [
  { id: 'text' as const, label: 'Texte', icon: FileText },
  { id: 'image' as const, label: 'Image', icon: ImageIcon },
  { id: 'file' as const, label: 'Fichiers', icon: FolderOpen },
  { id: 'gdrive' as const, label: 'Google Drive', icon: HardDrive },
]
</script>
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/frontend
npx nuxi typecheck 2>&1 | head -30
```

Expected: No errors.

- [ ] **Step 4: Run backend tests one final time**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend
python -m pytest -v
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm
git add frontend/components/ingest/GoogleDriveTab.vue frontend/pages/ingest.vue
git commit -m "feat(frontend): add GoogleDriveTab and Google Drive ingest tab"
```

---

## Post-implementation checklist

- [ ] Add to `.env` (or `.env.example`):
  ```
  OPENWIKILLM_APP_URL=http://localhost:3000
  OPENWIKILLM_BACKEND_URL=http://localhost:8088
  ```
- [ ] Update `CHANGELOG.md` with the new feature
- [ ] Create `docs/dev-notes/2026-05-29-google-drive-connector.md`
