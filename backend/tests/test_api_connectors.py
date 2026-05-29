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
        "app.api.connectors.exchange_code",
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
        "app.api.connectors.list_files",
        new=AsyncMock(return_value=fake_files),
    ), patch(
        "app.api.connectors.refresh_token_if_needed",
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
        "app.api.connectors.refresh_token_if_needed",
        new=AsyncMock(side_effect=lambda c: c),
    ), patch(
        "app.api.connectors.download_file",
        new=AsyncMock(return_value=(big, "big.pdf")),
    ):
        body = {"file_id": "f1", "file_name": "big.pdf", "mime_type": "application/pdf"}
        response = client_conn.post("/api/connectors/google-drive/ingest", json=body)
    assert response.status_code == 413
