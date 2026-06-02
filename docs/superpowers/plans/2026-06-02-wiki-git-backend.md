# Wiki Git Backend — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendre le dossier `wiki/` un dépôt git indépendant et optionnel, avec commit automatique par ingestion et par édition manuelle, et push configurable vers un remote.

**Architecture:** Un service `git_service.py` isolé orchestre toutes les opérations git via `subprocess`. `ingest_service.py` et `api/pages.py` l'appellent après leurs opérations d'écriture existantes. Un router `api/git.py` expose init/status/push/log. La fonctionnalité est pilotée par `config.git.enabled` dans `data/config.json`.

**Tech Stack:** Python stdlib (`subprocess`, `pathlib`), FastAPI, Pydantic, pytest + monkeypatch, git CLI

**Spec:** `docs/superpowers/specs/2026-06-02-wiki-git-backend-design.md`

---

## File Map

| Fichier | Action | Rôle |
|---------|--------|------|
| `backend/app/models/settings.py` | Modifier | Ajouter `GitSettings` et le champ `git` dans `AppSettings` |
| `backend/app/services/git_service.py` | Créer | Toute la logique git : init, commit, push, status, log |
| `backend/app/api/git.py` | Créer | Endpoints REST : `/api/git/init`, `/status`, `/push`, `/log` |
| `backend/app/main.py` | Modifier | Enregistrer le router git |
| `backend/app/services/ingest_service.py` | Modifier | Appeler `git_service.commit_ingest()` après `append_log` |
| `backend/app/api/pages.py` | Modifier | Appeler `git_service.commit_edit()` après `delete_page` |
| `data/config.json` | Modifier | Ajouter section `git` avec valeurs par défaut |
| `backend/tests/test_git_service.py` | Créer | Tests unitaires de `git_service.py` |
| `backend/tests/test_api_git.py` | Créer | Tests des endpoints `/api/git/...` |

---

### Task 1: GitSettings model + config par défaut

**Files:**
- Modify: `backend/app/models/settings.py`
- Modify: `data/config.json`
- Test: `backend/tests/test_api_settings.py`

- [ ] **Step 1: Écrire les tests échouants**

Ajouter à la fin de `backend/tests/test_api_settings.py` :

```python
def test_git_settings_defaults():
    from app.models.settings import AppSettings
    s = AppSettings()
    assert s.git.enabled is False
    assert s.git.auto_push is False
    assert s.git.remote_url == ""
    assert s.git.branch == "main"


def test_git_settings_persisted(tmp_path, monkeypatch):
    from app.core.config import settings as core_settings
    monkeypatch.setattr(core_settings, "data_path", str(tmp_path))
    from app.core import config_store
    cfg = config_store.load()
    cfg.git.enabled = True
    cfg.git.branch = "wiki"
    config_store.save(cfg)
    reloaded = config_store.load()
    assert reloaded.git.enabled is True
    assert reloaded.git.branch == "wiki"
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
cd backend && python -m pytest tests/test_api_settings.py::test_git_settings_defaults tests/test_api_settings.py::test_git_settings_persisted -v
```

Résultat attendu : `FAILED` — `AttributeError: 'AppSettings' object has no attribute 'git'`

- [ ] **Step 3: Ajouter `GitSettings` dans `backend/app/models/settings.py`**

Ajouter après la classe `ConnectorsConfig` :

```python
class GitSettings(BaseModel):
    enabled: bool = False
    auto_push: bool = False
    remote_url: str = ""
    branch: str = "main"
```

Modifier `AppSettings` :

```python
class AppSettings(BaseModel):
    llm: LLMConfig = LLMConfig()
    ingest: IngestConfig = IngestConfig()
    connectors: ConnectorsConfig = ConnectorsConfig()
    git: GitSettings = GitSettings()
```

- [ ] **Step 4: Vérifier que les tests passent**

```bash
cd backend && python -m pytest tests/test_api_settings.py::test_git_settings_defaults tests/test_api_settings.py::test_git_settings_persisted -v
```

Résultat attendu : `PASSED`

- [ ] **Step 5: Ajouter la section git à `data/config.json`**

