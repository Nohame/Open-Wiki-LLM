import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch
import httpx
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.storage.wiki import load_page

MOCK_MARKDOWN = """\
---
title: Test Ingestion
type: concept
status: draft
confidence: medium
sources: []
updated_at: 2026-05-12
tags: ["test"]
---

# Test Ingestion

## Résumé

Contenu structuré par Ollama.

## Règles connues

## Points à confirmer
"""

MOCK_XML = f'<page slug="imports--test-ingestion">{MOCK_MARKDOWN}</page>'

CONCEPT_MARKDOWN = """\
---
title: Groove
type: concept
status: draft
confidence: medium
sources: []
updated_at: 2026-05-15
tags: []
---

# Groove

## Résumé

Outil de gestion tickets.
"""

ENTITY_MARKDOWN = """\
---
title: Alizee
type: entity
status: draft
confidence: medium
sources: []
updated_at: 2026-05-15
tags: []
---

# Alizee

## Résumé

Responsable logistique.
"""


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


def test_ingest_text_creates_files(client_with_dirs):
    with patch("app.services.ingest_service.identify_related_pages", new=AsyncMock(return_value=[])), \
         patch("app.services.ingest_service.compile_multi_page", new=AsyncMock(return_value=MOCK_XML)):
        response = client_with_dirs.post(
            "/api/ingest/text",
            json={"text": "Texte source brut.", "title": "Test Ingestion", "tags": ["test"]},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "imports--test-ingestion"
    assert Path(data["raw_path"]).exists()
    assert Path(data["wiki_path"]).exists()
    assert data["pages_updated"] == []
    assert data["concepts_created"] == []
    assert data["entities_created"] == []
    assert data["stale_marked"] == []


def test_ingest_text_without_title(client_with_dirs):
    mock_xml = f'<page slug="imports--source-sans-titre">{MOCK_MARKDOWN}</page>'
    with patch("app.services.ingest_service.identify_related_pages", new=AsyncMock(return_value=[])), \
         patch("app.services.ingest_service.compile_multi_page", new=AsyncMock(return_value=mock_xml)):
        response = client_with_dirs.post(
            "/api/ingest/text",
            json={"text": "Texte sans titre."},
        )
    assert response.status_code == 200


def test_ingest_text_multi_page(client_with_dirs):
    wiki_tmp = settings.wiki_path
    Path(wiki_tmp, "imports").mkdir(parents=True, exist_ok=True)
    Path(wiki_tmp, "imports", "existing.md").write_text(
        "---\ntitle: Existing\n---\n\n## Résumé\n\nPage existante.\n",
        encoding="utf-8",
    )

    xml_two_pages = (
        f'<page slug="imports--test-ingestion">{MOCK_MARKDOWN}</page>\n'
        '<page slug="imports--existing">---\ntitle: Existing\n---\n\n## Résumé\n\nMis à jour.\n</page>'
    )
    with patch("app.services.ingest_service.identify_related_pages", new=AsyncMock(return_value=["imports--existing"])), \
         patch("app.services.ingest_service.compile_multi_page", new=AsyncMock(return_value=xml_two_pages)):
        response = client_with_dirs.post(
            "/api/ingest/text",
            json={"text": "Texte source.", "title": "Test Ingestion", "tags": []},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["pages_updated"] == ["imports--existing"]
    assert data["concepts_created"] == []
    assert data["entities_created"] == []
    assert data["stale_marked"] == []
    assert Path(wiki_tmp, "index.md").exists()


def test_ingest_text_no_related(client_with_dirs):
    with patch("app.services.ingest_service.identify_related_pages", new=AsyncMock(return_value=[])), \
         patch("app.services.ingest_service.compile_multi_page", new=AsyncMock(return_value=MOCK_XML)):
        response = client_with_dirs.post(
            "/api/ingest/text",
            json={"text": "Texte source.", "title": "Test Ingestion", "tags": []},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["pages_updated"] == []
    assert data["concepts_created"] == []
    assert data["entities_created"] == []
    assert data["stale_marked"] == []


def test_ingest_text_with_concepts(client_with_dirs):
    xml_with_concept = (
        f'<page slug="imports--test-ingestion">{MOCK_MARKDOWN}</page>\n'
        f'<page slug="concept--groove">{CONCEPT_MARKDOWN}</page>'
    )
    with patch("app.services.ingest_service.identify_related_pages", new=AsyncMock(return_value=[])), \
         patch("app.services.ingest_service.compile_multi_page", new=AsyncMock(return_value=xml_with_concept)):
        response = client_with_dirs.post(
            "/api/ingest/text",
            json={"text": "On utilise Groove pour les tickets.", "title": "Test Ingestion", "tags": ["test"]},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["concepts_created"] == ["concept--groove"]
    assert data["entities_created"] == []
    assert data["pages_updated"] == []
    assert data["stale_marked"] == []
    assert Path(settings.wiki_path, "concept", "groove.md").exists()


def test_ingest_text_with_entities(client_with_dirs):
    xml_with_entity = (
        f'<page slug="imports--test-ingestion">{MOCK_MARKDOWN}</page>\n'
        f'<page slug="entity--alizee">{ENTITY_MARKDOWN}</page>'
    )
    with patch("app.services.ingest_service.identify_related_pages", new=AsyncMock(return_value=[])), \
         patch("app.services.ingest_service.compile_multi_page", new=AsyncMock(return_value=xml_with_entity)):
        response = client_with_dirs.post(
            "/api/ingest/text",
            json={"text": "Alizee gère la logistique.", "title": "Test Ingestion", "tags": []},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["entities_created"] == ["entity--alizee"]
    assert data["concepts_created"] == []
    assert data["pages_updated"] == []
    assert data["stale_marked"] == []
    assert Path(settings.wiki_path, "entity", "alizee.md").exists()


def test_ingest_file_endpoint_txt(client_with_dirs):
    mock_xml = f'<page slug="imports--rapport">{MOCK_MARKDOWN}</page>'
    with patch("app.services.ingest_service.identify_related_pages", new=AsyncMock(return_value=[])), \
         patch("app.services.ingest_service.compile_multi_page", new=AsyncMock(return_value=mock_xml)):
        response = client_with_dirs.post(
            "/api/ingest/file",
            files={"file": ("rapport.txt", b"Contenu du fichier texte.", "text/plain")},
            data={"tags": "test"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "imports--rapport"
    assert data["title"] == "rapport"


def test_ingest_file_endpoint_with_title(client_with_dirs):
    mock_xml = f'<page slug="imports--mon-titre-custom">{MOCK_MARKDOWN}</page>'
    with patch("app.services.ingest_service.identify_related_pages", new=AsyncMock(return_value=[])), \
         patch("app.services.ingest_service.compile_multi_page", new=AsyncMock(return_value=mock_xml)):
        response = client_with_dirs.post(
            "/api/ingest/file",
            files={"file": ("doc.md", b"# Titre\n\nContenu.", "text/markdown")},
            data={"title": "Mon titre custom"},
        )
    assert response.status_code == 200
    assert response.json()["title"] == "Mon titre custom"


def test_ingest_file_endpoint_unsupported(client_with_dirs):
    response = client_with_dirs.post(
        "/api/ingest/file",
        files={"file": ("script.exe", b"data", "application/octet-stream")},
    )
    assert response.status_code == 415


def test_ingest_file_endpoint_empty_text(client_with_dirs):
    response = client_with_dirs.post(
        "/api/ingest/file",
        files={"file": ("vide.txt", b"   ", "text/plain")},
    )
    assert response.status_code == 422
    assert "extractible" in response.json()["detail"]


def test_ingest_file_endpoint_extract_error(client_with_dirs):
    with patch("app.api.ingest.extract_text", new=AsyncMock(side_effect=ValueError("PDF illisible"))):
        response = client_with_dirs.post(
            "/api/ingest/file",
            files={"file": ("broken.pdf", b"not a pdf", "application/pdf")},
        )
    assert response.status_code == 422
    assert "PDF illisible" in response.json()["detail"]


def test_ingest_marks_dependents_stale(client_with_dirs):
    """Page B a sources: [imports--test-ingestion] et n'est pas mise à jour → stale=True"""
    wiki_tmp = settings.wiki_path
    # Créer la page dépendante
    p = Path(wiki_tmp, "concept", "dependent.md")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "---\ntitle: Dependent\ntype: concept\nsources:\n  - imports--test-ingestion\n---\n\n# Dependent\n",
        encoding="utf-8",
    )
    # Ingest de imports--test-ingestion sans mise à jour de concept--dependent
    with patch("app.services.ingest_service.identify_related_pages", new=AsyncMock(return_value=[])), \
         patch("app.services.ingest_service.compile_multi_page", new=AsyncMock(return_value=MOCK_XML)):
        response = client_with_dirs.post(
            "/api/ingest/text",
            json={"text": "Texte source.", "title": "Test Ingestion", "tags": []},
        )
    assert response.status_code == 200
    data = response.json()
    assert "concept--dependent" in data["stale_marked"]
    # Vérifier que le frontmatter a été mis à jour sur disque
    page = load_page(Path(wiki_tmp, "concept", "dependent.md"), Path(wiki_tmp))
    assert page.stale is True


def test_ingest_text_truncates_large_input(client_with_dirs):
    """Un texte dépassant max_text_chars doit être tronqué avant envoi au LLM."""
    from app.core import config_store
    captured = {}

    async def fake_compile(text, *args, **kwargs):
        captured["text"] = text
        return MOCK_XML

    with patch("app.services.ingest_service.identify_related_pages", new=AsyncMock(return_value=[])), \
         patch("app.services.ingest_service.compile_multi_page", new=AsyncMock(side_effect=fake_compile)):
        client_with_dirs.post(
            "/api/ingest/text",
            json={"text": "A" * 40_000, "title": "Test", "tags": []},
        )
    assert len(captured["text"]) == 30000


def test_ingest_file_ollama_timeout_returns_504(client_with_dirs):
    """Un timeout Ollama doit retourner 504, pas 500."""
    with patch("app.services.ingest_service.identify_related_pages", new=AsyncMock(return_value=[])), \
         patch("app.services.ingest_service.compile_multi_page",
               new=AsyncMock(side_effect=httpx.ReadTimeout("timeout"))):
        response = client_with_dirs.post(
            "/api/ingest/file",
            files={"file": ("doc.txt", b"Contenu.", "text/plain")},
        )
    assert response.status_code == 504
    assert "Ollama" in response.json()["detail"]


def test_ingest_clears_stale_on_updated(client_with_dirs):
    """Page mis à jour par le LLM → stale doit être effacé"""
    wiki_tmp = settings.wiki_path
    # Créer concept--groove déjà stale
    p = Path(wiki_tmp, "concept", "groove.md")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "---\ntitle: Groove\ntype: concept\nstale: true\n---\n\n# Groove\n",
        encoding="utf-8",
    )
    # Ingest qui met à jour concept--groove
    xml_updates_groove = (
        f'<page slug="imports--test-ingestion">{MOCK_MARKDOWN}</page>\n'
        f'<page slug="concept--groove">{CONCEPT_MARKDOWN}</page>'
    )
    with patch("app.services.ingest_service.identify_related_pages", new=AsyncMock(return_value=[])), \
         patch("app.services.ingest_service.compile_multi_page", new=AsyncMock(return_value=xml_updates_groove)):
        response = client_with_dirs.post(
            "/api/ingest/text",
            json={"text": "Groove tickets.", "title": "Test Ingestion", "tags": []},
        )
    assert response.status_code == 200
    # concept--groove a été mis à jour → stale doit être False
    page = load_page(Path(wiki_tmp, "concept", "groove.md"), Path(wiki_tmp))
    assert page.stale is False
