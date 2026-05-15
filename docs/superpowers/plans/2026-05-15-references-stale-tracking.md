# References & Stale Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tracker les dépendances entre pages wiki via le champ `sources[]` frontmatter, détecter les pages obsolètes après un re-ingest, et exposer ces informations via API, MCP tools, et badge frontend.

**Architecture:** Table SQLite `page_references` rebuild-able depuis les frontmatters (cache dérivé). Flag `stale: bool` dans le frontmatter markdown (source de vérité). Post-ingest : rebuild graph + mark stale les dépendants non mis à jour + clear stale sur les pages mises à jour.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, python-frontmatter, sqlite3, pytest, Nuxt 3, Vue 3, TypeScript

---

## Fichiers touchés

| Statut | Fichier |
|--------|---------|
| Modifier | `backend/app/storage/search.py` — table `page_references` dans `_init_db` |
| Créer | `backend/app/services/reference_service.py` — rebuild_references, get_references, get_stale_pages |
| Créer | `backend/tests/test_reference_service.py` |
| Modifier | `backend/app/models/page.py` — `stale: bool = False` + `StaleUpdate` |
| Modifier | `backend/app/storage/wiki.py` — lire `stale` dans `load_page` |
| Modifier | `backend/app/services/wiki_manager.py` — `set_stale()` |
| Créer | `backend/tests/test_stale_wiki_manager.py` |
| Créer | `backend/app/models/references.py` — `PageReferences` |
| Créer | `backend/app/api/references.py` — `GET /api/pages/{slug}/references` |
| Modifier | `backend/app/api/pages.py` — `PATCH /api/pages/{slug}/stale` |
| Modifier | `backend/app/main.py` — enregistrer references router |
| Créer | `backend/tests/test_references_endpoint.py` |
| Créer | `backend/tests/test_stale_endpoint.py` |
| Modifier | `backend/app/mcp/server.py` — `wiki_list_stale`, `wiki_list_references` |
| Modifier | `backend/app/services/ingest_service.py` — post-ingest stale logic |
| Modifier | `backend/app/models/ingest.py` — `stale_marked: list[str]` |
| Modifier | `frontend/types/api.ts` — `WikiPage.stale`, `IngestResult.stale_marked`, `PageReferences` |
| Modifier | `frontend/composables/useApi.ts` — méthode `patch<T>()` |
| Modifier | `frontend/pages/wiki/[slug].vue` — badge Obsolète + bouton |

---

## Task 1 : SQLite table + reference_service

**Files:**
- Modify: `backend/app/storage/search.py`
- Create: `backend/app/services/reference_service.py`
- Test: `backend/tests/test_reference_service.py`

- [ ] **Step 1 : Écrire les tests qui échouent**

Créer `backend/tests/test_reference_service.py` :

```python
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
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend && source .venv/bin/activate && pytest tests/test_reference_service.py -v 2>&1 | tail -5
```

Attendu : `ImportError` ou `ModuleNotFoundError` sur `reference_service`

- [ ] **Step 3 : Ajouter la table page_references à SearchIndex._init_db**

Dans `backend/app/storage/search.py`, modifier `_init_db` :

```python
def _init_db(self) -> None:
    with self._connect() as conn:
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS wiki_pages_fts
            USING fts5(slug, title, content, tags)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS page_references (
                page_slug TEXT NOT NULL,
                source_slug TEXT NOT NULL,
                PRIMARY KEY (page_slug, source_slug)
            )
        """)
```

- [ ] **Step 4 : Créer backend/app/services/reference_service.py**

