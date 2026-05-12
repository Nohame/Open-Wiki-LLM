# OpenWikiLLM MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire le MVP OpenWikiLLM : API REST + serveur MCP permettant de lire, rechercher et ingérer des pages Markdown via Ollama, le tout dockerisé.

**Architecture:** FastAPI avec FastMCP monté sur `/mcp`, SQLite FTS5 pour la recherche, fichiers Markdown avec frontmatter YAML dans `wiki/`. Auth via `X-API-Key` header désactivable. Ollama tourne sur le host (`host.docker.internal:11434`).

**Tech Stack:** Python 3.11+, FastAPI, FastMCP, SQLite FTS5, python-frontmatter, Pydantic, pytest, Docker Compose, Ollama (httpx pour les appels).

---

## Étape 1 — Initialisation

### Task 1: Structure du projet

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/health.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/storage/__init__.py`
- Create: `backend/app/mcp/__init__.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_health.py`
- Create: `backend/pyproject.toml`
- Create: `backend/Dockerfile`
- Create: `docker-compose.yml`
- Create: `docker.sh`
- Create: `.env.example`
- Create: `CHANGELOG.md`
- Create: `README.md`
- Create: `wiki/.gitkeep`
- Create: `raw/.gitkeep`
- Create: `data/.gitkeep`
- Create: `docs/dev-notes/2026-05-12-initialisation.md`

- [ ] **Step 1: Créer les dossiers**

```bash
mkdir -p backend/app/{api,core,models,services,storage,mcp}
mkdir -p backend/tests
mkdir -p wiki raw data logs
mkdir -p docs/{architecture,changelog,decisions,dev-notes,specs}
touch backend/app/__init__.py
touch backend/app/api/__init__.py
touch backend/app/core/__init__.py
touch backend/app/models/__init__.py
touch backend/app/services/__init__.py
touch backend/app/storage/__init__.py
touch backend/app/mcp/__init__.py
touch backend/tests/__init__.py
touch wiki/.gitkeep raw/.gitkeep data/.gitkeep logs/.gitkeep
```

- [ ] **Step 2: Créer `backend/pyproject.toml`**

```toml
[project]
name = "openwikillm"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.29.0",
    "fastmcp>=2.0.0",
    "python-frontmatter>=1.1.0",
    "pydantic-settings>=2.2.0",
    "httpx>=0.27.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 3: Créer `backend/app/core/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "local"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8088

    raw_path: str = "/app/raw"
    wiki_path: str = "/app/wiki"
    data_path: str = "/app/data"

    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "mistral"

    api_key: str = ""

    class Config:
        env_file = ".env"
        env_prefix = "OPENWIKILLM_"
        extra = "ignore"


settings = Settings()
```

- [ ] **Step 4: Créer `backend/app/api/health.py`**

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}
```

- [ ] **Step 5: Créer `backend/app/core/auth.py`**

```python
from fastapi import Header, HTTPException, status
from .config import settings


async def verify_api_key(x_api_key: str = Header(default="")) -> None:
    if not settings.api_key:
        return
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
```

- [ ] **Step 6: Créer `backend/app/main.py`**

```python
from fastapi import FastAPI, Depends
from .api.health import router as health_router
from .core.auth import verify_api_key

app = FastAPI(title="OpenWikiLLM", version="0.1.0")

app.include_router(health_router)
```

- [ ] **Step 7: Écrire le test `backend/tests/test_health.py`**

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings


@pytest.fixture
def client():
    return TestClient(app)


def test_health_no_auth_when_key_empty(client, monkeypatch):
    monkeypatch.setattr(settings, "api_key", "")
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}


def test_health_with_valid_key(client, monkeypatch):
    monkeypatch.setattr(settings, "api_key", "secret")
    response = client.get("/health", headers={"X-API-Key": "secret"})
    assert response.status_code == 200


def test_health_route_ignores_auth(client, monkeypatch):
    monkeypatch.setattr(settings, "api_key", "secret")
    response = client.get("/health")
    assert response.status_code == 200
