import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

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