```python
import sqlite3
import logging
from pathlib import Path
import frontmatter as fm
from ..core.config import settings

logger = logging.getLogger(__name__)


def _db_path() -> Path:
    return Path(settings.data_path) / "openwikillm.db"


def _ensure_table() -> None:
    with sqlite3.connect(str(_db_path())) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS page_references (
                page_slug TEXT NOT NULL,
                source_slug TEXT NOT NULL,
                PRIMARY KEY (page_slug, source_slug)
            )
        """)


def _path_to_slug(wiki_path: Path, file_path: Path) -> str:
    return str(file_path.relative_to(wiki_path).with_suffix("")).replace("/", "--")


def rebuild_references() -> None:
    _ensure_table()
    wiki_root = Path(settings.wiki_path)
    rows: list[tuple[str, str]] = []
    for md_file in wiki_root.rglob("*.md"):
        if md_file.name in ("index.md", "log.md", "schema.md"):
            continue
        slug = _path_to_slug(wiki_root, md_file)
        try:
            post = fm.load(str(md_file))
            sources = post.metadata.get("sources") or []
        except Exception:
            logger.warning("Frontmatter malformé — ignoré : %s", md_file)
            continue
        for source_slug in sources:
            rows.append((slug, source_slug))
    with sqlite3.connect(str(_db_path())) as conn:
        conn.execute("DELETE FROM page_references")
        conn.executemany("INSERT OR IGNORE INTO page_references VALUES (?, ?)", rows)


def get_references(slug: str) -> dict:
    _ensure_table()
    with sqlite3.connect(str(_db_path())) as conn:
        references = [
            row[0]
            for row in conn.execute(
                "SELECT source_slug FROM page_references WHERE page_slug = ?", (slug,)
            ).fetchall()
        ]
        referenced_by = [
            row[0]
            for row in conn.execute(
                "SELECT page_slug FROM page_references WHERE source_slug = ?", (slug,)
            ).fetchall()
        ]
    return {"references": references, "referenced_by": referenced_by}


def get_stale_pages() -> list[str]:
    wiki_root = Path(settings.wiki_path)
    stale: list[str] = []
    for md_file in wiki_root.rglob("*.md"):
        if md_file.name in ("index.md", "log.md", "schema.md"):
            continue
        try:
            post = fm.load(str(md_file))
            if post.metadata.get("stale", False):
                stale.append(_path_to_slug(wiki_root, md_file))
        except Exception:
            logger.warning("Frontmatter malformé — ignoré : %s", md_file)
    return stale
```

- [ ] **Step 5 : Vérifier que les tests passent**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend && source .venv/bin/activate && pytest tests/test_reference_service.py -v 2>&1 | tail -15
```

Attendu : `9 passed`

- [ ] **Step 6 : Vérifier la suite complète**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend && source .venv/bin/activate && pytest tests/ -q 2>&1 | tail -3
```

Attendu : `65 passed` (56 + 9)

- [ ] **Step 7 : Commit**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm && git add backend/app/storage/search.py backend/app/services/reference_service.py backend/tests/test_reference_service.py && git commit -m "feat: add page_references SQLite table and reference_service"
```

---

## Task 2 : WikiPage.stale + wiki_storage + wiki_manager.set_stale

**Files:**
- Modify: `backend/app/models/page.py`
- Modify: `backend/app/storage/wiki.py`
- Modify: `backend/app/services/wiki_manager.py`
- Test: `backend/tests/test_stale_wiki_manager.py`

- [ ] **Step 1 : Écrire les tests qui échouent**

Créer `backend/tests/test_stale_wiki_manager.py` :

```python
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
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend && source .venv/bin/activate && pytest tests/test_stale_wiki_manager.py -v 2>&1 | tail -10
```

Attendu : `AttributeError` — `WikiPage` n'a pas de champ `stale`

- [ ] **Step 3 : Ajouter stale + StaleUpdate à models/page.py**

Remplacer le contenu de `backend/app/models/page.py` :

```python
from pydantic import BaseModel
from typing import Literal


class WikiPage(BaseModel):
    slug: str
    title: str
    type: Literal["concept", "project", "procedure", "decision", "note", "entity"] = "note"
    status: Literal["draft", "reviewed", "validated", "deprecated"] = "draft"
    confidence: Literal["low", "medium", "high"] = "medium"
    sources: list[str] = []
    updated_at: str = ""
    tags: list[str] = []
    stale: bool = False
    content: str


class StaleUpdate(BaseModel):
    stale: bool
```

- [ ] **Step 4 : Mettre à jour load_page dans backend/app/storage/wiki.py**

Ajouter `stale=post.metadata.get("stale", False),` dans `load_page` :

```python
def load_page(file_path: Path, wiki_path: Path) -> WikiPage:
    post = frontmatter.load(str(file_path))
    return WikiPage(
        slug=_path_to_slug(wiki_path, file_path),
        title=post.metadata.get("title", file_path.stem),
        type=post.metadata.get("type", "note"),
        status=post.metadata.get("status", "draft"),
        confidence=post.metadata.get("confidence", "medium"),
        sources=post.metadata.get("sources", []),
        updated_at=str(post.metadata.get("updated_at", "")),
        tags=post.metadata.get("tags", []),
        stale=post.metadata.get("stale", False),
        content=post.content,
    )