```

- [ ] **Step 8: Lancer les tests (hors Docker)**

```bash
cd backend
pip install -e ".[dev]"
pytest tests/test_health.py -v
```

Expected: 3 tests PASS

- [ ] **Step 9: Créer `backend/Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY app/ ./app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8088", "--reload"]
```

- [ ] **Step 10: Créer `docker-compose.yml`**

```yaml
services:
  openwikillm-api:
    build:
      context: ./backend
    container_name: openwikillm-api
    ports:
      - "8088:8088"
    volumes:
      - ./raw:/app/raw
      - ./wiki:/app/wiki
      - ./data:/app/data
      - ./docs:/app/docs
      - ./logs:/app/logs
    env_file:
      - .env
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

- [ ] **Step 11: Créer `docker.sh`**

```bash
#!/usr/bin/env bash

set -e

SERVICE_NAME="openwikillm-api"

case "$1" in
  start)
    docker compose up -d
    ;;
  stop)
    docker compose down
    ;;
  restart)
    docker compose down
    docker compose up -d
    ;;
  ssh)
    docker compose exec "$SERVICE_NAME" bash
    ;;
  *)
    echo "Usage: ./docker.sh {start|stop|restart|ssh}"
    exit 1
    ;;
esac
```

```bash
chmod +x docker.sh
```

- [ ] **Step 12: Créer `.env.example`**

```env
APP_ENV=local
APP_DEBUG=true
APP_HOST=0.0.0.0
APP_PORT=8088

OPENWIKILLM_RAW_PATH=/app/raw
OPENWIKILLM_WIKI_PATH=/app/wiki
OPENWIKILLM_DATA_PATH=/app/data

OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=mistral

API_KEY=
```

- [ ] **Step 13: Créer `.env` (copie locale, non commitée)**

```bash
cp .env.example .env
```

- [ ] **Step 14: Créer `CHANGELOG.md`**

```markdown
# Changelog

## Non publié

### Ajouté
- Initialisation du projet OpenWikiLLM
- Structure du projet
- Docker Compose + docker.sh
- API FastAPI minimale avec GET /health
- Middleware auth X-API-Key (désactivable)
```

- [ ] **Step 15: Tester le démarrage Docker**

```bash
./docker.sh start
curl http://localhost:8088/health
```

Expected: `{"status":"ok","version":"0.1.0"}`

```bash
./docker.sh stop
```

- [ ] **Step 16: Commit**

```bash
git add backend/ docker-compose.yml docker.sh .env.example CHANGELOG.md README.md wiki/.gitkeep raw/.gitkeep data/.gitkeep docs/
git commit -m "feat: initialisation projet OpenWikiLLM - structure, Docker, FastAPI /health"
```

---

## Étape 2 — Wiki Markdown

### Task 2: Lecture et parsing des pages Markdown

**Files:**
- Create: `backend/app/models/page.py`
- Create: `backend/app/storage/wiki.py`
- Create: `backend/app/services/wiki_service.py`
- Create: `backend/app/api/pages.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_wiki_service.py`
- Create: `backend/tests/test_api_pages.py`
- Create: `wiki/concepts/example.md` (fixture de test)

- [ ] **Step 1: Créer une page wiki de test `wiki/concepts/example.md`**

```markdown
---
title: Exemple de concept
type: concept
status: draft
confidence: medium
sources:
  - raw/imports/source.md
updated_at: 2026-05-12
tags:
  - exemple
  - test
---

# Exemple de concept

## Résumé

Ceci est une page d'exemple pour tester la lecture du wiki.

## Règles connues

- Règle 1 : toujours documenter.

## Pages liées

[[Autre concept]]
```

- [ ] **Step 2: Créer `backend/app/models/page.py`**

```python
from pydantic import BaseModel
from typing import Literal


class WikiPage(BaseModel):
    slug: str
    title: str
    type: Literal["concept", "project", "procedure", "decision", "note"] = "note"
    status: Literal["draft", "reviewed", "validated", "deprecated"] = "draft"
    confidence: Literal["low", "medium", "high"] = "medium"
    sources: list[str] = []
    updated_at: str = ""
    tags: list[str] = []
    content: str
```

- [ ] **Step 3: Créer `backend/app/storage/wiki.py`**