Dans `data/config.json`, ajouter après le bloc `"connectors"` (avant la dernière accolade `}`) :

```json
  "git": {
    "enabled": false,
    "auto_push": false,
    "remote_url": "",
    "branch": "main"
  }
```

- [ ] **Step 6: Vérifier que la suite de tests settings passe toujours**

```bash
cd backend && python -m pytest tests/test_api_settings.py -v
```

Résultat attendu : tous `PASSED`

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/settings.py backend/tests/test_api_settings.py data/config.json
git commit -m "feat(git): add GitSettings model and config defaults"
```

---

### Task 2: git_service.py

**Files:**
- Create: `backend/app/services/git_service.py`
- Create: `backend/tests/test_git_service.py`

- [ ] **Step 1: Créer le fichier de tests**

Créer `backend/tests/test_git_service.py` :

```python
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
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
cd backend && python -m pytest tests/test_git_service.py -v
```

Résultat attendu : `ERROR` — `ModuleNotFoundError: No module named 'app.services.git_service'`

- [ ] **Step 3: Créer `backend/app/services/git_service.py`**

```python
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
    if result.returncode != 0 and "nothing to commit" not in result.stdout:
        logger.warning("git init commit warning: %s", result.stderr)


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
        result = _run(["commit", "-m", msg, "--allow-empty"], check=False)
        if result.returncode != 0:
            logger.warning("git commit_ingest failed: %s", result.stderr)
            return None
        hash_result = _run(["rev-parse", "--short", "HEAD"])
        commit_hash = hash_result.stdout.strip()
        cfg = config_store.load()
        if cfg.git.auto_push and cfg.git.remote_url:
            push()
        return commit_hash
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
        result = _run(["commit", "-m", msg, "--allow-empty"], check=False)
        if result.returncode != 0:
            logger.warning("git commit_edit failed: %s", result.stderr)
            return None
        hash_result = _run(["rev-parse", "--short", "HEAD"])
        commit_hash = hash_result.stdout.strip()
        cfg = config_store.load()
        if cfg.git.auto_push and cfg.git.remote_url:
            push()
        return commit_hash
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
```

- [ ] **Step 4: Vérifier que les tests passent**

```bash
cd backend && python -m pytest tests/test_git_service.py -v
```

Résultat attendu : tous `PASSED`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/git_service.py backend/tests/test_git_service.py
git commit -m "feat(git): implement git_service with subprocess"
```

---

### Task 3: api/git.py + enregistrement dans main.py

**Files:**
- Create: `backend/app/api/git.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_api_git.py`

- [ ] **Step 1: Créer le fichier de tests**

Créer `backend/tests/test_api_git.py` :

```python
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "")
    return TestClient(app)


def test_git_status_not_initialized(client):
    with patch("app.api.git.git_service.get_status") as mock:
        mock.return_value = {
            "enabled": False,
            "initialized": False,
            "last_commit": None,
            "dirty_files": 0,
        }
        response = client.get("/api/git/status")
    assert response.status_code == 200
    data = response.json()
    assert data["initialized"] is False
    assert data["enabled"] is False


def test_git_status_initialized(client):
    with patch("app.api.git.git_service.get_status") as mock:
        mock.return_value = {
            "enabled": True,
            "initialized": True,
            "last_commit": "abc1234 chore(wiki): init 2026-06-02",
            "dirty_files": 0,
        }
        response = client.get("/api/git/status")
    assert response.status_code == 200
    assert response.json()["initialized"] is True
    assert response.json()["last_commit"] is not None


def test_git_init_when_not_initialized(client):
    with patch("app.api.git.git_service.is_initialized", return_value=False), \
         patch("app.api.git.git_service.init_repo") as mock_init:
        response = client.post("/api/git/init")
    assert response.status_code == 200
    assert response.json()["status"] == "initialized"
    mock_init.assert_called_once()


def test_git_init_already_initialized(client):
    with patch("app.api.git.git_service.is_initialized", return_value=True), \
         patch("app.api.git.git_service.init_repo") as mock_init:
        response = client.post("/api/git/init")
    assert response.status_code == 200
    assert response.json()["status"] == "already_initialized"
    mock_init.assert_not_called()


def test_git_push(client):
    with patch("app.api.git.git_service.push") as mock_push:
        response = client.post("/api/git/push")
    assert response.status_code == 200
    assert response.json()["status"] == "push_triggered"
    mock_push.assert_called_once()


def test_git_log(client):
    with patch("app.api.git.git_service.get_log") as mock_log:
        mock_log.return_value = [
            {"hash": "abc1234", "message": "chore(wiki): init", "date": "2026-06-02 10:00:00 +0200"}
        ]
        response = client.get("/api/git/log")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["hash"] == "abc1234"
    assert data[0]["message"] == "chore(wiki): init"


def test_git_log_empty(client):
    with patch("app.api.git.git_service.get_log", return_value=[]):
        response = client.get("/api/git/log")
    assert response.status_code == 200
    assert response.json() == []


def test_git_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "secret")
    client = TestClient(app)
    response = client.get("/api/git/status")
    assert response.status_code == 401
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
cd backend && python -m pytest tests/test_api_git.py -v
```

