import subprocess
import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def git_env(monkeypatch):
    """Ensure git author identity is set for all test commits."""
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Test")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "test@test.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Test")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "test@test.com")


@pytest.fixture
def wiki_dir(tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "wiki_path", str(tmp_path))
    monkeypatch.setattr(settings, "data_path", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    return tmp_path


@pytest.fixture
def git_enabled(wiki_dir):
    from app.models.settings import AppSettings, GitSettings
    from app.core import config_store
    config_store.save(AppSettings(git=GitSettings(enabled=True)))
    return wiki_dir


def test_is_initialized_false(wiki_dir):
    from app.services import git_service
    assert git_service.is_initialized() is False


def test_is_initialized_true(wiki_dir):
    subprocess.run(["git", "init", str(wiki_dir)], check=True, capture_output=True)
    from app.services import git_service
    assert git_service.is_initialized() is True


def test_init_repo_creates_git_dir(wiki_dir):
    from app.services import git_service
    git_service.init_repo()
    assert (wiki_dir / ".git").is_dir()


def test_init_repo_creates_gitignore(wiki_dir):
    from app.services import git_service
    git_service.init_repo()
    assert (wiki_dir / ".gitignore").exists()


def test_commit_ingest_no_op_when_disabled(wiki_dir):
    # No config.json in data/ → default AppSettings with git.enabled=False
    from app.services import git_service
    result = git_service.commit_ingest("test-source", ["concept--foo"], [])
    assert result is None


def test_commit_ingest_skip_if_not_initialized(git_enabled):
    # git enabled but repo not initialized
    from app.services import git_service
    result = git_service.commit_ingest("source", ["slug"], [])
    assert result is None


def test_commit_ingest_returns_hash(git_enabled):
    from app.services import git_service
    git_service.init_repo()
    (git_enabled / "concept--foo.md").write_text("# Foo")
    result = git_service.commit_ingest("test-source", ["concept--foo"], [])
    assert result is not None
    assert len(result) > 0


def test_commit_edit_no_op_when_disabled(wiki_dir):
    from app.services import git_service
    result = git_service.commit_edit("concept--bar", "create")
    assert result is None


def test_commit_edit_returns_hash(git_enabled):
    from app.services import git_service
    git_service.init_repo()
    (git_enabled / "concept--bar.md").write_text("# Bar")
    result = git_service.commit_edit("concept--bar", "create")
    assert result is not None


def test_get_status_not_initialized(wiki_dir):
    from app.services import git_service
    status = git_service.get_status()
    assert status["initialized"] is False
    assert status["enabled"] is False


def test_get_status_initialized(git_enabled):
    from app.services import git_service
    git_service.init_repo()
    status = git_service.get_status()
    assert status["initialized"] is True
    assert status["enabled"] is True
    assert status["last_commit"] is not None
    assert isinstance(status["dirty_files"], int)


def test_get_log_empty_when_not_initialized(wiki_dir):
    from app.services import git_service
    assert git_service.get_log() == []


def test_get_log_returns_entries(git_enabled):
    from app.services import git_service
    git_service.init_repo()
    entries = git_service.get_log()
    assert isinstance(entries, list)
    assert len(entries) >= 1
    assert "hash" in entries[0]
    assert "message" in entries[0]
    assert "date" in entries[0]