```python
from pathlib import Path
import frontmatter
from ..models.page import WikiPage


def _path_to_slug(wiki_path: Path, file_path: Path) -> str:
    return str(file_path.relative_to(wiki_path).with_suffix("")).replace("/", "--")


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
        content=post.content,
    )


def list_pages(wiki_path: Path) -> list[WikiPage]:
    pages = []
    for file_path in sorted(wiki_path.rglob("*.md")):
        if file_path.name == "index.md":
            continue
        pages.append(load_page(file_path, wiki_path))
    return pages


def get_page(slug: str, wiki_path: Path) -> WikiPage | None:
    for file_path in wiki_path.rglob("*.md"):
        if _path_to_slug(wiki_path, file_path) == slug:
            return load_page(file_path, wiki_path)
    return None
```

- [ ] **Step 4: Créer `backend/app/services/wiki_service.py`**

```python
from pathlib import Path
from ..models.page import WikiPage
from ..storage import wiki as wiki_storage
from ..core.config import settings


def list_pages() -> list[WikiPage]:
    return wiki_storage.list_pages(Path(settings.wiki_path))


def get_page(slug: str) -> WikiPage | None:
    return wiki_storage.get_page(slug, Path(settings.wiki_path))
```

- [ ] **Step 5: Écrire `backend/tests/test_wiki_service.py`**

```python
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
```

- [ ] **Step 6: Lancer les tests**

```bash
pytest tests/test_wiki_service.py -v
```

Expected: 4 tests PASS

- [ ] **Step 7: Créer `backend/app/api/pages.py`**

```python
from fastapi import APIRouter, HTTPException, Depends
from ..services.wiki_service import list_pages, get_page
from ..models.page import WikiPage
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
```

- [ ] **Step 8: Modifier `backend/app/main.py`**

```python
from fastapi import FastAPI
from .api.health import router as health_router
from .api.pages import router as pages_router

app = FastAPI(title="OpenWikiLLM", version="0.1.0")

app.include_router(health_router)
app.include_router(pages_router)
```

- [ ] **Step 9: Écrire `backend/tests/test_api_pages.py`**

```python
import pytest
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
import frontmatter as fm
from app.main import app
from app.core.config import settings


@pytest.fixture
def client_with_wiki(monkeypatch):
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
            tags=["livraison"],
            sources=[],
            updated_at="2026-05-12",
        )
        page.write_text(fm.dumps(post))
        monkeypatch.setattr(settings, "api_key", "")
        monkeypatch.setattr(settings, "wiki_path", str(wiki))
        yield TestClient(app)


def test_list_pages(client_with_wiki):
    response = client_with_wiki.get("/api/pages")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Livraison 24h"


def test_get_page_found(client_with_wiki):
    response = client_with_wiki.get("/api/pages/concepts--livraison")
    assert response.status_code == 200
    assert response.json()["title"] == "Livraison 24h"


def test_get_page_not_found(client_with_wiki):
    response = client_with_wiki.get("/api/pages/nonexistent")
    assert response.status_code == 404


def test_api_requires_key_when_set(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "secret")
    client = TestClient(app)
    response = client.get("/api/pages")
    assert response.status_code == 401
```

- [ ] **Step 10: Lancer tous les tests**

```bash
pytest tests/ -v
```

Expected: tous les tests PASS

- [ ] **Step 11: Commit**

```bash
git add backend/app/models/page.py backend/app/storage/wiki.py \
        backend/app/services/wiki_service.py backend/app/api/pages.py \
        backend/app/main.py backend/tests/test_wiki_service.py \
        backend/tests/test_api_pages.py wiki/concepts/example.md
git commit -m "feat: lecture pages Markdown avec frontmatter, GET /api/pages et /api/pages/{slug}"
```

---

## Étape 3 — Index SQLite FTS5

### Task 3: Indexation et recherche

**Files:**
- Create: `backend/app/storage/search.py`
- Create: `backend/app/services/search_service.py`
- Create: `backend/app/models/search.py`
- Create: `backend/app/api/search.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_search.py`

- [ ] **Step 1: Créer `backend/app/models/search.py`**

```python
from pydantic import BaseModel


class SearchQuery(BaseModel):
    q: str
    limit: int = 10


class SearchResult(BaseModel):
    slug: str
    title: str
    snippet: str
    score: float
```