Résultat attendu : `FAILED` avec `404 Not Found` pour tous les endpoints git

- [ ] **Step 3: Créer `backend/app/api/git.py`**

```python
from fastapi import APIRouter, Depends
from ..services import git_service
from ..core.auth import verify_api_key

router = APIRouter(prefix="/api/git", dependencies=[Depends(verify_api_key)])


@router.get("/status")
def git_status() -> dict:
    return git_service.get_status()


@router.post("/init")
def git_init() -> dict:
    if git_service.is_initialized():
        return {"status": "already_initialized"}
    git_service.init_repo()
    return {"status": "initialized"}


@router.post("/push")
def git_push() -> dict:
    git_service.push()
    return {"status": "push_triggered"}


@router.get("/log")
def git_log(limit: int = 10) -> list[dict]:
    return git_service.get_log(limit=limit)
```

- [ ] **Step 4: Enregistrer le router dans `backend/app/main.py`**

Ajouter l'import après les imports existants :

```python
from .api.git import router as git_router
```

Ajouter dans la liste `include_router` :

```python
app.include_router(git_router)
```

- [ ] **Step 5: Vérifier que les tests passent**

```bash
cd backend && python -m pytest tests/test_api_git.py -v
```

Résultat attendu : tous `PASSED`

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/git.py backend/app/main.py backend/tests/test_api_git.py
git commit -m "feat(git): add /api/git endpoints (init, status, push, log)"
```

---

### Task 4: Intégration dans ingest_service.py

**Files:**
- Modify: `backend/app/services/ingest_service.py`
- Test: `backend/tests/test_ingest.py`

- [ ] **Step 1: Écrire le test échouant**

Ajouter à la fin de `backend/tests/test_ingest.py` :

```python
def test_ingest_calls_git_commit(client_with_dirs):
    from unittest.mock import patch
    with patch("app.services.ingest_service.identify_related_pages", new=AsyncMock(return_value=[])), \
         patch("app.services.ingest_service.compile_multi_page", new=AsyncMock(return_value=MOCK_XML)), \
         patch("app.services.git_service.commit_ingest", return_value="abc1234") as mock_git:
        response = client_with_dirs.post(
            "/api/ingest/text",
            json={"text": "Texte source.", "title": "Test Ingestion", "tags": []},
        )
    assert response.status_code == 200
    mock_git.assert_called_once()
    args = mock_git.call_args[0]
    assert args[0] == "test-ingestion"  # source slug slugifié depuis le titre
    assert "imports--test-ingestion" in args[1]  # written slugs
    assert args[2] == []  # deleted slugs
