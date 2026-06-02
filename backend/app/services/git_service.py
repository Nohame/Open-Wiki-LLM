import logging
import subprocess
from pathlib import Path
from ..core.config import settings
from ..core import config_store

logger = logging.getLogger(__name__)


class GitNotAvailableError(Exception):
    pass


def _wiki_path() -> Path:
    return Path(settings.wiki_path)


def _run(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["git"] + args,
            cwd=str(_wiki_path()),
            capture_output=True,
            text=True,
            check=check,
        )
    except FileNotFoundError:
        raise GitNotAvailableError("git n'est pas installé ou introuvable dans PATH")


def _is_enabled() -> bool:
    return config_store.load().git.enabled


def is_initialized() -> bool:
    return (_wiki_path() / ".git").is_dir()


def init_repo() -> None:
    _run(["init"])
    _run(["config", "user.email", "wiki@openwikillm.local"], check=False)
    _run(["config", "user.name", "OpenWikiLLM"], check=False)
    gitignore = _wiki_path() / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("*.pyc\n__pycache__/\n", encoding="utf-8")
    _run(["add", "-A"])
    result = _run(["commit", "-m", "chore(wiki): init", "--allow-empty"], check=False)
    if result.returncode != 0 and "nothing to commit" not in (result.stdout + result.stderr):
        logger.warning("git init commit warning: %s", result.stderr)


def _commit_and_maybe_push(msg: str) -> str | None:
    result = _run(["commit", "-m", msg, "--allow-empty"], check=False)
    if result.returncode != 0:
        logger.warning("git commit failed: %s", result.stderr)
        return None
    hash_result = _run(["rev-parse", "--short", "HEAD"])
    commit_hash = hash_result.stdout.strip()
    cfg = config_store.load()
    if cfg.git.auto_push and cfg.git.remote_url:
        push()
    return commit_hash


def commit_ingest(source: str, written: list[str], deleted: list[str]) -> str | None:
    if not _is_enabled():
        return None
    if not is_initialized():
        logger.warning("git commit_ingest: repo non initialisé, skip")
        return None
    try:
        _run(["add", "-A"])
        parts = []
        if written:
            n = len(written)
            parts.append(f"{n} page{'s' if n > 1 else ''} créée{'s' if n > 1 else ''}")
        if deleted:
            n = len(deleted)
            parts.append(f"{n} supprimée{'s' if n > 1 else ''}")
        detail = ", ".join(parts) if parts else "aucun changement"
        msg = f"feat(wiki): ingest {source} — {detail}"
        return _commit_and_maybe_push(msg)
    except GitNotAvailableError as e:
        logger.warning("git non disponible: %s", e)
        return None


def commit_edit(slug: str, action: str) -> str | None:
    if not _is_enabled():
        return None
    if not is_initialized():
        logger.warning("git commit_edit: repo non initialisé, skip")
        return None
    try:
        _run(["add", "-A"])
        msg = f"{action}(wiki): {slug}"
        return _commit_and_maybe_push(msg)
    except GitNotAvailableError as e:
        logger.warning("git non disponible: %s", e)
        return None


def push() -> None:
    cfg = config_store.load()
    if not cfg.git.remote_url:
        logger.warning("git push: remote_url non configuré, skip")
        return
    try:
        result = _run(
            ["push", cfg.git.remote_url, cfg.git.branch],
            check=False,
        )
        if result.returncode != 0:
            logger.warning("git push failed: %s", result.stderr)
    except GitNotAvailableError as e:
        logger.warning("git non disponible: %s", e)


def get_status() -> dict:
    initialized = is_initialized()
    enabled = _is_enabled()
    if not initialized:
        return {"enabled": enabled, "initialized": False, "last_commit": None, "dirty_files": 0}
    try:
        log_result = _run(["log", "-1", "--format=%h %s %ai"], check=False)
        last_commit = log_result.stdout.strip() or None
        status_result = _run(["status", "--porcelain"], check=False)
        dirty = len([ln for ln in status_result.stdout.splitlines() if ln.strip()])
        return {"enabled": enabled, "initialized": True, "last_commit": last_commit, "dirty_files": dirty}
    except GitNotAvailableError:
        return {"enabled": enabled, "initialized": False, "last_commit": None, "dirty_files": 0}


def get_log(limit: int = 10) -> list[dict]:
    if not is_initialized():
        return []
    try:
        result = _run(["log", f"-{limit}", "--format=%h|%s|%ai"], check=False)
        entries = []
        for line in result.stdout.splitlines():
            parts = line.split("|", 2)
            if len(parts) == 3:
                entries.append({"hash": parts[0], "message": parts[1], "date": parts[2]})
        return entries
    except GitNotAvailableError:
        return []