- [ ] **Step 2: Écrire `backend/tests/test_search.py`** (test en premier)

```python
import pytest
import tempfile
from pathlib import Path
from app.storage.search import SearchIndex


@pytest.fixture
def index():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        idx = SearchIndex(db_path)
        idx.index_page(
            slug="concepts--livraison",
            title="Livraison 24h",
            content="Livraison rapide en vingt-quatre heures garantie.",
            tags="livraison transport",
        )
        idx.index_page(
            slug="concepts--retour",
            title="Politique de retour",
            content="Retour possible sous 30 jours.",
            tags="retour client",
        )
        yield idx


def test_search_returns_relevant_result(index):
    results = index.search("livraison", limit=5)
    assert len(results) >= 1
    assert results[0]["slug"] == "concepts--livraison"


def test_search_no_result(index):
    results = index.search("inexistant", limit=5)
    assert results == []


def test_rebuild_clears_old_data(index):
    index.index_page(
        slug="concepts--livraison",
        title="Livraison 24h",
        content="Contenu mis à jour.",
        tags="livraison",
    )
    results = index.search("livraison", limit=5)
    assert len(results) == 1
```

- [ ] **Step 3: Lancer le test pour vérifier qu'il échoue**

```bash
pytest tests/test_search.py -v
```

Expected: FAIL avec "cannot import name 'SearchIndex'"

- [ ] **Step 4: Créer `backend/app/storage/search.py`**

```python
import sqlite3
from pathlib import Path


class SearchIndex:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS wiki_pages_fts
                USING fts5(slug, title, content, tags)
            """)

    def index_page(self, slug: str, title: str, content: str, tags: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM wiki_pages_fts WHERE slug = ?", (slug,)
            )
            conn.execute(
                "INSERT INTO wiki_pages_fts(slug, title, content, tags) VALUES (?, ?, ?, ?)",
                (slug, title, content, tags),
            )

    def search(self, query: str, limit: int = 10) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT slug, title,
                       snippet(wiki_pages_fts, 2, '<b>', '</b>', '...', 20) as snippet,
                       rank
                FROM wiki_pages_fts
                WHERE wiki_pages_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
        return [
            {"slug": r[0], "title": r[1], "snippet": r[2], "score": r[3]}
            for r in rows
        ]

    def rebuild(self, pages: list[dict]) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM wiki_pages_fts")
        for page in pages:
            self.index_page(
                slug=page["slug"],
                title=page["title"],
                content=page["content"],
                tags=" ".join(page.get("tags", [])),
            )
```

- [ ] **Step 5: Lancer les tests search**

```bash
pytest tests/test_search.py -v
```

Expected: 3 tests PASS

- [ ] **Step 6: Créer `backend/app/services/search_service.py`**

```python
from pathlib import Path
from .wiki_service import list_pages
from ..storage.search import SearchIndex
from ..models.search import SearchResult
from ..core.config import settings


def _get_index() -> SearchIndex:
    return SearchIndex(Path(settings.data_path) / "openwikillm.db")


def rebuild_index() -> int:
    pages = list_pages()
    index = _get_index()
    index.rebuild([
        {
            "slug": p.slug,
            "title": p.title,
            "content": p.content,
            "tags": p.tags,
        }
        for p in pages
    ])
    return len(pages)


def search(query: str, limit: int = 10) -> list[SearchResult]:
    index = _get_index()
    results = index.search(query, limit=limit)
    return [
        SearchResult(
            slug=r["slug"],
            title=r["title"],
            snippet=r["snippet"],
            score=r["score"],
        )
        for r in results
    ]
```

- [ ] **Step 7: Créer `backend/app/api/search.py`**

```python
from fastapi import APIRouter, Depends
from ..services.search_service import search, rebuild_index
from ..models.search import SearchQuery, SearchResult
from ..core.auth import verify_api_key

router = APIRouter(prefix="/api", dependencies=[Depends(verify_api_key)])


@router.post("/search", response_model=list[SearchResult])
def search_pages(query: SearchQuery) -> list[SearchResult]:
    return search(query.q, query.limit)


@router.post("/index/rebuild")
def rebuild() -> dict:
    count = rebuild_index()
    return {"indexed": count}
```

