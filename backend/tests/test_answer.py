import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import frontmatter as fm
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings


@pytest.fixture
def client_validated(monkeypatch):
    with tempfile.TemporaryDirectory() as wiki_tmp, \
         tempfile.TemporaryDirectory() as data_tmp:
        wiki = Path(wiki_tmp)
        (wiki / "concepts").mkdir()
        page = wiki / "concepts" / "livraison.md"
        post = fm.Post(
            "Livraison garantie en 24h sur tout le territoire.",
            title="Livraison 24h",
            type="concept",
            status="validated",
            confidence="high",
            tags=["livraison"],
            sources=[],
            updated_at="2026-05-12",
        )
        page.write_text(fm.dumps(post))
        monkeypatch.setattr(settings, "wiki_path", str(wiki))
        monkeypatch.setattr(settings, "data_path", data_tmp)
        monkeypatch.setattr(settings, "api_key", "")
        yield TestClient(app)


def test_strict_mode_no_result_returns_fallback(client_validated):
    response = client_validated.post(
        "/api/answer",
        json={"question": "Quel est le prix ?", "mode": "strict"},
    )
    assert response.status_code == 200
    assert "Je ne trouve pas" in response.json()["answer"]


def test_validated_only_returns_answer(client_validated):
    # Rebuild the search index so the validated page is findable
    client_validated.post("/api/index/rebuild")
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value="Livraison en 24h.")
    with patch(
        "app.services.answer_service.llm_service.get_provider",
        return_value=mock_provider,
    ):
        response = client_validated.post(
            "/api/answer",
            json={"question": "délai livraison", "mode": "validated_only"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] != "Je ne trouve pas cette information dans le wiki validé."
