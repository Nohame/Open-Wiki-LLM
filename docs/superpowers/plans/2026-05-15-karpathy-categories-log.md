# Karpathy Pattern — Catégories Wiki + Log Enrichi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Activer la création automatique de pages `concept--` et `entity--` par le LLM, enrichir `wiki/log.md` avec durée/tags/catégories, et exposer ce journal dans une page `/log` du frontend.

**Architecture:** Modification du prompt `MULTI_UPDATE_PROMPT` (instructions concept/entity explicites), catégorisation des slugs écrits dans `ingest_service.py` (par préfixe), nouveau endpoint `GET /api/wiki/log` retournant le markdown brut, nouvelle page Nuxt `/log` utilisant `MarkdownViewer`.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, pytest, Nuxt 3, Vue 3, TypeScript, lucide-vue-next

---

## Fichiers touchés

| Statut | Fichier |
|--------|---------|
| Modifier | `backend/app/services/wiki_manager.py` — ajouter `load_log()` |
| Créer | `backend/app/models/log.py` — modèle `LogResponse` |
| Créer | `backend/app/api/log.py` — endpoint `GET /api/wiki/log` |
| Modifier | `backend/app/main.py` — enregistrer log router |
| Modifier | `backend/tests/test_wiki_manager.py` — 2 nouveaux tests |
| Créer | `backend/tests/test_log_endpoint.py` — 2 tests endpoint |
| Modifier | `backend/app/services/ollama_service.py` — règles MULTI_UPDATE_PROMPT |
| Modifier | `backend/app/models/ingest.py` — ajouter `concepts_created`, `entities_created` |
| Modifier | `backend/app/services/ingest_service.py` — durée + catégorisation + log enrichi |
| Modifier | `backend/tests/test_ingest.py` — assertions + nouveau test |
| Modifier | `frontend/types/api.ts` — `IngestResult` + `LogResponse` |
| Modifier | `frontend/components/layout/AppSidebar.vue` — lien Journal |
| Créer | `frontend/pages/log.vue` — page journal |
| Modifier | `frontend/components/ingest/IngestText.vue` — afficher concepts/entités |
| Modifier | `frontend/components/ingest/IngestFile.vue` — afficher concepts/entités |

---

## Task 1: load_log + API endpoint log

**Files:**
- Modify: `backend/app/services/wiki_manager.py`
- Create: `backend/app/models/log.py`
- Create: `backend/app/api/log.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_wiki_manager.py`
- Create: `backend/tests/test_log_endpoint.py`

- [ ] **Step 1 : Ajouter les tests load_log dans test_wiki_manager.py**

À la fin de `backend/tests/test_wiki_manager.py`, ajouter :

```python
def test_load_log_absent(tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "wiki_path", str(tmp_path))
    from app.services.wiki_manager import load_log
    assert load_log() == ""


def test_load_log_present(tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "wiki_path", str(tmp_path))
    (tmp_path / "log.md").write_text("# Journal\n\n## test", encoding="utf-8")
    from app.services.wiki_manager import load_log
    assert load_log() == "# Journal\n\n## test"
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend && source .venv/bin/activate && pytest tests/test_wiki_manager.py::test_load_log_absent tests/test_wiki_manager.py::test_load_log_present -v 2>&1 | tail -10
```

Attendu : `AttributeError: module has no attribute 'load_log'`

- [ ] **Step 3 : Ajouter load_log à wiki_manager.py**

À la fin de `backend/app/services/wiki_manager.py`, avant `_extract_frontmatter_title`, ajouter :

```python
def load_log() -> str:
    log_path = Path(settings.wiki_path) / "log.md"
    if not log_path.exists():
        return ""
    return log_path.read_text(encoding="utf-8")
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend && source .venv/bin/activate && pytest tests/test_wiki_manager.py -v 2>&1 | tail -5
```

Attendu : `13 passed`

- [ ] **Step 5 : Créer backend/app/models/log.py**