- [ ] **Step 8: Modifier `backend/app/main.py`**

```python
from fastapi import FastAPI
from .api.health import router as health_router
from .api.pages import router as pages_router
from .api.search import router as search_router

app = FastAPI(title="OpenWikiLLM", version="0.1.0")

app.include_router(health_router)
app.include_router(pages_router)
app.include_router(search_router)
```

- [ ] **Step 9: Lancer tous les tests**

```bash
pytest tests/ -v
```

Expected: tous les tests PASS

- [ ] **Step 10: Commit**

```bash
git add backend/app/models/search.py backend/app/storage/search.py \
        backend/app/services/search_service.py backend/app/api/search.py \
        backend/app/main.py backend/tests/test_search.py
git commit -m "feat: index SQLite FTS5, POST /api/search, POST /api/index/rebuild"
```

---

## Étape 4 — MCP Server

### Task 4: Montage FastMCP dans FastAPI

**Files:**
- Create: `backend/app/mcp/server.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_mcp_tools.py`
- Create: `docs/dev-notes/2026-05-12-mcp-server.md`

- [ ] **Step 1: Créer `backend/app/mcp/server.py`**

```python
from fastmcp import FastMCP
from ..services.wiki_service import list_pages, get_page
from ..services.search_service import search, rebuild_index

mcp = FastMCP("openwikillm")


@mcp.tool()
def wiki_list_pages() -> list[dict]:
    """Liste toutes les pages du wiki."""
    return [p.model_dump(exclude={"content"}) for p in list_pages()]


@mcp.tool()
def wiki_read_page(slug: str) -> dict | None:
    """Lit le contenu complet d'une page wiki par son slug."""
    page = get_page(slug)
    if page is None:
        return None
    return page.model_dump()


@mcp.tool()
def wiki_search(query: str, limit: int = 10) -> list[dict]:
    """Recherche dans le wiki via FTS5."""
    results = search(query, limit=limit)
    return [r.model_dump() for r in results]


@mcp.tool()
def wiki_rebuild_index() -> dict:
    """Reconstruit l'index de recherche FTS5."""
    count = rebuild_index()
    return {"indexed": count}
```

- [ ] **Step 2: Modifier `backend/app/main.py`**

```python
from fastapi import FastAPI
from .api.health import router as health_router
from .api.pages import router as pages_router
from .api.search import router as search_router
from .mcp.server import mcp

app = FastAPI(title="OpenWikiLLM", version="0.1.0")

app.include_router(health_router)
app.include_router(pages_router)
app.include_router(search_router)
app.mount("/mcp", mcp.get_asgi_app())
```

- [ ] **Step 3: Écrire `backend/tests/test_mcp_tools.py`**

```python
import pytest
import tempfile
from pathlib import Path
import frontmatter as fm
from app.mcp.server import wiki_list_pages, wiki_read_page, wiki_search, wiki_rebuild_index
from app.core.config import settings


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
```

- [ ] **Step 4: Lancer les tests**

```bash
pytest tests/test_mcp_tools.py -v
```

Expected: 4 tests PASS

- [ ] **Step 5: Lancer tous les tests**

```bash
pytest tests/ -v
```

Expected: tous les tests PASS

- [ ] **Step 6: Créer `docs/dev-notes/2026-05-12-mcp-server.md`**

```markdown
# MCP Server — Montage dans FastAPI

## Objectif
Exposer les outils wiki (lecture, recherche, indexation) via le protocole MCP
pour permettre aux agents IA (Claude Code, Claude Desktop) de consulter le wiki.

## Fichiers modifiés
- `backend/app/mcp/server.py` (créé)
- `backend/app/main.py` (montage `/mcp`)

## Décisions prises
- FastMCP monté via ASGI sur `/mcp` — même process que FastAPI
- Auth couverte par le middleware FastAPI (X-API-Key)

## Config client MCP
```json
{
  "openwikillm": {
    "type": "http",
    "url": "http://localhost:8088/mcp"
  }
}
```

## Tests effectués
- wiki_list_pages, wiki_read_page, wiki_search, wiki_rebuild_index

## Prochaines étapes
- Étape 5 : ingestion texte via Ollama
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/mcp/server.py backend/app/main.py \
        backend/tests/test_mcp_tools.py \
        docs/dev-notes/2026-05-12-mcp-server.md
git commit -m "feat: serveur MCP monté sur /mcp avec wiki_search, wiki_read_page, wiki_list_pages, wiki_rebuild_index"
```

