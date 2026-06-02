import pytest
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
import frontmatter as fm
from app.main import app
from app.core.config import settings


@pytest.fixture
def client_with_wiki(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        wiki = Path(tmp)
        (wiki / "concepts").mkdir()
        page = wiki / "concepts" / "livraison.md"
        post = fm.Post(
            "## Résumé\n\nLivraison en 24h.",
            title="Livraison 24h",
            type="concept",
            status="validated",
            confidence="high",
            tags=["livraison"],
            sources=[],
            updated_at="2026-05-12",
        )
        page.write_text(fm.dumps(post))
        monkeypatch.setattr(settings, "api_key", "")
        monkeypatch.setattr(settings, "wiki_path", str(wiki))
        yield TestClient(app)


def test_list_pages(client_with_wiki):
    response = client_with_wiki.get("/api/pages")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Livraison 24h"


def test_get_page_found(client_with_wiki):
    response = client_with_wiki.get("/api/pages/concepts--livraison")
    assert response.status_code == 200
    assert response.json()["title"] == "Livraison 24h"


def test_get_page_not_found(client_with_wiki):
    response = client_with_wiki.get("/api/pages/nonexistent")
    assert response.status_code == 404


def test_api_requires_key_when_set(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "secret")
    client = TestClient(app)
    response = client.get("/api/pages")
    assert response.status_code == 401


def test_delete_page(client_with_wiki):
    response = client_with_wiki.delete("/api/pages/concepts--livraison")
    assert response.status_code == 204


def test_delete_page_not_found(client_with_wiki):
    response = client_with_wiki.delete("/api/pages/nonexistent--page")
    assert response.status_code == 404


def test_delete_page_removes_from_list(client_with_wiki):
    client_with_wiki.delete("/api/pages/concepts--livraison")
    response = client_with_wiki.get("/api/pages")
    assert response.status_code == 200
    assert len(response.json()) == 0


def test_delete_page_calls_git_commit(monkeypatch):
    from unittest.mock import patch
    with tempfile.TemporaryDirectory() as tmp:
        wiki = Path(tmp)
        (wiki / "concepts").mkdir()
        page = wiki / "concepts" / "livraison.md"
        post = fm.Post(
            "## Résumé\n\nLivraison en 24h.",
            title="Livraison 24h",
            type="concept",
            status="validated",
            confidence="high",
            tags=[],
            sources=[],
            updated_at="2026-06-02",
        )
        page.write_text(fm.dumps(post))
        monkeypatch.setattr(settings, "api_key", "")
        monkeypatch.setattr(settings, "wiki_path", str(wiki))
        with patch("app.api.pages.git_service.commit_edit", return_value="abc1234") as mock_git:
            client = TestClient(app)
            response = client.delete("/api/pages/concepts--livraison")
        assert response.status_code == 204
        mock_git.assert_called_once_with("concepts--livraison", "delete")