```python
from pydantic import BaseModel


class LogResponse(BaseModel):
    content: str
```

- [ ] **Step 6 : Créer backend/app/api/log.py**

```python
from fastapi import APIRouter
from ..services import wiki_manager
from ..models.log import LogResponse

router = APIRouter(prefix="/api")


@router.get("/wiki/log", response_model=LogResponse)
async def get_log() -> LogResponse:
    return LogResponse(content=wiki_manager.load_log())
```

- [ ] **Step 7 : Enregistrer le router dans main.py**

Dans `backend/app/main.py`, ajouter l'import et l'enregistrement après `answer_router` :

```python
from .api.log import router as log_router
```

Et dans la liste des `include_router` :

```python
app.include_router(log_router)
```

Le fichier complet doit ressembler à :

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.health import router as health_router
from .api.pages import router as pages_router
from .api.search import router as search_router
from .api.ingest import router as ingest_router
from .api.answer import router as answer_router
from .api.log import router as log_router
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
app.mount("/mcp", mcp.http_app())
```

- [ ] **Step 8 : Créer backend/tests/test_log_endpoint.py**

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


def test_log_endpoint_empty(client_with_dirs):
    response = client_with_dirs.get("/api/wiki/log")
    assert response.status_code == 200
    assert response.json()["content"] == ""


def test_log_endpoint_with_content(client_with_dirs):
    (Path(settings.wiki_path) / "log.md").write_text(
        "# Journal\n\n## test", encoding="utf-8"
    )
    response = client_with_dirs.get("/api/wiki/log")
    assert response.status_code == 200
    assert "Journal" in response.json()["content"]
```

- [ ] **Step 9 : Lancer tous les tests backend**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend && source .venv/bin/activate && pytest tests/ -v 2>&1 | tail -10
```

Attendu : `52 passed`

- [ ] **Step 10 : Commit**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm && git add backend/app/services/wiki_manager.py backend/app/models/log.py backend/app/api/log.py backend/app/main.py backend/tests/test_wiki_manager.py backend/tests/test_log_endpoint.py && git commit -m "feat: add load_log and GET /api/wiki/log endpoint"
```

---

## Task 2: MULTI_UPDATE_PROMPT — instructions concept/entity

**Files:**
- Modify: `backend/app/services/ollama_service.py`

- [ ] **Step 1 : Localiser la section Règles dans MULTI_UPDATE_PROMPT**

Ouvrir `backend/app/services/ollama_service.py`. La constante `MULTI_UPDATE_PROMPT` contient une section `Règles :` avec les lignes suivantes :

```
Règles :
- Crée une page pour le document source (slug : {new_slug})
- Mets à jour les pages liées : nouvelles informations, corrections, cross-refs [[slug]]
- N'inclus QUE les pages qui changent réellement
- Réponds UNIQUEMENT avec les balises <page>, sans commentaire
```

- [ ] **Step 2 : Remplacer la section Règles**

Remplacer uniquement ces 5 lignes par :

```
Règles :
- Crée une page de type `source` pour le document (slug : {new_slug})
- Si le document contient des concepts métier distincts, crée ou mets à jour les pages concept-- correspondantes (ex: concept--groove-tags)
- Si le document mentionne des entités (personnes, fournisseurs, outils, systèmes), crée ou mets à jour les pages entity-- correspondantes (ex: entity--alizee)
- Mets à jour les pages liées existantes : nouvelles informations, corrections, cross-refs [[slug]]
- N'inclus QUE les pages qui changent réellement
- Réponds UNIQUEMENT avec les balises <page>, sans commentaire
```

- [ ] **Step 3 : Vérifier la syntaxe**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend && source .venv/bin/activate && python -c "from app.services.ollama_service import MULTI_UPDATE_PROMPT; assert 'concept--' in MULTI_UPDATE_PROMPT; assert 'entity--' in MULTI_UPDATE_PROMPT; print('OK')"
```

Attendu : `OK`

- [ ] **Step 4 : Commit**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm && git add backend/app/services/ollama_service.py && git commit -m "feat: guide LLM to create concept-- and entity-- pages in wiki prompt"
```

