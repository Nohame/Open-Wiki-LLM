import pytest
from pathlib import Path


def test_parse_xml_updates_single():
    from app.services.wiki_manager import parse_xml_updates
    xml = '<page slug="imports--foo">Contenu foo</page>'
    result = parse_xml_updates(xml)
    assert result == {"imports--foo": "Contenu foo"}


def test_parse_xml_updates_multiple():
    from app.services.wiki_manager import parse_xml_updates
    xml = (
        '<page slug="imports--foo">Contenu foo</page>\n'
        '<page slug="imports--bar">Contenu bar</page>\n'
        '<page slug="concept--planning">Contenu planning</page>'
    )
    result = parse_xml_updates(xml)
    assert len(result) == 3
    assert "imports--foo" in result
    assert "imports--bar" in result
    assert "concept--planning" in result


def test_parse_xml_updates_malformed():
    from app.services.wiki_manager import parse_xml_updates
    with pytest.raises(ValueError, match="Aucune balise"):
        parse_xml_updates("pas de balise ici")


def test_apply_updates_creates_dirs(tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "wiki_path", str(tmp_path))
    from app.services.wiki_manager import apply_updates

    written = apply_updates({"imports--foo": "Contenu de foo"})

    assert written == ["imports--foo"]
    assert (tmp_path / "imports" / "foo.md").exists()
    assert (tmp_path / "imports" / "foo.md").read_text() == "Contenu de foo"


def test_load_index_absent(tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "wiki_path", str(tmp_path))
    from app.services.wiki_manager import load_index
    assert load_index() == ""


def test_load_index_present(tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "wiki_path", str(tmp_path))
    (tmp_path / "index.md").write_text("# Index")
    from app.services.wiki_manager import load_index
    assert load_index() == "# Index"


def test_load_pages_existing(tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "wiki_path", str(tmp_path))
    (tmp_path / "imports").mkdir()
    (tmp_path / "imports" / "foo.md").write_text("Contenu foo")
    from app.services.wiki_manager import load_pages
    result = load_pages(["imports--foo"])
    assert result == {"imports--foo": "Contenu foo"}


def test_load_pages_missing_ignored(tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "wiki_path", str(tmp_path))
    from app.services.wiki_manager import load_pages
    assert load_pages(["imports--inexistant"]) == {}


def test_rebuild_index_file(tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "wiki_path", str(tmp_path))
    (tmp_path / "imports").mkdir()
    (tmp_path / "imports" / "page1.md").write_text(
        "---\ntitle: Page Un\n---\n\n# Page Un\n\n## Résumé\n\nDescription de la page un.\n"
    )
    (tmp_path / "imports" / "page2.md").write_text(
        "---\ntitle: Page Deux\n---\n\n# Page Deux\n\n## Résumé\n\nDescription de la page deux.\n"
    )
    from app.services.wiki_manager import rebuild_index_file
    rebuild_index_file()

    index = (tmp_path / "index.md").read_text()
    assert "imports--page1" in index
    assert "imports--page2" in index


def test_append_log_creates_file(tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "wiki_path", str(tmp_path))
    from app.services.wiki_manager import append_log

    append_log("## [2026-05-13] ingest | foo\n- Pages créées : imports--foo\n")

    log_path = tmp_path / "log.md"
    assert log_path.exists()
    assert "ingest | foo" in log_path.read_text()


def test_append_log_prepends(tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "wiki_path", str(tmp_path))
    from app.services.wiki_manager import append_log

    append_log("## [2026-05-13] ingest | premier\n")
    append_log("## [2026-05-14] ingest | deuxieme\n")

    content = (tmp_path / "log.md").read_text()
    assert content.index("deuxieme") < content.index("premier")
