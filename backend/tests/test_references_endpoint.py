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
        # Initialize the DB schema (creates page_references table)
        from app.storage.search import SearchIndex
        SearchIndex(Path(data_tmp) / "openwikillm.db")
        yield TestClient(app)


def test_references_endpoint_no_pages(client_with_dirs):
    response = client_with_dirs.get("/api/pages/concept--groove/references")
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "concept--groove"
    assert data["references"] == []
    assert data["referenced_by"] == []


def test_references_endpoint_with_source(client_with_dirs):
    wiki_tmp = settings.wiki_path
    p = Path(wiki_tmp, "concept", "groove.md")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "---\ntitle: Groove\nsources:\n  - imports--ticket-doc\n---\n\n# Groove\n",
        encoding="utf-8",
    )
    from app.services.reference_service import rebuild_references
    rebuild_references()
    response = client_with_dirs.get("/api/pages/concept--groove/references")
    assert response.status_code == 200
    data = response.json()
    assert "imports--ticket-doc" in data["references"]
