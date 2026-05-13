def test_load_or_create_creates_default(tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "wiki_path", str(tmp_path))
    from app.services.schema_service import load_or_create, DEFAULT_SCHEMA

    result = load_or_create()

    assert result == DEFAULT_SCHEMA
    schema_file = tmp_path / "schema.md"
    assert schema_file.exists()
    assert schema_file.read_text(encoding="utf-8") == DEFAULT_SCHEMA


def test_load_or_create_reads_existing(tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "wiki_path", str(tmp_path))
    (tmp_path / "schema.md").write_text("# Custom schema", encoding="utf-8")
    from app.services.schema_service import load_or_create

    result = load_or_create()

    assert result == "# Custom schema"
    assert (tmp_path / "schema.md").read_text(encoding="utf-8") == "# Custom schema"