---

## Task 3: ingest_service + IngestResult + tests

**Files:**
- Modify: `backend/app/models/ingest.py`
- Modify: `backend/app/services/ingest_service.py`
- Modify: `backend/tests/test_ingest.py`

- [ ] **Step 1 : Mettre à jour IngestResult dans models/ingest.py**

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
```

- [ ] **Step 2 : Réécrire ingest_text dans ingest_service.py**

Remplacer le contenu de `backend/app/services/ingest_service.py` :

```python
import re
import time
from pathlib import Path
from datetime import date
from .ollama_service import compile_image_to_markdown, identify_related_pages, compile_multi_page
from . import wiki_manager, schema_service
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
    pages_updated = [s for s in written_slugs if s.startswith("imports--") and s != new_slug]

    wiki_manager.rebuild_index_file()
    duration_s = round(time.monotonic() - start)
    wiki_manager.append_log(
        f"## [{today}] ingest | {slug}\n"
        f"- Source : {new_slug}\n"
        f"- Concepts : {', '.join(concepts_created) or '—'}\n"
        f"- Entités : {', '.join(entities_created) or '—'}\n"
        f"- Tags : {', '.join(tags) or '—'}\n"
        f"- Durée : {duration_s}s\n"
    )

    rebuild_index()

    wiki_path = Path(settings.wiki_path) / "imports" / f"{slug}.md"
    return {
        "slug": new_slug,
        "raw_path": str(raw_path),
        "wiki_path": str(wiki_path),
        "title": effective_title,
        "pages_updated": pages_updated,
        "concepts_created": concepts_created,
        "entities_created": entities_created,
    }


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
    }