```

- [ ] **Step 5 : Ajouter set_stale à wiki_manager.py**

Ajouter en haut de `backend/app/services/wiki_manager.py` après les imports existants :

```python
import logging
import frontmatter as fm

logger = logging.getLogger(__name__)
```

Ajouter la fonction `set_stale` à la fin du fichier (avant les fonctions privées `_*`) :

```python
def set_stale(slug: str, stale: bool) -> None:
    path = _slug_to_path(slug)
    if not path.exists():
        logger.warning("set_stale: slug introuvable : %s", slug)
        return
    try:
        post = fm.load(str(path))
        post.metadata["stale"] = stale
        path.write_text(fm.dumps(post), encoding="utf-8")
    except Exception:
        logger.warning("set_stale: frontmatter malformé pour %s", slug)
```

- [ ] **Step 6 : Vérifier que les tests passent**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend && source .venv/bin/activate && pytest tests/test_stale_wiki_manager.py -v 2>&1 | tail -10
```

Attendu : `6 passed`

- [ ] **Step 7 : Vérifier la suite complète**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend && source .venv/bin/activate && pytest tests/ -q 2>&1 | tail -3
```

Attendu : `71 passed`

- [ ] **Step 8 : Commit**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm && git add backend/app/models/page.py backend/app/storage/wiki.py backend/app/services/wiki_manager.py backend/tests/test_stale_wiki_manager.py && git commit -m "feat: add stale field to WikiPage and set_stale to wiki_manager"
```

---

## Task 3 : API endpoints + main.py + tests

**Files:**
- Create: `backend/app/models/references.py`
- Create: `backend/app/api/references.py`
- Modify: `backend/app/api/pages.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_references_endpoint.py`
- Test: `backend/tests/test_stale_endpoint.py`

- [ ] **Step 1 : Écrire les tests qui échouent**

Créer `backend/tests/test_references_endpoint.py` :

```python
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
import pytest


@pytest.fixture
def client_with_dirs(monkeypatch):
    with tempfile.TemporaryDirectory() as wiki_tmp, \
         tempfile.TemporaryDirectory() as raw_tmp, \
         tempfile.TemporaryDirectory() as data_tmp:
        monkeypatch.setattr(settings, "wiki_path", wiki_tmp)
        monkeypatch.setattr(settings, "raw_path", raw_tmp)
        monkeypatch.setattr(settings, "data_path", data_tmp)
        monkeypatch.setattr(settings, "api_key", "")
        yield TestClient(app)


def test_references_endpoint_no_pages(client_with_dirs):
    response = client_with_dirs.get("/api/pages/concept--groove/references")
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "concept--groove"
    assert data["references"] == []
    assert data["referenced_by"] == []


def test_references_endpoint_with_source(client_with_dirs):
    wiki_tmp = settings.wiki_path
    p = Path(wiki_tmp, "concept", "groove.md")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "---\ntitle: Groove\nsources:\n  - imports--ticket-doc\n---\n\n# Groove\n",
        encoding="utf-8",
    )
    from app.services.reference_service import rebuild_references
    rebuild_references()
    response = client_with_dirs.get("/api/pages/concept--groove/references")
    assert response.status_code == 200
    data = response.json()
    assert "imports--ticket-doc" in data["references"]
```

Créer `backend/tests/test_stale_endpoint.py` :

