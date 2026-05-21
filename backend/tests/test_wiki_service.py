import pytest
from pathlib import Path
import tempfile
import frontmatter as fm
from app.storage.wiki import load_page, list_pages, get_page


@pytest.fixture
def wiki_dir():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = Path(tmp)
        concepts = wiki / "concepts"
        concepts.mkdir()
        page = concepts / "test-page.md"
        post = fm.Post(
            "## Contenu\n\nTexte de test.",
            title="Page Test",
            type="concept",
            status="draft",
            confidence="high",
            tags=["test"],
            sources=[],
            updated_at="2026-05-12",
        )
        page.write_text(fm.dumps(post))
        yield wiki


def test_load_page(wiki_dir):
    file_path = wiki_dir / "concepts" / "test-page.md"
    page = load_page(file_path, wiki_dir)
    assert page.title == "Page Test"
    assert page.slug == "concepts--test-page"
    assert page.type == "concept"
    assert "Texte de test." in page.content


def test_list_pages(wiki_dir):
    pages = list_pages(wiki_dir)
    assert len(pages) == 1
    assert pages[0].title == "Page Test"


def test_get_page_found(wiki_dir):
    page = get_page("concepts--test-page", wiki_dir)
    assert page is not None
    assert page.title == "Page Test"


def test_get_page_not_found(wiki_dir):
    page = get_page("nonexistent", wiki_dir)
    assert page is None


def test_list_pages_skips_invalid_type(wiki_dir):
    """list_pages doit ignorer les pages dont le type n'est pas dans le Literal autorisé."""
    bad = wiki_dir / "bad-type.md"
    bad.write_text("---\ntitle: Bad\ntype: source\nstatus: draft\n---\nContenu.")
    pages = list_pages(wiki_dir)
    slugs = [p.slug for p in pages]
    assert "bad-type" not in slugs
    assert len(pages) == 1  # seule la page valide du fixture
