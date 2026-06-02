import pytest
import tempfile
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.core import config_store
from app.models.settings import AppSettings


@pytest.fixture
def client_settings(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setattr(settings, "data_path", tmp)
        monkeypatch.setattr(settings, "api_key", "")
        yield TestClient(app)


def test_get_settings_returns_defaults(client_settings):
    response = client_settings.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["llm"]["provider"] == "ollama"
    assert data["ingest"]["max_text_chars"] == 30000


def test_get_settings_masks_api_key(client_settings, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_path", str(tmp_path))
    s = AppSettings()
    s.llm.provider = "openai"
    s.llm.openai.api_key = "sk-real-key"
    config_store.save(s)
    response = client_settings.get("/api/settings")
    assert response.json()["llm"]["openai"]["api_key"] == "****"


def test_put_settings_saves_and_returns(client_settings):
    payload = {
        "llm": {
            "provider": "openai",
            "ollama": {"base_url": "http://host.docker.internal:11434", "model": "mistral", "vision_model": "llava"},
            "openai": {"api_key": "sk-new", "model": "gpt-4o", "vision_model": "gpt-4o"},
            "gemini": {"api_key": "", "model": "gemini-1.5-pro", "vision_model": "gemini-1.5-pro"},
            "anthropic": {"api_key": "", "model": "claude-opus-4-7", "vision_model": "claude-opus-4-7"},
            "custom": {"base_url": "", "api_key": "", "model": "", "vision_model": ""},
        },
        "ingest": {"max_text_chars": 20000},
    }
    response = client_settings.put("/api/settings", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["llm"]["provider"] == "openai"
    assert data["llm"]["openai"]["api_key"] == "****"
    assert data["ingest"]["max_text_chars"] == 20000


def test_put_settings_preserves_existing_api_key_when_masked(client_settings, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_path", str(tmp_path))
    s = AppSettings()
    s.llm.openai.api_key = "sk-original"
    config_store.save(s)

    payload = {
        "llm": {
            "provider": "openai",
            "ollama": {"base_url": "", "model": "mistral", "vision_model": "llava"},
            "openai": {"api_key": "****", "model": "gpt-4o", "vision_model": "gpt-4o"},
            "gemini": {"api_key": "", "model": "gemini-1.5-pro", "vision_model": "gemini-1.5-pro"},
            "anthropic": {"api_key": "", "model": "claude-opus-4-7", "vision_model": "claude-opus-4-7"},
            "custom": {"base_url": "", "api_key": "", "model": "", "vision_model": ""},
        },
        "ingest": {"max_text_chars": 30000},
    }
    client_settings.put("/api/settings", json=payload)
    saved = config_store.load()
    assert saved.llm.openai.api_key == "sk-original"


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


def test_git_settings_defaults():
    from app.models.settings import AppSettings
    s = AppSettings()
    assert s.git.enabled is False
    assert s.git.auto_push is False
    assert s.git.remote_url == ""
    assert s.git.branch == "main"


def test_git_settings_persisted(tmp_path, monkeypatch):
    from app.core.config import settings as core_settings
    monkeypatch.setattr(core_settings, "data_path", str(tmp_path))
    from app.core import config_store
    cfg = config_store.load()
    cfg.git.enabled = True
    cfg.git.branch = "wiki"
    config_store.save(cfg)
    reloaded = config_store.load()
    assert reloaded.git.enabled is True
    assert reloaded.git.branch == "wiki"
