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
    with patch("app.services.connectors.google_drive.httpx.AsyncClient") as MockCls:
        MockCls.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        MockCls.return_value.__aexit__ = AsyncMock(return_value=None)
        result = asyncio.run(google_drive.refresh_token_if_needed(cfg))
        # Client should never be entered for a fresh token
        MockCls.return_value.__aenter__.assert_not_called()
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