```

- [ ] **Step 3 : Remplacer test_ingest.py**

Remplacer le contenu de `backend/tests/test_ingest.py` :

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

MOCK_XML = f'<page slug="imports--test-ingestion">{MOCK_MARKDOWN}</page>'

CONCEPT_MARKDOWN = """\
---
title: Groove
type: concept
status: draft
confidence: medium
sources: []
updated_at: 2026-05-15
tags: []
---

# Groove

## Résumé

Outil de gestion tickets.
"""


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


def test_ingest_text_creates_files(client_with_dirs):
    with patch("app.services.ingest_service.identify_related_pages", new=AsyncMock(return_value=[])), \
         patch("app.services.ingest_service.compile_multi_page", new=AsyncMock(return_value=MOCK_XML)):
        response = client_with_dirs.post(
            "/api/ingest/text",
            json={"text": "Texte source brut.", "title": "Test Ingestion", "tags": ["test"]},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "imports--test-ingestion"
    assert Path(data["raw_path"]).exists()
    assert Path(data["wiki_path"]).exists()
    assert data["pages_updated"] == []
    assert data["concepts_created"] == []
    assert data["entities_created"] == []


def test_ingest_text_without_title(client_with_dirs):
    mock_xml = f'<page slug="imports--source-sans-titre">{MOCK_MARKDOWN}</page>'
    with patch("app.services.ingest_service.identify_related_pages", new=AsyncMock(return_value=[])), \
         patch("app.services.ingest_service.compile_multi_page", new=AsyncMock(return_value=mock_xml)):
        response = client_with_dirs.post(
            "/api/ingest/text",
            json={"text": "Texte sans titre."},
        )
    assert response.status_code == 200


def test_ingest_text_multi_page(client_with_dirs):
    wiki_tmp = settings.wiki_path
    Path(wiki_tmp, "imports").mkdir(parents=True, exist_ok=True)
    Path(wiki_tmp, "imports", "existing.md").write_text(
        "---\ntitle: Existing\n---\n\n## Résumé\n\nPage existante.\n",
        encoding="utf-8",
    )

    xml_two_pages = (
        f'<page slug="imports--test-ingestion">{MOCK_MARKDOWN}</page>\n'
        '<page slug="imports--existing">---\ntitle: Existing\n---\n\n## Résumé\n\nMis à jour.\n</page>'
    )
    with patch("app.services.ingest_service.identify_related_pages", new=AsyncMock(return_value=["imports--existing"])), \
         patch("app.services.ingest_service.compile_multi_page", new=AsyncMock(return_value=xml_two_pages)):
        response = client_with_dirs.post(
            "/api/ingest/text",
            json={"text": "Texte source.", "title": "Test Ingestion", "tags": []},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["pages_updated"] == ["imports--existing"]
    assert data["concepts_created"] == []
    assert data["entities_created"] == []
    assert Path(wiki_tmp, "index.md").exists()


def test_ingest_text_no_related(client_with_dirs):
    with patch("app.services.ingest_service.identify_related_pages", new=AsyncMock(return_value=[])), \
         patch("app.services.ingest_service.compile_multi_page", new=AsyncMock(return_value=MOCK_XML)):
        response = client_with_dirs.post(
            "/api/ingest/text",
            json={"text": "Texte source.", "title": "Test Ingestion", "tags": []},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["pages_updated"] == []
    assert data["concepts_created"] == []
    assert data["entities_created"] == []


def test_ingest_text_with_concepts(client_with_dirs):
    xml_with_concept = (
        f'<page slug="imports--test-ingestion">{MOCK_MARKDOWN}</page>\n'
        f'<page slug="concept--groove">{CONCEPT_MARKDOWN}</page>'
    )
    with patch("app.services.ingest_service.identify_related_pages", new=AsyncMock(return_value=[])), \
         patch("app.services.ingest_service.compile_multi_page", new=AsyncMock(return_value=xml_with_concept)):
        response = client_with_dirs.post(
            "/api/ingest/text",
            json={"text": "On utilise Groove pour les tickets.", "title": "Test Ingestion", "tags": ["test"]},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["concepts_created"] == ["concept--groove"]
    assert data["entities_created"] == []
    assert data["pages_updated"] == []
    assert Path(settings.wiki_path, "concept", "groove.md").exists()


def test_ingest_file_endpoint_txt(client_with_dirs):
    mock_xml = f'<page slug="imports--rapport">{MOCK_MARKDOWN}</page>'
    with patch("app.services.ingest_service.identify_related_pages", new=AsyncMock(return_value=[])), \
         patch("app.services.ingest_service.compile_multi_page", new=AsyncMock(return_value=mock_xml)):
        response = client_with_dirs.post(
            "/api/ingest/file",
            files={"file": ("rapport.txt", b"Contenu du fichier texte.", "text/plain")},
            data={"tags": "test"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "imports--rapport"
    assert data["title"] == "rapport"


def test_ingest_file_endpoint_with_title(client_with_dirs):
    mock_xml = f'<page slug="imports--mon-titre-custom">{MOCK_MARKDOWN}</page>'
    with patch("app.services.ingest_service.identify_related_pages", new=AsyncMock(return_value=[])), \
         patch("app.services.ingest_service.compile_multi_page", new=AsyncMock(return_value=mock_xml)):
        response = client_with_dirs.post(
            "/api/ingest/file",
            files={"file": ("doc.md", b"# Titre\n\nContenu.", "text/markdown")},
            data={"title": "Mon titre custom"},
        )
    assert response.status_code == 200
    assert response.json()["title"] == "Mon titre custom"


def test_ingest_file_endpoint_unsupported(client_with_dirs):
    response = client_with_dirs.post(
        "/api/ingest/file",
        files={"file": ("script.exe", b"data", "application/octet-stream")},
    )
    assert response.status_code == 415


def test_ingest_file_endpoint_empty_text(client_with_dirs):
    response = client_with_dirs.post(
        "/api/ingest/file",
        files={"file": ("vide.txt", b"   ", "text/plain")},
    )
    assert response.status_code == 422
    assert "extractible" in response.json()["detail"]


def test_ingest_file_endpoint_extract_error(client_with_dirs):
    with patch("app.api.ingest.extract_text", new=AsyncMock(side_effect=ValueError("PDF illisible"))):
        response = client_with_dirs.post(
            "/api/ingest/file",
            files={"file": ("broken.pdf", b"not a pdf", "application/pdf")},
        )
    assert response.status_code == 422
    assert "PDF illisible" in response.json()["detail"]
```