```python
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
import pytest


@pytest.fixture
def client_with_dirs(monkeypatch):
    with tempfile.TemporaryDirectory() as wiki_tmp, \
         tempfile.TemporaryDirectory() as raw_tmp, \
         tempfile.TemporaryDirectory() as data_tmp:
        monkeypatch.setattr(settings, "wiki_path", wiki_tmp)
        monkeypatch.setattr(settings, "raw_path", raw_tmp)
        monkeypatch.setattr(settings, "data_path", data_tmp)
        monkeypatch.setattr(settings, "api_key", "")
        yield TestClient(app)


def _write_page(wiki_path: str, slug: str) -> None:
    parts = slug.split("--", 1)
    p = Path(wiki_path, parts[0], f"{parts[1]}.md")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "---\ntitle: Test\ntype: concept\n---\n\n# Test\n",
        encoding="utf-8",
    )


def test_set_stale_true(client_with_dirs):
    _write_page(settings.wiki_path, "concept--groove")
    response = client_with_dirs.patch(
        "/api/pages/concept--groove/stale", json={"stale": True}
    )
    assert response.status_code == 200
    assert response.json()["stale"] is True


def test_set_stale_false(client_with_dirs):
    _write_page(settings.wiki_path, "concept--groove")
    client_with_dirs.patch("/api/pages/concept--groove/stale", json={"stale": True})
    response = client_with_dirs.patch(
        "/api/pages/concept--groove/stale", json={"stale": False}
    )
    assert response.status_code == 200
    assert response.json()["stale"] is False


def test_set_stale_unknown(client_with_dirs):
    response = client_with_dirs.patch(
        "/api/pages/concept--does-not-exist/stale", json={"stale": True}
    )
    assert response.status_code == 404
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend && source .venv/bin/activate && pytest tests/test_references_endpoint.py tests/test_stale_endpoint.py -v 2>&1 | tail -10
```

Attendu : `404` ou `ImportError` — endpoint inexistant

- [ ] **Step 3 : Créer backend/app/models/references.py**

```python
from pydantic import BaseModel


class PageReferences(BaseModel):
    slug: str
    references: list[str] = []
    referenced_by: list[str] = []
```

- [ ] **Step 4 : Créer backend/app/api/references.py**

```python
from fastapi import APIRouter, Depends
from ..services import reference_service
from ..models.references import PageReferences
from ..core.auth import verify_api_key

router = APIRouter(prefix="/api", dependencies=[Depends(verify_api_key)])


@router.get("/pages/{slug}/references", response_model=PageReferences)
def get_page_references(slug: str) -> PageReferences:
    refs = reference_service.get_references(slug)
    return PageReferences(slug=slug, **refs)
```

- [ ] **Step 5 : Ajouter PATCH /pages/{slug}/stale dans pages.py**

Dans `backend/app/api/pages.py`, ajouter les imports et le nouvel endpoint :

```python
from fastapi import APIRouter, HTTPException, Depends
from ..services.wiki_service import list_pages, get_page
from ..services import wiki_manager
from ..models.page import WikiPage, StaleUpdate
from ..core.auth import verify_api_key

router = APIRouter(prefix="/api", dependencies=[Depends(verify_api_key)])


@router.get("/pages", response_model=list[WikiPage])
def get_pages() -> list[WikiPage]:
    return list_pages()


@router.get("/pages/{slug}", response_model=WikiPage)
def get_page_by_slug(slug: str) -> WikiPage:
    page = get_page(slug)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


@router.patch("/pages/{slug}/stale", response_model=WikiPage)
def update_stale(slug: str, body: StaleUpdate) -> WikiPage:
    page = get_page(slug)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    wiki_manager.set_stale(slug, body.stale)
    return get_page(slug)
```

- [ ] **Step 6 : Enregistrer references router dans main.py**

Dans `backend/app/main.py`, ajouter après `from .api.log import router as log_router` :

```python
from .api.references import router as references_router
```

Et après `app.include_router(log_router)` :

```python
app.include_router(references_router)
```

Le fichier complet devient :

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.health import router as health_router
from .api.pages import router as pages_router
from .api.search import router as search_router
from .api.ingest import router as ingest_router
from .api.answer import router as answer_router
from .api.log import router as log_router
from .api.references import router as references_router
from .mcp.server import mcp

