import pytest
import tempfile
from pathlib import Path
import frontmatter as fm
from app.mcp.server import wiki_list_pages, wiki_read_page, wiki_search, wiki_rebuild_index
from app.core.config import settings


@pytest.fixture
def wiki_env(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(settings, "wiki_path", str(tmp_path / "wiki"))
    monkeypatch.setattr(settings, "data_path", str(data_dir))
    Path(settings.wiki_path).mkdir(parents=True, exist_ok=True)
    from app.storage.search import SearchIndex
    SearchIndex(data_dir / "openwikillm.db")
    return tmp_path


def test_wiki_list_stale_empty(wiki_env):
    from app.mcp.server import wiki_list_stale
    result = wiki_list_stale()
    assert result == []


def test_wiki_list_stale_with_stale_page(wiki_env):
    p = Path(settings.wiki_path) / "concept" / "old.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("---\ntitle: Old\nstale: true\n---\n\n# Old\n", encoding="utf-8")
    from app.mcp.server import wiki_list_stale
    result = wiki_list_stale()
    assert any(r["slug"] == "concept--old" for r in result)


def test_wiki_list_references_unknown_slug(wiki_env):
    from app.services.reference_service import rebuild_references
    rebuild_references()
    from app.mcp.server import wiki_list_references
    result = wiki_list_references("concept--unknown")
    assert result == {"references": [], "referenced_by": []}


def test_wiki_list_references_with_source(wiki_env):
    p = Path(settings.wiki_path) / "concept" / "groove.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "---\ntitle: Groove\nsources:\n  - imports--ticket-doc\n---\n\n# Groove\n",
        encoding="utf-8",
    )
    from app.services.reference_service import rebuild_references
    rebuild_references()
    from app.mcp.server import wiki_list_references
    result = wiki_list_references("concept--groove")
    assert "imports--ticket-doc" in result["references"]


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


def test_wiki_guide_empty(wiki_env):
    from app.mcp.server import wiki_guide
    result = wiki_guide()
    assert result == ""


def test_wiki_guide_returns_index_content(wiki_env):
    from app.mcp.server import wiki_guide
    index_path = Path(settings.wiki_path) / "index.md"
    index_path.write_text("# Index du wiki\n\n## concept\n", encoding="utf-8")
    result = wiki_guide()
    assert "# Index du wiki" in result


def test_wiki_write_creates_new_page(wiki_env):
    from app.mcp.server import wiki_write
    result = wiki_write(
        slug="imports--test-write",
        title="Test Write",
        content="## Résumé\n\nContenu créé par agent.",
        type="concept",
        status="draft",
        tags=["test"],
        confidence="medium",
    )
    assert result == {"slug": "imports--test-write", "written": True}
    page_path = Path(settings.wiki_path) / "imports" / "test-write.md"
    assert page_path.exists()
    post = fm.load(str(page_path))
    assert post.metadata["title"] == "Test Write"
    assert post.metadata["status"] == "draft"
    assert post.metadata["tags"] == ["test"]
    assert "Contenu créé par agent" in post.content


def test_wiki_write_updates_existing_page(wiki_env):
    existing = Path(settings.wiki_path) / "imports"
    existing.mkdir(parents=True, exist_ok=True)
    (existing / "existing.md").write_text(
        "---\ntitle: Ancien Titre\nstatus: draft\n---\n\n# Ancien\n",
        encoding="utf-8",
    )
    from app.mcp.server import wiki_write
    result = wiki_write(
        slug="imports--existing",
        title="Nouveau Titre",
        content="## Résumé\n\nContenu mis à jour.",
    )
    assert result["written"] is True
    post = fm.load(str(existing / "existing.md"))
    assert post.metadata["title"] == "Nouveau Titre"
    assert "mis à jour" in post.content