- [ ] **Step 4 : Lancer tous les tests backend**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend && source .venv/bin/activate && pytest tests/ -v 2>&1 | tail -15
```

Attendu : `54 passed` (50 existants + 2 load_log + 2 endpoint log). Si des tests échouent, corriger avant de continuer.

- [ ] **Step 5 : Commit**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm && git add backend/app/models/ingest.py backend/app/services/ingest_service.py backend/tests/test_ingest.py && git commit -m "feat: enrich ingest with duration, concept/entity categorization and enriched log"
```

---

## Task 4: Frontend

**Files:**
- Modify: `frontend/types/api.ts`
- Modify: `frontend/components/layout/AppSidebar.vue`
- Create: `frontend/pages/log.vue`
- Modify: `frontend/components/ingest/IngestText.vue`
- Modify: `frontend/components/ingest/IngestFile.vue`

- [ ] **Step 1 : Mettre à jour frontend/types/api.ts**

Remplacer l'interface `IngestResult` et ajouter `LogResponse` :

```typescript
export interface IngestResult {
  slug: string
  raw_path: string
  wiki_path: string
  title: string
  pages_updated: string[]
  concepts_created: string[]
  entities_created: string[]
}

export interface LogResponse {
  content: string
}
```

Le reste du fichier reste identique.

- [ ] **Step 2 : Ajouter le lien Journal dans AppSidebar.vue**

Dans `frontend/components/layout/AppSidebar.vue` :

1. Ajouter `ScrollText` à l'import lucide :

```typescript
import { BookOpen, MessageSquare, Library, Upload, PanelLeft, ScrollText } from 'lucide-vue-next'
```

2. Ajouter `{ to: '/log', icon: ScrollText, label: 'Journal' }` entre Wiki et Ingest dans `navItems` :

```typescript
const navItems = [
  { to: '/chat', icon: MessageSquare, label: 'Chat' },
  { to: '/wiki', icon: Library, label: 'Wiki' },
  { to: '/log', icon: ScrollText, label: 'Journal' },
  { to: '/ingest', icon: Upload, label: 'Ingest' },
]
```

- [ ] **Step 3 : Créer frontend/pages/log.vue**

```vue
<template>
  <div class="max-w-3xl mx-auto py-8 px-4">
    <h1 class="text-xl font-semibold text-white mb-6">Journal des ingestions</h1>
    <div v-if="loading" class="text-gray-400 text-sm">Chargement...</div>
    <div v-else-if="!content" class="text-gray-500 text-sm italic">
      Aucune ingestion enregistrée.
    </div>
    <MarkdownViewer v-else :content="content" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import MarkdownViewer from '~/components/wiki/MarkdownViewer.vue'
import { useApi } from '~/composables/useApi'
import type { LogResponse } from '~/types/api'

const { get } = useApi()
const content = ref('')
const loading = ref(true)

onMounted(async () => {
  try {
    const data = await get<LogResponse>('/api/wiki/log')
    content.value = data.content
  } finally {
    loading.value = false
  }
})
</script>
```

- [ ] **Step 4 : Mettre à jour IngestText.vue**

Dans le bloc résultat (après `<p v-for="s in result.pages_updated" ...>`), ajouter :

