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


def _write_page(wiki_path: str, slug: str) -> None:
    parts = slug.split("--", 1)
    p = Path(wiki_path, parts[0], f"{parts[1]}.md")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "---\ntitle: Test\ntype: concept\n---\n\n# Test\n",
        encoding="utf-8",
    )


def test_set_stale_true(client_with_dirs):
    _write_page(settings.wiki_path, "concept--groove")
    response = client_with_dirs.patch(
        "/api/pages/concept--groove/stale", json={"stale": True}
    )
    assert response.status_code == 200
    assert response.json()["stale"] is True


def test_set_stale_false(client_with_dirs):
    _write_page(settings.wiki_path, "concept--groove")
    client_with_dirs.patch("/api/pages/concept--groove/stale", json={"stale": True})
    response = client_with_dirs.patch(
        "/api/pages/concept--groove/stale", json={"stale": False}
    )
    assert response.status_code == 200
    assert response.json()["stale"] is False


def test_set_stale_unknown(client_with_dirs):
    response = client_with_dirs.patch(
        "/api/pages/concept--does-not-exist/stale", json={"stale": True}
    )
    assert response.status_code == 404