---

## Étape 5 — Ingestion simple

### Task 5: POST /api/ingest/text via Ollama

**Files:**
- Create: `backend/app/models/ingest.py`
- Create: `backend/app/services/ollama_service.py`
- Create: `backend/app/services/ingest_service.py`
- Create: `backend/app/api/ingest.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_ingest.py`

- [ ] **Step 1: Créer `backend/app/models/ingest.py`**

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
```

- [ ] **Step 2: Créer `backend/app/services/ollama_service.py`**

```python
import httpx
import json
from ..core.config import settings

COMPILE_PROMPT = """\
Tu es un assistant qui structure des textes bruts en pages wiki Markdown.

Voici un texte brut à structurer :

---
{text}
---

Génère une page wiki Markdown avec ce format EXACT (frontmatter inclus) :

```markdown
---
title: {title}
type: concept
status: draft
confidence: medium
sources: []
updated_at: {date}
tags: {tags}
---

# {title}

## Résumé

## Règles connues

## Points à confirmer
```

Réponds UNIQUEMENT avec le Markdown, sans commentaire ni explication.
"""


async def compile_to_markdown(text: str, title: str, tags: list[str], date: str) -> str:
    prompt = COMPILE_PROMPT.format(
        text=text,
        title=title,
        tags=json.dumps(tags, ensure_ascii=False),
        date=date,
    )
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
            },
        )
        response.raise_for_status()
        return response.json()["response"]
```

- [ ] **Step 3: Créer `backend/app/services/ingest_service.py`**

```python
import re
from pathlib import Path
from datetime import date
from ..services.ollama_service import compile_to_markdown
from ..core.config import settings


def _slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


async def ingest_text(text: str, title: str | None, tags: list[str]) -> dict:
    today = date.today().isoformat()
    effective_title = title or "Source sans titre"
    slug = _slugify(effective_title)

    raw_path = Path(settings.raw_path) / "imports" / f"{slug}.md"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(text)

    markdown = await compile_to_markdown(text, effective_title, tags, today)

    wiki_path = Path(settings.wiki_path) / "imports" / f"{slug}.md"
    wiki_path.parent.mkdir(parents=True, exist_ok=True)
    wiki_path.write_text(markdown)

    return {
        "slug": f"imports--{slug}",
        "raw_path": str(raw_path),
        "wiki_path": str(wiki_path),
        "title": effective_title,
    }
```

- [ ] **Step 4: Écrire `backend/tests/test_ingest.py`**

```python
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

MOCK_MARKDOWN = """\
---
title: Test Ingestion
type: concept
status: draft
confidence: medium
sources: []
updated_at: 2026-05-12
tags: ["test"]
---

# Test Ingestion

## Résumé

Contenu structuré par Ollama.

## Règles connues

## Points à confirmer
"""


@pytest.fixture
def client_with_dirs(monkeypatch):
    with tempfile.TemporaryDirectory() as wiki_tmp, \
         tempfile.TemporaryDirectory() as raw_tmp:
        monkeypatch.setattr(settings, "wiki_path", wiki_tmp)
        monkeypatch.setattr(settings, "raw_path", raw_tmp)
        monkeypatch.setattr(settings, "api_key", "")
        yield TestClient(app)


