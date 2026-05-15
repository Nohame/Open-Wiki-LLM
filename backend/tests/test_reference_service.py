import tempfile
from pathlib import Path
import pytest
from app.core.config import settings


@pytest.fixture
def wiki_env(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(settings, "wiki_path", str(tmp_path / "wiki"))
    monkeypatch.setattr(settings, "data_path", str(data_dir))
    Path(settings.wiki_path).mkdir(parents=True, exist_ok=True)
    # Initialiser la DB pour créer les tables
    from app.storage.search import SearchIndex
    SearchIndex(data_dir / "openwikillm.db")
    return tmp_path


def _write_page(wiki_path: str, slug: str, sources: list[str]) -> None:
    parts = slug.split("--", 1)
    if len(parts) == 2:
        folder, name = parts
        p = Path(wiki_path) / folder / f"{name}.md"
    else:
        p = Path(wiki_path) / f"{slug}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    sources_yaml = "\n".join(f"  - {s}" for s in sources)
    p.write_text(
        f"---\ntitle: Test\nsources:\n{sources_yaml}\n---\n\n# Test\n",
        encoding="utf-8",
    )


def test_rebuild_references_empty_wiki(wiki_env):
    from app.services.reference_service import rebuild_references, get_references
    rebuild_references()
    result = get_references("concept--foo")
    assert result == {"references": [], "referenced_by": []}


def test_rebuild_references_single_page(wiki_env):
    _write_page(settings.wiki_path, "concept--groove", ["imports--ticket-doc"])
    from app.services.reference_service import rebuild_references, get_references
    rebuild_references()
    result = get_references("concept--groove")
    assert result["references"] == ["imports--ticket-doc"]
    assert result["referenced_by"] == []


def test_rebuild_references_no_sources(wiki_env):
    p = Path(settings.wiki_path) / "concept" / "empty.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("---\ntitle: Empty\n---\n\n# Empty\n", encoding="utf-8")
    from app.services.reference_service import rebuild_references, get_references
    rebuild_references()
    result = get_references("concept--empty")
    assert result["references"] == []


def test_rebuild_references_referenced_by(wiki_env):
    _write_page(settings.wiki_path, "concept--a", ["imports--foo"])
    _write_page(settings.wiki_path, "concept--b", ["imports--foo"])
    from app.services.reference_service import rebuild_references, get_references
    rebuild_references()
    result = get_references("imports--foo")
    assert set(result["referenced_by"]) == {"concept--a", "concept--b"}
    assert result["references"] == []


def test_rebuild_references_skips_meta_files(wiki_env):
    wiki_root = Path(settings.wiki_path)
    (wiki_root / "index.md").write_text("---\ntitle: idx\n---\n", encoding="utf-8")
    (wiki_root / "log.md").write_text("---\ntitle: log\n---\n", encoding="utf-8")
    _write_page(settings.wiki_path, "concept--real", ["imports--src"])
    from app.services.reference_service import rebuild_references, get_references
    rebuild_references()
    assert get_references("index")["references"] == []
    assert get_references("concept--real")["references"] == ["imports--src"]


def test_rebuild_references_malformed_frontmatter(wiki_env, caplog):
    import logging
    p = Path(settings.wiki_path) / "concept" / "broken.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("---\ntitle: [broken yaml\n---\n\n# Broken\n", encoding="utf-8")
    from app.services.reference_service import rebuild_references
    with caplog.at_level(logging.WARNING):
        rebuild_references()  # ne doit pas lever d'exception
    assert True  # juste vérifier que ça ne crash pas


def test_get_references_unknown_slug(wiki_env):
    from app.services.reference_service import rebuild_references, get_references
    rebuild_references()
    result = get_references("does--not-exist")
    assert result == {"references": [], "referenced_by": []}


def test_get_stale_pages_empty(wiki_env):
    _write_page(settings.wiki_path, "concept--fresh", [])
    from app.services.reference_service import rebuild_references, get_stale_pages
    rebuild_references()
    assert get_stale_pages() == []


def test_get_stale_pages_with_stale(wiki_env):
    p = Path(settings.wiki_path) / "concept" / "old.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("---\ntitle: Old\nstale: true\n---\n\n# Old\n", encoding="utf-8")
    _write_page(settings.wiki_path, "concept--fresh", [])
    from app.services.reference_service import get_stale_pages
    stale = get_stale_pages()
    assert "concept--old" in stale
    assert "concept--fresh" not in stale