```html
<p v-for="s in result.concepts_created" :key="s" class="text-purple-300 text-xs">+ {{ s }}</p>
<p v-for="s in result.entities_created" :key="s" class="text-yellow-300 text-xs">+ {{ s }}</p>
```

Le bloc résultat complet devient :

```html
<div v-if="result" class="p-3 bg-green-900/30 border border-green-700 rounded-lg space-y-1">
  <p class="text-green-400 text-sm font-medium">✓ {{ result.slug }} créé</p>
  <p v-for="s in result.pages_updated" :key="s" class="text-blue-300 text-xs">↻ {{ s }} mis à jour</p>
  <p v-for="s in result.concepts_created" :key="s" class="text-purple-300 text-xs">+ {{ s }}</p>
  <p v-for="s in result.entities_created" :key="s" class="text-yellow-300 text-xs">+ {{ s }}</p>
  <NuxtLink :to="`/wiki/${result.slug}`" class="text-blue-400 text-xs hover:underline">
    Voir la page →
  </NuxtLink>
</div>
```

- [ ] **Step 5 : Mettre à jour IngestFile.vue**

1. Ajouter `conceptsCreated` et `entitiesCreated` à l'interface `FileEntry` :

```typescript
interface FileEntry {
  file: File
  status: 'pending' | 'processing' | 'done' | 'error'
  slug?: string
  pagesUpdated?: string[]
  conceptsCreated?: string[]
  entitiesCreated?: string[]
  error?: string
}
```

2. Après `entry.pagesUpdated = result.pages_updated` dans `ingestAll()`, ajouter :

```typescript
entry.conceptsCreated = result.concepts_created
entry.entitiesCreated = result.entities_created
```

3. Dans le template, dans le bloc `v-else-if="entry.status === 'done'"`, après les lignes `pagesUpdated`, ajouter :

```html
<span v-for="s in entry.conceptsCreated" :key="s" class="block text-xs text-purple-300 mt-0.5">+ {{ s }}</span>
<span v-for="s in entry.entitiesCreated" :key="s" class="block text-xs text-yellow-300 mt-0.5">+ {{ s }}</span>
```

Le bloc `done` complet devient :

```html
<span v-else-if="entry.status === 'done'" class="text-green-400">
  <span>✓ <NuxtLink :to="`/wiki/${entry.slug}`" class="underline hover:text-white">{{ entry.slug }}</NuxtLink></span>
  <span v-for="s in entry.pagesUpdated" :key="s" class="block text-xs text-blue-300 mt-0.5">↻ {{ s }}</span>
  <span v-for="s in entry.conceptsCreated" :key="s" class="block text-xs text-purple-300 mt-0.5">+ {{ s }}</span>
  <span v-for="s in entry.entitiesCreated" :key="s" class="block text-xs text-yellow-300 mt-0.5">+ {{ s }}</span>
</span>
```

- [ ] **Step 6 : Vérifier la compilation TypeScript**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/frontend && npx nuxi typecheck 2>&1 | grep -E "ERROR|error TS" | head -10
```

Attendu : aucune erreur dans les fichiers modifiés.

- [ ] **Step 7 : Commit**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm && git add frontend/types/api.ts frontend/components/layout/AppSidebar.vue frontend/pages/log.vue frontend/components/ingest/IngestText.vue frontend/components/ingest/IngestFile.vue && git commit -m "feat: add /log page and display concepts/entities in ingest UI"
```

---

## Vérification finale

- [ ] Lancer la suite complète des tests backend :

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend && source .venv/bin/activate && pytest tests/ -v 2>&1 | tail -5
```

Attendu : `54 passed`

- [ ] Vérifier les imports Python :

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend && source .venv/bin/activate && python -c "
from app.services.wiki_manager import load_log
from app.models.log import LogResponse
from app.api.log import router
from app.services.ingest_service import ingest_text
print('OK')
"
```

Attendu : `OK`
