import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
import pytest


@pytest.fixture
def client_with_dirs(monkeypatch):
    with tempfile.TemporaryDirectory() as wiki_tmp, \
         tempfile.TemporaryDirectory() as raw_tmp, \
         tempfile.TemporaryDirectory() as data_tmp:
        monkeypatch.setattr(settings, "wiki_path", wiki_tmp)
        monkeypatch.setattr(settings, "raw_path", raw_tmp)
        monkeypatch.setattr(settings, "data_path", data_tmp)
        monkeypatch.setattr(settings, "api_key", "")
        yield TestClient(app)


def test_log_endpoint_empty(client_with_dirs):
    response = client_with_dirs.get("/api/wiki/log")
    assert response.status_code == 200
    assert response.json()["content"] == ""


def test_log_endpoint_with_content(client_with_dirs):
    (Path(settings.wiki_path) / "log.md").write_text(
        "# Journal\n\n## test", encoding="utf-8"
    )
    response = client_with_dirs.get("/api/wiki/log")
    assert response.status_code == 200
    assert "Journal" in response.json()["content"]
