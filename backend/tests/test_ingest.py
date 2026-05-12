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


@pytest.fixture
def client_with_dirs(monkeypatch):
    with tempfile.TemporaryDirectory() as wiki_tmp, \
         tempfile.TemporaryDirectory() as raw_tmp:
        monkeypatch.setattr(settings, "wiki_path", wiki_tmp)
        monkeypatch.setattr(settings, "raw_path", raw_tmp)
        monkeypatch.setattr(settings, "api_key", "")
        yield TestClient(app)


def test_ingest_text_creates_files(client_with_dirs):
    with patch(
        "app.services.ingest_service.compile_to_markdown",
        new=AsyncMock(return_value=MOCK_MARKDOWN),
    ):
        response = client_with_dirs.post(
            "/api/ingest/text",
            json={"text": "Texte source brut.", "title": "Test Ingestion", "tags": ["test"]},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "imports--test-ingestion"
    assert Path(data["raw_path"]).exists()
    assert Path(data["wiki_path"]).exists()


def test_ingest_text_without_title(client_with_dirs):
    with patch(
        "app.services.ingest_service.compile_to_markdown",
        new=AsyncMock(return_value=MOCK_MARKDOWN),
    ):
        response = client_with_dirs.post(
            "/api/ingest/text",
            json={"text": "Texte sans titre."},
        )
    assert response.status_code == 200
