import pytest
import tempfile
from pathlib import Path
from app.storage.search import SearchIndex


@pytest.fixture
def index():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        idx = SearchIndex(db_path)
        idx.index_page(
            slug="concepts--livraison",
            title="Livraison 24h",
            content="Livraison rapide en vingt-quatre heures garantie.",
            tags="livraison transport",
        )
        idx.index_page(
            slug="concepts--retour",
            title="Politique de retour",
            content="Retour possible sous 30 jours.",
            tags="retour client",
        )
        yield idx


def test_search_returns_relevant_result(index):
    results = index.search("livraison", limit=5)
    assert len(results) >= 1
    assert results[0]["slug"] == "concepts--livraison"


def test_search_no_result(index):
    results = index.search("inexistant", limit=5)
    assert results == []


def test_rebuild_clears_old_data(index):
    index.index_page(
        slug="concepts--livraison",
        title="Livraison 24h",
        content="Contenu mis à jour.",
        tags="livraison",
    )
    results = index.search("livraison", limit=5)
    assert len(results) == 1