```

- [ ] **Step 2: Vérifier que le test échoue**

```bash
cd backend && python -m pytest tests/test_ingest.py::test_ingest_calls_git_commit -v
```

Résultat attendu : `FAILED` — `AssertionError: mock_git.assert_called_once()` (not called)

- [ ] **Step 3: Modifier `backend/app/services/ingest_service.py`**

Ajouter l'import en haut du fichier, après les imports existants :

```python
from . import git_service
```

Ajouter après le bloc `wiki_manager.append_log(...)` (juste avant `return {`):

```python
    git_service.commit_ingest(slug, written_slugs, [])
```

Le bloc final de la fonction `ingest_text` doit ressembler à :

```python
    wiki_manager.append_log(
        f"## [{today}] ingest | {slug}\n"
        f"- Source : {new_slug}\n"
        f"- Concepts : {', '.join(concepts_created) or '—'}\n"
        f"- Entités : {', '.join(entities_created) or '—'}\n"
        f"- Tags : {', '.join(tags) or '—'}\n"
        f"- Durée : {duration_s}s\n"
    )

    git_service.commit_ingest(slug, written_slugs, [])

    return {
        "slug": new_slug,
        ...
    }
```

- [ ] **Step 4: Vérifier que le test passe**

```bash
cd backend && python -m pytest tests/test_ingest.py::test_ingest_calls_git_commit -v
```

Résultat attendu : `PASSED`

- [ ] **Step 5: Vérifier que les tests existants passent toujours**

```bash
cd backend && python -m pytest tests/test_ingest.py -v
```

Résultat attendu : tous `PASSED` (git.enabled=False par défaut → commit_ingest est un no-op dans les autres tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/ingest_service.py backend/tests/test_ingest.py
git commit -m "feat(git): call commit_ingest after text ingestion"
```

---

### Task 5: Intégration dans api/pages.py

**Files:**
- Modify: `backend/app/api/pages.py`
- Test: `backend/tests/test_api_pages.py`

- [ ] **Step 1: Écrire le test échouant**

Ajouter à la fin de `backend/tests/test_api_pages.py` :

```python
def test_delete_page_calls_git_commit(monkeypatch):
    import tempfile
    from unittest.mock import patch
    import frontmatter as fm
    with tempfile.TemporaryDirectory() as tmp:
        wiki = Path(tmp)
        (wiki / "concepts").mkdir()
        page = wiki / "concepts" / "livraison.md"
        post = fm.Post(
            "## Résumé\n\nLivraison en 24h.",
            title="Livraison 24h",
            type="concept",
            status="validated",
            confidence="high",
            tags=[],
            sources=[],
            updated_at="2026-06-02",
        )
        page.write_text(fm.dumps(post))
        monkeypatch.setattr(settings, "api_key", "")
        monkeypatch.setattr(settings, "wiki_path", str(wiki))
        with patch("app.api.pages.git_service.commit_edit", return_value="abc1234") as mock_git:
            client = TestClient(app)
            response = client.delete("/api/pages/concepts--livraison")
        assert response.status_code == 204
        mock_git.assert_called_once_with("concepts--livraison", "delete")
```

- [ ] **Step 2: Vérifier que le test échoue**

```bash
cd backend && python -m pytest tests/test_api_pages.py::test_delete_page_calls_git_commit -v
```

Résultat attendu : `FAILED` — `AssertionError: mock_git.assert_called_once_with(...)` (not called)

- [ ] **Step 3: Modifier `backend/app/api/pages.py`**

Ajouter l'import en haut :

```python
from ..services import git_service
```

Modifier l'endpoint `delete_page` :

```python
@router.delete("/pages/{slug}", status_code=204)
def delete_page(slug: str) -> Response:
    deleted = wiki_manager.delete_page(slug)
    if not deleted:
        raise HTTPException(status_code=404, detail="Page not found")
    git_service.commit_edit(slug, "delete")
    return Response(status_code=204)
```

- [ ] **Step 4: Vérifier que le test passe**

```bash
cd backend && python -m pytest tests/test_api_pages.py::test_delete_page_calls_git_commit -v
```

Résultat attendu : `PASSED`

- [ ] **Step 5: Vérifier que tous les tests passent**

```bash
cd backend && python -m pytest tests/test_api_pages.py -v
```

Résultat attendu : tous `PASSED`

- [ ] **Step 6: Lancer la suite complète**

```bash
cd backend && python -m pytest --tb=short -q
```

Résultat attendu : tous les tests passent

- [ ] **Step 7: Commit final**

```bash
git add backend/app/api/pages.py backend/tests/test_api_pages.py
git commit -m "feat(git): call commit_edit after page delete"
```
