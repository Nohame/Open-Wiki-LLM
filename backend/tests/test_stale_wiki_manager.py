from pathlib import Path
import pytest
from app.core.config import settings


@pytest.fixture
def wiki_env(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "wiki_path", str(tmp_path))
    return tmp_path


def _write_concept(wiki_path: Path, name: str, stale: bool | None = None) -> Path:
    p = wiki_path / "concept" / f"{name}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    stale_line = f"stale: {str(stale).lower()}\n" if stale is not None else ""
    p.write_text(
        f"---\ntitle: {name.capitalize()}\ntype: concept\n{stale_line}---\n\n# {name}\n",
        encoding="utf-8",
    )
    return p


def test_set_stale_true(wiki_env):
    _write_concept(wiki_env, "groove")
    from app.services.wiki_manager import set_stale
    set_stale("concept--groove", True)
    from app.storage.wiki import load_page
    page = load_page(wiki_env / "concept" / "groove.md", wiki_env)
    assert page.stale is True


def test_set_stale_false(wiki_env):
    _write_concept(wiki_env, "groove", stale=True)
    from app.services.wiki_manager import set_stale
    set_stale("concept--groove", False)
    from app.storage.wiki import load_page
    page = load_page(wiki_env / "concept" / "groove.md", wiki_env)
    assert page.stale is False


def test_set_stale_nonexistent_slug(wiki_env):
    from app.services.wiki_manager import set_stale
    set_stale("concept--does-not-exist", True)  # ne doit pas lever d'exception


def test_load_page_stale_default_false(wiki_env):
    _write_concept(wiki_env, "fresh")
    from app.storage.wiki import load_page
    page = load_page(wiki_env / "concept" / "fresh.md", wiki_env)
    assert page.stale is False


def test_load_page_stale_true(wiki_env):
    _write_concept(wiki_env, "old", stale=True)
    from app.storage.wiki import load_page
    page = load_page(wiki_env / "concept" / "old.md", wiki_env)
    assert page.stale is True


def test_wikepage_stale_field_in_model():
    from app.models.page import WikiPage
    page = WikiPage(slug="concept--test", title="Test", content="")
    assert page.stale is False
    page2 = WikiPage(slug="concept--test", title="Test", content="", stale=True)
    assert page2.stale is True


def test_set_stale_malformed_frontmatter(wiki_env, caplog):
    import logging
    p = wiki_env / "concept" / "broken.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("---\ntitle: [broken yaml\n---\n\n# Broken\n", encoding="utf-8")
    from app.services.wiki_manager import set_stale
    with caplog.at_level(logging.WARNING):
        set_stale("concept--broken", True)  # ne doit pas lever d'exception
    assert any("malformé" in r.message for r in caplog.records)


def test_set_deprecated_marks_status(tmp_path, monkeypatch):
    import frontmatter as fm
    monkeypatch.setattr(settings, "wiki_path", str(tmp_path))
    p = tmp_path / "concept" / "old.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("---\ntitle: Old\nstatus: draft\n---\n\n# Old\n", encoding="utf-8")
    from app.services.wiki_manager import set_deprecated
    result = set_deprecated("concept--old")
    assert result is True
    post = fm.load(str(p))
    assert post.metadata["status"] == "deprecated"


def test_set_deprecated_unknown_slug_returns_false(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "wiki_path", str(tmp_path))
    from app.services.wiki_manager import set_deprecated
    result = set_deprecated("concept--unknown")
    assert result is False


def test_set_deprecated_malformed_frontmatter(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "wiki_path", str(tmp_path))
    p = tmp_path / "concept" / "broken.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("---\ntitle: [broken yaml\n---\n\n# Broken\n", encoding="utf-8")
    from app.services.wiki_manager import set_deprecated
    result = set_deprecated("concept--broken")
    assert result is False
