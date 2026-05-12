import pytest
import tempfile
from pathlib import Path
import frontmatter as fm
from app.mcp.server import wiki_list_pages, wiki_read_page, wiki_search, wiki_rebuild_index
from app.core.config import settings


@pytest.fixture(autouse=True)
def wiki_and_data(monkeypatch):
    with tempfile.TemporaryDirectory() as wiki_tmp, \
         tempfile.TemporaryDirectory() as data_tmp:
        wiki = Path(wiki_tmp)
        (wiki / "concepts").mkdir()
        page = wiki / "concepts" / "test.md"
        post = fm.Post(
            "Contenu de test pour la recherche.",
            title="Page MCP Test",
            type="concept",
            status="validated",
            confidence="high",
            tags=["mcp", "test"],
            sources=[],
            updated_at="2026-05-12",
        )
        page.write_text(fm.dumps(post))
        monkeypatch.setattr(settings, "wiki_path", str(wiki))
        monkeypatch.setattr(settings, "data_path", data_tmp)
        yield


def test_wiki_list_pages():
    pages = wiki_list_pages()
    assert len(pages) == 1
    assert pages[0]["title"] == "Page MCP Test"
    assert "content" not in pages[0]


def test_wiki_read_page_found():
    page = wiki_read_page("concepts--test")
    assert page is not None
    assert page["title"] == "Page MCP Test"
    assert "Contenu de test" in page["content"]


def test_wiki_read_page_not_found():
    result = wiki_read_page("inexistant")
    assert result is None


def test_wiki_rebuild_and_search():
    wiki_rebuild_index()
    results = wiki_search("test")
    assert len(results) >= 1
    assert results[0]["slug"] == "concepts--test"