app = FastAPI(title="OpenWikiLLM", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(pages_router)
app.include_router(search_router)
app.include_router(ingest_router)
app.include_router(answer_router)
app.include_router(log_router)
app.include_router(references_router)
app.mount("/mcp", mcp.http_app())
```

- [ ] **Step 7 : Vérifier que les tests passent**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend && source .venv/bin/activate && pytest tests/test_references_endpoint.py tests/test_stale_endpoint.py -v 2>&1 | tail -10
```

Attendu : `5 passed`

- [ ] **Step 8 : Vérifier la suite complète**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend && source .venv/bin/activate && pytest tests/ -q 2>&1 | tail -3
```

Attendu : `76 passed`

- [ ] **Step 9 : Commit**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm && git add backend/app/models/references.py backend/app/api/references.py backend/app/api/pages.py backend/app/main.py backend/tests/test_references_endpoint.py backend/tests/test_stale_endpoint.py && git commit -m "feat: add GET /references and PATCH /stale endpoints"
```

---

## Task 4 : MCP tools + ingest_service post-ingest + IngestResult

**Files:**
- Modify: `backend/app/mcp/server.py`
- Modify: `backend/app/services/ingest_service.py`
- Modify: `backend/app/models/ingest.py`
- Modify: `backend/tests/test_ingest.py` (assertions + nouveaux tests)

- [ ] **Step 1 : Écrire les tests qui échouent pour le post-ingest stale**

À la fin de `backend/tests/test_ingest.py`, ajouter :

```python
def test_ingest_marks_dependents_stale(client_with_dirs):
    """Page B a sources: [imports--test-ingestion] et n'est pas mise à jour → stale=True"""
    wiki_tmp = settings.wiki_path
    # Créer la page dépendante
    p = Path(wiki_tmp, "concept", "dependent.md")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "---\ntitle: Dependent\ntype: concept\nsources:\n  - imports--test-ingestion\n---\n\n# Dependent\n",
        encoding="utf-8",
    )
    # Ingest de imports--test-ingestion sans mise à jour de concept--dependent
    with patch("app.services.ingest_service.identify_related_pages", new=AsyncMock(return_value=[])), \
         patch("app.services.ingest_service.compile_multi_page", new=AsyncMock(return_value=MOCK_XML)):
        response = client_with_dirs.post(
            "/api/ingest/text",
            json={"text": "Texte source.", "title": "Test Ingestion", "tags": []},
        )
    assert response.status_code == 200
    data = response.json()
    assert "concept--dependent" in data["stale_marked"]
    # Vérifier que le frontmatter a été mis à jour
    from app.storage.wiki import load_page
    from pathlib import Path as P
    page = load_page(P(wiki_tmp, "concept", "dependent.md"), P(wiki_tmp))
    assert page.stale is True


def test_ingest_clears_stale_on_updated(client_with_dirs):
    """Page mis à jour par le LLM → stale doit être effacé"""
    wiki_tmp = settings.wiki_path
    # Créer concept--groove déjà stale
    p = Path(wiki_tmp, "concept", "groove.md")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "---\ntitle: Groove\ntype: concept\nstale: true\n---\n\n# Groove\n",
        encoding="utf-8",
    )
    # Ingest qui met à jour concept--groove
    xml_updates_groove = (
        f'<page slug="imports--test-ingestion">{MOCK_MARKDOWN}</page>\n'
        f'<page slug="concept--groove">{CONCEPT_MARKDOWN}</page>'
    )
    with patch("app.services.ingest_service.identify_related_pages", new=AsyncMock(return_value=[])), \
         patch("app.services.ingest_service.compile_multi_page", new=AsyncMock(return_value=xml_updates_groove)):
        response = client_with_dirs.post(
            "/api/ingest/text",
            json={"text": "Groove tickets.", "title": "Test Ingestion", "tags": []},
        )
    assert response.status_code == 200
    # concept--groove a été mis à jour → stale doit être False
    from app.storage.wiki import load_page
    from pathlib import Path as P
    page = load_page(P(wiki_tmp, "concept", "groove.md"), P(wiki_tmp))
    assert page.stale is False
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend && source .venv/bin/activate && pytest tests/test_ingest.py::test_ingest_marks_dependents_stale tests/test_ingest.py::test_ingest_clears_stale_on_updated -v 2>&1 | tail -10
```

Attendu : `KeyError: stale_marked` ou assertion fail

- [ ] **Step 3 : Mettre à jour IngestResult dans models/ingest.py**

Remplacer le contenu de `backend/app/models/ingest.py` :

```python
from pydantic import BaseModel


class IngestTextRequest(BaseModel):
    text: str
    title: str | None = None
    tags: list[str] = []


class IngestResult(BaseModel):
    slug: str
    raw_path: str
    wiki_path: str
    title: str
    pages_updated: list[str] = []
    concepts_created: list[str] = []
    entities_created: list[str] = []
    stale_marked: list[str] = []
```

- [ ] **Step 4 : Mettre à jour ingest_service.py avec la logique post-ingest stale**

Remplacer le contenu de `backend/app/services/ingest_service.py` :

```python
import re
import time
from pathlib import Path
from datetime import date
from .ollama_service import compile_image_to_markdown, identify_related_pages, compile_multi_page
from . import wiki_manager, schema_service, reference_service
from .search_service import rebuild_index
from ..core.config import settings


def _slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


async def ingest_text(text: str, title: str | None, tags: list[str]) -> dict:
    start = time.monotonic()
    today = date.today().isoformat()
    effective_title = title or "Source sans titre"
    slug = _slugify(effective_title)
    new_slug = f"imports--{slug}"

    raw_path = Path(settings.raw_path) / "imports" / f"{slug}.md"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(text, encoding="utf-8")

    schema = schema_service.load_or_create()
    index_content = wiki_manager.load_index()

    related_slugs = await identify_related_pages(text, effective_title, index_content)
    related_pages = wiki_manager.load_pages(related_slugs)

    xml_output = await compile_multi_page(
        text, effective_title, tags, today, schema, related_pages, new_slug
    )

    updates = wiki_manager.parse_xml_updates(xml_output)
    written_slugs = wiki_manager.apply_updates(updates)

    concepts_created = [s for s in written_slugs if s.startswith("concept--")]
    entities_created = [s for s in written_slugs if s.startswith("entity--")]
    known_prefixes = ("concept--", "entity--", "imports--")
    pages_updated = [
        s for s in written_slugs
        if (s.startswith("imports--") and s != new_slug)
        or not s.startswith(known_prefixes)
    ]

    wiki_manager.rebuild_index_file()
    rebuild_index()

    # Clear stale sur les pages mises à jour par le LLM
    for s in written_slugs:
        wiki_manager.set_stale(s, False)

    # Rebuild graph de références
    reference_service.rebuild_references()

    # Marquer stale les pages dépendantes non mises à jour
    stale_marked: list[str] = []
    refs = reference_service.get_references(new_slug)
    for dependent_slug in refs["referenced_by"]:
        if dependent_slug not in written_slugs:
            wiki_manager.set_stale(dependent_slug, True)
            stale_marked.append(dependent_slug)

    wiki_path = Path(settings.wiki_path) / "imports" / f"{slug}.md"
    duration_s = round(time.monotonic() - start)
    wiki_manager.append_log(
        f"## [{today}] ingest | {slug}\n"
        f"- Source : {new_slug}\n"
        f"- Concepts : {', '.join(concepts_created) or '—'}\n"
        f"- Entités : {', '.join(entities_created) or '—'}\n"
        f"- Tags : {', '.join(tags) or '—'}\n"
        f"- Durée : {duration_s}s\n"
    )

    return {
        "slug": new_slug,
        "raw_path": str(raw_path),
        "wiki_path": str(wiki_path),
        "title": effective_title,
        "pages_updated": pages_updated,
        "concepts_created": concepts_created,
        "entities_created": entities_created,
        "stale_marked": stale_marked,
    }


# Image ingest does not append to wiki/log.md — only text ingest is logged.
async def ingest_image(image_bytes: bytes, filename: str, title: str | None, tags: list[str]) -> dict:
    today = date.today().isoformat()
    effective_title = title or Path(filename).stem.replace("-", " ").replace("_", " ").capitalize()
    slug = _slugify(effective_title)
    suffix = Path(filename).suffix.lower()

    raw_path = Path(settings.raw_path) / "imports" / f"{slug}{suffix}"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(image_bytes)

    markdown = await compile_image_to_markdown(image_bytes, effective_title, tags, today)

    wiki_path = Path(settings.wiki_path) / "imports" / f"{slug}.md"
    wiki_path.parent.mkdir(parents=True, exist_ok=True)
    wiki_path.write_text(markdown, encoding="utf-8")

    return {
        "slug": f"imports--{slug}",
        "raw_path": str(raw_path),
        "wiki_path": str(wiki_path),
        "title": effective_title,
        "pages_updated": [],
        "concepts_created": [],
        "entities_created": [],
        "stale_marked": [],
    }
```

- [ ] **Step 5 : Ajouter les MCP tools dans server.py**

Dans `backend/app/mcp/server.py`, ajouter après les imports existants :

```python
from ..services import reference_service
```

Et ajouter les deux nouveaux tools à la fin du fichier :

```python
@mcp.tool()
def wiki_list_stale() -> list[dict]:
    """Liste toutes les pages wiki marquées comme obsolètes (stale: true)."""
    slugs = reference_service.get_stale_pages()
    return [{"slug": s} for s in slugs]


@mcp.tool()
def wiki_list_references(slug: str) -> dict:
    """
    Retourne les références d'une page wiki :
    - references : sources[] dont dépend cette page
    - referenced_by : pages qui dépendent de ce slug
    """
    return reference_service.get_references(slug)
```

- [ ] **Step 6 : Mettre à jour les assertions existantes dans test_ingest.py**

Ajouter `"stale_marked": []` aux assertions des tests existants où `response.json()` est utilisé. Les tests `test_ingest_text_creates_files`, `test_ingest_text_multi_page`, `test_ingest_text_no_related`, `test_ingest_text_with_concepts`, `test_ingest_text_with_entities` doivent inclure :

```python
assert data["stale_marked"] == []
```

(Ajouter cette ligne après les assertions `pages_updated`, `concepts_created`, `entities_created` dans chacun de ces tests.)

- [ ] **Step 7 : Vérifier tous les tests**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend && source .venv/bin/activate && pytest tests/ -q 2>&1 | tail -3
```

Attendu : `83 passed` (76 + 2 stale ingest + existing tests mis à jour ne changent pas le compte)

- [ ] **Step 8 : Commit**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm && git add backend/app/mcp/server.py backend/app/services/ingest_service.py backend/app/models/ingest.py backend/tests/test_ingest.py && git commit -m "feat: add stale tracking in ingest pipeline and MCP tools"
```

---

## Task 5 : Frontend

**Files:**
- Modify: `frontend/types/api.ts`
- Modify: `frontend/composables/useApi.ts`
- Modify: `frontend/pages/wiki/[slug].vue`

- [ ] **Step 1 : Mettre à jour frontend/types/api.ts**

Remplacer les interfaces `WikiPage`, `IngestResult` et ajouter `PageReferences` :

```typescript
export interface WikiPageSummary {
  slug: string
  title: string
  type: string
  status: string
  confidence: string
  sources: string[]
  updated_at: string
  tags: string[]
}

export interface WikiPage extends WikiPageSummary {
  content: string
  stale: boolean
}

export interface SearchResult {
  slug: string
  title: string
  snippet: string
  score: number
}

export interface AnswerResponse {
  answer: string
  mode: string
  sources: string[]
}

export interface IngestResult {
  slug: string
  raw_path: string
  wiki_path: string
  title: string
  pages_updated: string[]
  concepts_created: string[]
  entities_created: string[]
  stale_marked: string[]
}

export interface PageReferences {
  slug: string
  references: string[]
  referenced_by: string[]
}

export type AnswerMode = 'validated_only' | 'strict' | 'draft' | 'source_only'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: string[]
}

export interface LogResponse {
  content: string
}
```

- [ ] **Step 2 : Ajouter la méthode patch dans useApi.ts**

Dans `frontend/composables/useApi.ts`, ajouter après la fonction `post` :

```typescript
async function patch<T>(path: string, body: unknown): Promise<T> {
  return $fetch<T>(`${baseUrl}${path}`, {
    method: 'PATCH',
    headers: headers({ 'Content-Type': 'application/json' }),
    body,
    onResponseError,
  })
}
```

Et ajouter `patch` dans le return :

```typescript
return { get, post, postForm, patch }
```

- [ ] **Step 3 : Ajouter le badge Obsolète dans [slug].vue**

Remplacer le contenu de `frontend/pages/wiki/[slug].vue` :

```vue
<template>
  <div class="flex h-full overflow-hidden">
    <!-- Contenu principal -->
    <div class="flex-1 overflow-y-auto p-6 max-w-3xl mx-auto space-y-6">
      <div class="flex items-center gap-3">
        <NuxtLink to="/wiki" class="text-gray-400 hover:text-white transition-colors">
          <ArrowLeft class="w-4 h-4" />
        </NuxtLink>
        <h1 class="text-xl font-bold text-white">{{ currentPage?.title }}</h1>
      </div>

      <!-- Badge Obsolète -->
      <div
        v-if="currentPage?.stale"
        class="flex items-center gap-3 p-3 bg-red-900/30 border border-red-700 rounded-lg"
      >
        <span class="text-red-400 text-sm font-medium">⚠ Page obsolète</span>
        <span class="text-red-300 text-xs flex-1">
          Une source a été mise à jour depuis la dernière révision de cette page.
        </span>
        <button
          class="text-xs text-red-300 hover:text-white underline shrink-0"
          :disabled="markingCurrent"
          @click="markAsCurrent"
        >
          {{ markingCurrent ? '…' : 'Marquer comme à jour' }}
        </button>
      </div>

      <div v-if="loading" class="text-gray-400 text-sm">Chargement...</div>
      <div v-else-if="error" class="text-red-400 text-sm">{{ error }}</div>
      <MarkdownViewer v-else-if="currentPage" :content="currentPage.content" />
    </div>

    <!-- Panel frontmatter -->
    <div
      v-if="currentPage"
      class="w-64 shrink-0 border-l border-gray-800 p-4 space-y-4 overflow-y-auto bg-gray-900"
    >
      <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Métadonnées</h3>

      <div class="space-y-3 text-sm">
        <div>
          <p class="text-xs text-gray-500">Statut</p>
          <span
            :class="[
              'px-2 py-0.5 rounded text-xs font-medium',
              currentPage.status === 'validated'
                ? 'bg-green-900 text-green-300'
                : currentPage.status === 'draft'
                  ? 'bg-yellow-900 text-yellow-300'
                  : 'bg-gray-700 text-gray-400',
            ]"
          >
            {{ currentPage.status }}
          </span>
        </div>

        <div>
          <p class="text-xs text-gray-500">Confiance</p>
          <p class="text-gray-300">{{ currentPage.confidence }}</p>
        </div>

        <div>
          <p class="text-xs text-gray-500">Mis à jour</p>
          <p class="text-gray-300">{{ currentPage.updated_at || '—' }}</p>
        </div>

        <div v-if="currentPage.tags?.length">
          <p class="text-xs text-gray-500 mb-1">Tags</p>
          <div class="flex flex-wrap gap-1">
            <span
              v-for="tag in currentPage.tags"
              :key="tag"
              class="px-2 py-0.5 bg-gray-800 rounded text-xs text-gray-400"
            >
              #{{ tag }}
            </span>
          </div>
        </div>

        <div v-if="currentPage.sources?.length">
          <p class="text-xs text-gray-500 mb-1">Sources</p>
          <ul class="space-y-1">
            <li
              v-for="src in currentPage.sources"
              :key="src"
              class="text-xs text-gray-400 truncate"
            >
              {{ src }}
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ArrowLeft } from 'lucide-vue-next'
import { useApi } from '~/composables/useApi'

const route = useRoute()
const { currentPage, loading, error, fetchPage } = useWiki()
const { patch } = useApi()
const markingCurrent = ref(false)

onMounted(() => fetchPage(route.params.slug as string))

async function markAsCurrent() {
  if (!currentPage.value) return
  markingCurrent.value = true
  try {
    await patch(`/api/pages/${currentPage.value.slug}/stale`, { stale: false })
    await fetchPage(currentPage.value.slug)
  } finally {
    markingCurrent.value = false
  }
}
</script>
```

- [ ] **Step 4 : Vérifier la compilation TypeScript**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/frontend && npx nuxi typecheck 2>&1 | grep -E "ERROR|error TS" | grep -v "node_modules" | head -10
```

Attendu : aucune nouvelle erreur dans les fichiers modifiés.

- [ ] **Step 5 : Commit**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm && git add frontend/types/api.ts frontend/composables/useApi.ts frontend/pages/wiki/\[slug\].vue && git commit -m "feat: add stale badge and mark-as-current button in wiki page"
```

---

## Vérification finale

- [ ] Lancer la suite complète des tests backend :

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend && source .venv/bin/activate && pytest tests/ -v 2>&1 | tail -10
```

Attendu : `83 passed` minimum

- [ ] Vérifier les imports Python :

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend && source .venv/bin/activate && python -c "
from app.services.reference_service import rebuild_references, get_references, get_stale_pages
from app.services.wiki_manager import set_stale
from app.models.page import WikiPage, StaleUpdate
from app.models.references import PageReferences
from app.api.references import router
print('OK')
"
```

Attendu : `OK`