def test_ingest_text_creates_files(client_with_dirs):
    with patch(
        "app.services.ingest_service.compile_to_markdown",
        new=AsyncMock(return_value=MOCK_MARKDOWN),
    ):
        response = client_with_dirs.post(
            "/api/ingest/text",
            json={"text": "Texte source brut.", "title": "Test Ingestion", "tags": ["test"]},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "imports--test-ingestion"
    assert Path(data["raw_path"]).exists()
    assert Path(data["wiki_path"]).exists()


def test_ingest_text_without_title(client_with_dirs):
    with patch(
        "app.services.ingest_service.compile_to_markdown",
        new=AsyncMock(return_value=MOCK_MARKDOWN),
    ):
        response = client_with_dirs.post(
            "/api/ingest/text",
            json={"text": "Texte sans titre."},
        )
    assert response.status_code == 200
```

- [ ] **Step 5: Lancer les tests pour vérifier qu'ils échouent**

```bash
pytest tests/test_ingest.py -v
```

Expected: FAIL avec "cannot import"

- [ ] **Step 6: Créer `backend/app/api/ingest.py`**

```python
from fastapi import APIRouter, Depends
from ..services.ingest_service import ingest_text
from ..models.ingest import IngestTextRequest, IngestResult
from ..core.auth import verify_api_key

router = APIRouter(prefix="/api", dependencies=[Depends(verify_api_key)])


@router.post("/ingest/text", response_model=IngestResult)
async def ingest_text_endpoint(request: IngestTextRequest) -> IngestResult:
    result = await ingest_text(request.text, request.title, request.tags)
    return IngestResult(**result)
```

- [ ] **Step 7: Modifier `backend/app/main.py`**

```python
from fastapi import FastAPI
from .api.health import router as health_router
from .api.pages import router as pages_router
from .api.search import router as search_router
from .api.ingest import router as ingest_router
from .mcp.server import mcp

app = FastAPI(title="OpenWikiLLM", version="0.1.0")

app.include_router(health_router)
app.include_router(pages_router)
app.include_router(search_router)
app.include_router(ingest_router)
app.mount("/mcp", mcp.get_asgi_app())
```

- [ ] **Step 8: Lancer tous les tests**

```bash
pytest tests/ -v
```

Expected: tous les tests PASS

- [ ] **Step 9: Commit**

```bash
git add backend/app/models/ingest.py backend/app/services/ollama_service.py \
        backend/app/services/ingest_service.py backend/app/api/ingest.py \
        backend/app/main.py backend/tests/test_ingest.py
git commit -m "feat: ingestion texte via Ollama, POST /api/ingest/text"
```

---

## Étape 6 — Préparation IA

### Task 6: Modes strict et validated_only

**Files:**
- Create: `backend/app/models/answer.py`
- Create: `backend/app/services/answer_service.py`
- Create: `backend/app/api/answer.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_answer.py`

- [ ] **Step 1: Créer `backend/app/models/answer.py`**

```python
from pydantic import BaseModel
from typing import Literal


class AnswerRequest(BaseModel):
    question: str
    mode: Literal["draft", "strict", "source_only", "validated_only"] = "strict"
    limit: int = 5


class AnswerResponse(BaseModel):
    answer: str
    mode: str
    sources: list[str]
```

- [ ] **Step 2: Écrire `backend/tests/test_answer.py`**

```python
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch
import frontmatter as fm
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings


@pytest.fixture
def client_validated(monkeypatch):
    with tempfile.TemporaryDirectory() as wiki_tmp, \
         tempfile.TemporaryDirectory() as data_tmp:
        wiki = Path(wiki_tmp)
        (wiki / "concepts").mkdir()
        page = wiki / "concepts" / "livraison.md"
        post = fm.Post(
            "Livraison garantie en 24h sur tout le territoire.",
            title="Livraison 24h",
            type="concept",
            status="validated",
            confidence="high",
            tags=["livraison"],
            sources=[],
            updated_at="2026-05-12",
        )
        page.write_text(fm.dumps(post))
        monkeypatch.setattr(settings, "wiki_path", str(wiki))
        monkeypatch.setattr(settings, "data_path", data_tmp)
        monkeypatch.setattr(settings, "api_key", "")
        yield TestClient(app)


def test_strict_mode_no_result_returns_fallback(client_validated):
    response = client_validated.post(
        "/api/answer",
        json={"question": "Quel est le prix ?", "mode": "strict"},
    )
    assert response.status_code == 200
    assert "Je ne trouve pas" in response.json()["answer"]


def test_validated_only_returns_answer(client_validated):
    with patch(
        "app.services.answer_service.call_ollama",
        new=AsyncMock(return_value="Livraison en 24h."),
    ):
        response = client_validated.post(
            "/api/answer",
            json={"question": "délai livraison", "mode": "validated_only"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] != "Je ne trouve pas cette information dans le wiki validé."
```

- [ ] **Step 3: Lancer les tests pour vérifier qu'ils échouent**

```bash
pytest tests/test_answer.py -v
```

Expected: FAIL avec "cannot import"

- [ ] **Step 4: Créer `backend/app/services/answer_service.py`**

```python
from ..services.search_service import search
from ..services.wiki_service import list_pages
from ..services.ollama_service import compile_to_markdown as _compile
import httpx
from ..models.answer import AnswerRequest, AnswerResponse
from ..core.config import settings

FALLBACK = "Je ne trouve pas cette information dans le wiki validé."

ANSWER_PROMPT = """\
Tu es un assistant qui répond à des questions à partir d'extraits de wiki.

Question : {question}

Extraits pertinents du wiki :
{context}

Réponds en te basant uniquement sur ces extraits. Si tu ne peux pas répondre, dis-le clairement.
"""


async def call_ollama(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/generate",
            json={"model": settings.ollama_model, "prompt": prompt, "stream": False},
        )
        response.raise_for_status()
        return response.json()["response"]


async def answer(request: AnswerRequest) -> AnswerResponse:
    results = search(request.question, limit=request.limit)

    if request.mode in ("strict", "validated_only"):
        all_pages = list_pages()
        validated_slugs = {p.slug for p in all_pages if p.status == "validated"}
        results = [r for r in results if r.slug in validated_slugs]

    if not results:
        return AnswerResponse(answer=FALLBACK, mode=request.mode, sources=[])

    context = "\n\n".join(
        f"[{r.title}]\n{r.snippet}" for r in results
    )
    prompt = ANSWER_PROMPT.format(question=request.question, context=context)
    llm_answer = await call_ollama(prompt)

    return AnswerResponse(
        answer=llm_answer,
        mode=request.mode,
        sources=[r.slug for r in results],
    )
```

- [ ] **Step 5: Créer `backend/app/api/answer.py`**

```python
from fastapi import APIRouter, Depends
from ..services.answer_service import answer
from ..models.answer import AnswerRequest, AnswerResponse
from ..core.auth import verify_api_key

router = APIRouter(prefix="/api", dependencies=[Depends(verify_api_key)])


@router.post("/answer", response_model=AnswerResponse)
async def answer_question(request: AnswerRequest) -> AnswerResponse:
    return await answer(request)
```

- [ ] **Step 6: Modifier `backend/app/main.py`**

```python
from fastapi import FastAPI
from .api.health import router as health_router
from .api.pages import router as pages_router
from .api.search import router as search_router
from .api.ingest import router as ingest_router
from .api.answer import router as answer_router
from .mcp.server import mcp

app = FastAPI(title="OpenWikiLLM", version="0.1.0")

app.include_router(health_router)
app.include_router(pages_router)
app.include_router(search_router)
app.include_router(ingest_router)
app.include_router(answer_router)
app.mount("/mcp", mcp.get_asgi_app())
```

- [ ] **Step 7: Lancer tous les tests**

```bash
pytest tests/ -v
```

Expected: tous les tests PASS

- [ ] **Step 8: Commit final MVP**

```bash
git add backend/app/models/answer.py backend/app/services/answer_service.py \
        backend/app/api/answer.py backend/app/main.py backend/tests/test_answer.py
git commit -m "feat: modes strict/validated_only, POST /api/answer via Ollama"
```

---

## Critères d'acceptation MVP

- [ ] `./docker.sh start` → pas d'erreur
- [ ] `curl http://localhost:8088/health` → `{"status":"ok","version":"0.1.0"}`
- [ ] `pytest tests/ -v` → tous les tests PASS
- [ ] `POST /api/ingest/text` → crée une page draft dans `wiki/imports/`
- [ ] `POST /api/index/rebuild` → indexe les pages
- [ ] `POST /api/search` → retourne des résultats
- [ ] `GET /api/pages` → liste les pages
- [ ] MCP accessible sur `http://localhost:8088/mcp`
- [ ] Aucun commit effectué sans validation explicite
