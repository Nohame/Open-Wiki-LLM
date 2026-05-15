# Karpathy Pattern — Ingest Multi-Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transformer l'ingest de "1 doc → 1 page wiki" en "1 doc → N pages mises à jour" via 2 appels Ollama, avec `wiki/schema.md`, `wiki/index.md`, `wiki/log.md` maintenus automatiquement.

**Architecture:** `wiki_manager.py` et `schema_service.py` gèrent toutes les opérations multi-fichiers. Deux nouvelles fonctions async dans `ollama_service.py` (identifier pages liées + générer XML multi-pages). `ingest_service.py` orchestre le flux en 10 étapes.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, pytest, Nuxt 3, Vue 3, TypeScript, httpx, re

---

## Fichiers touchés

| Statut | Fichier |
|--------|---------|
| Créer | `backend/app/services/wiki_manager.py` |
| Créer | `backend/app/services/schema_service.py` |
| Créer | `backend/tests/test_wiki_manager.py` |
| Créer | `backend/tests/test_schema_service.py` |
| Modifier | `backend/app/services/ollama_service.py` |
| Modifier | `backend/app/services/ingest_service.py` |
| Modifier | `backend/app/models/ingest.py` |
| Modifier | `backend/tests/test_ingest.py` |
| Modifier | `frontend/types/api.ts` |
| Modifier | `frontend/components/ingest/IngestText.vue` |
| Modifier | `frontend/components/ingest/IngestFile.vue` |

---

## Task 1: wiki_manager.py

**Files:**
- Create: `backend/app/services/wiki_manager.py`
- Test: `backend/tests/test_wiki_manager.py`

- [ ] **Step 1 : Écrire les tests (test_wiki_manager.py)**

Créer `backend/tests/test_wiki_manager.py` :

```python
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
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
cd backend && python -m pytest tests/test_wiki_manager.py -v 2>&1 | head -30
```

Attendu : `ModuleNotFoundError` ou `ImportError` (le module n'existe pas encore).

- [ ] **Step 3 : Implémenter wiki_manager.py**

Créer `backend/app/services/wiki_manager.py` :

```python
import re
from pathlib import Path
from ..core.config import settings


def _slug_to_path(slug: str) -> Path:
    if "--" in slug:
        folder, name = slug.split("--", 1)
        return Path(settings.wiki_path) / folder / f"{name}.md"
    return Path(settings.wiki_path) / f"{slug}.md"


def load_index() -> str:
    index_path = Path(settings.wiki_path) / "index.md"
    if not index_path.exists():
        return ""
    return index_path.read_text()


def load_pages(slugs: list[str]) -> dict[str, str]:
    result = {}
    for slug in slugs:
        path = _slug_to_path(slug)
        if path.exists():
            result[slug] = path.read_text()
    return result


def parse_xml_updates(xml: str) -> dict[str, str]:
    pattern = re.compile(r'<page\s+slug="([^"]+)">(.*?)</page>', re.DOTALL)
    matches = pattern.findall(xml)
    if not matches:
        raise ValueError("Aucune balise <page> trouvée dans la réponse XML")
    return {slug: content.strip() for slug, content in matches}


def apply_updates(updates: dict[str, str]) -> list[str]:
    written = []
    for slug, content in updates.items():
        path = _slug_to_path(slug)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        written.append(slug)
    return written


def rebuild_index_file() -> None:
    wiki_root = Path(settings.wiki_path)
    categories: dict[str, list[tuple[str, str, str]]] = {}

    for md_file in sorted(wiki_root.rglob("*.md")):
        if md_file.name in ("index.md", "log.md", "schema.md"):
            continue
        rel = md_file.relative_to(wiki_root)
        parts = rel.parts
        category = parts[0] if len(parts) > 1 else "root"
        name = md_file.stem
        slug = f"{parts[0]}--{name}" if len(parts) > 1 else name

        text = md_file.read_text()
        title = _extract_frontmatter_title(text) or name
        summary = _extract_resume_first_line(text) or ""
        categories.setdefault(category, []).append((slug, title, summary))

    lines = [
        "# Index du wiki",
        "",
        "<!-- Mis à jour automatiquement — ne pas modifier manuellement -->",
    ]
    for category, pages in sorted(categories.items()):
        lines.append(f"\n## {category}\n")
        lines.append("| Page | Résumé |")
        lines.append("|------|--------|")
        for slug, title, summary in pages:
            path_ref = slug.replace("--", "/")
            lines.append(f"| [{slug}]({path_ref}.md) | {summary} |")

    (wiki_root / "index.md").write_text("\n".join(lines) + "\n")


def append_log(entry: str) -> None:
    log_path = Path(settings.wiki_path) / "log.md"
    header = "# Journal des ingestions\n\n"
    if log_path.exists():
        existing = log_path.read_text()
        if existing.startswith("# Journal des ingestions"):
            existing = existing[len("# Journal des ingestions"):].lstrip("\n")
        log_path.write_text(header + entry + "\n" + existing)
    else:
        log_path.write_text(header + entry + "\n")


def _extract_frontmatter_title(text: str) -> str | None:
    match = re.search(r"^title:\s*(.+)$", text, re.MULTILINE)
    if match:
        return match.group(1).strip().strip('"').strip("'")
    return None


def _extract_resume_first_line(text: str) -> str | None:
    match = re.search(r"##\s+Résumé\s*\n+(.*?)(?:\n\n|\n##|\Z)", text, re.DOTALL)
    if match:
        content = match.group(1).strip()
        if not content:
            return ""
        return content.splitlines()[0][:100]
    return None
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
cd backend && python -m pytest tests/test_wiki_manager.py -v
```

Attendu : `11 passed`

- [ ] **Step 5 : Commit**

```bash
git add backend/app/services/wiki_manager.py backend/tests/test_wiki_manager.py
git commit -m "feat: add wiki_manager service with multi-file wiki operations"
```

---

## Task 2: schema_service.py

**Files:**
- Create: `backend/app/services/schema_service.py`
- Test: `backend/tests/test_schema_service.py`

- [ ] **Step 1 : Écrire les tests**

Créer `backend/tests/test_schema_service.py` :

```python
def test_load_or_create_creates_default(tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "wiki_path", str(tmp_path))
    from app.services.schema_service import load_or_create, DEFAULT_SCHEMA

    result = load_or_create()

    assert result == DEFAULT_SCHEMA
    schema_file = tmp_path / "schema.md"
    assert schema_file.exists()
    assert schema_file.read_text() == DEFAULT_SCHEMA


def test_load_or_create_reads_existing(tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "wiki_path", str(tmp_path))
    (tmp_path / "schema.md").write_text("# Custom schema")
    from app.services.schema_service import load_or_create

    result = load_or_create()

    assert result == "# Custom schema"
    assert (tmp_path / "schema.md").read_text() == "# Custom schema"
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
cd backend && python -m pytest tests/test_schema_service.py -v 2>&1 | head -20
```

Attendu : `ModuleNotFoundError`

- [ ] **Step 3 : Implémenter schema_service.py**

Créer `backend/app/services/schema_service.py` :

```python
from pathlib import Path
from ..core.config import settings

DEFAULT_SCHEMA = """\
# Wiki Schema

## Format des pages

Frontmatter YAML obligatoire : title, type, status, confidence, sources, updated_at, tags
Sections standard : ## Résumé / ## Règles connues / ## Liens liés / ## Points à confirmer

## Types de pages

- `concept` : notion, règle, procédure métier
- `entity` : personne, fournisseur, outil, système
- `source` : résumé structuré d'un document source

## Conventions

- Cross-références entre pages : [[slug-de-la-page]]
- Slugs : minuscules, tirets, pas de caractères spéciaux
- status: draft = créé automatiquement / status: validated = relu manuellement
- Une page par concept ou entité distincte
"""


def load_or_create() -> str:
    schema_path = Path(settings.wiki_path) / "schema.md"
    if schema_path.exists():
        return schema_path.read_text()
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.write_text(DEFAULT_SCHEMA)
    return DEFAULT_SCHEMA
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
cd backend && python -m pytest tests/test_schema_service.py -v
```

Attendu : `2 passed`

- [ ] **Step 5 : Commit**

```bash
git add backend/app/services/schema_service.py backend/tests/test_schema_service.py
git commit -m "feat: add schema_service with default wiki schema"
```

---

## Task 3: ollama_service.py — nouveaux prompts et fonctions

**Files:**
- Modify: `backend/app/services/ollama_service.py`

- [ ] **Step 1 : Ajouter les deux prompts en bas des constantes**

Dans `backend/app/services/ollama_service.py`, après la constante `IMAGE_PROMPT` (ligne ~69), ajouter :

```python
IDENTIFY_RELATED_PROMPT = """\
Tu analyses un nouveau document pour identifier quelles pages wiki existantes
pourraient être liées ou nécessiter une mise à jour.

Titre du document : {title}

Document :
{text}

Index actuel du wiki :
{index}

Liste les slugs des pages wiki à charger (maximum 10).
Réponds UNIQUEMENT avec un JSON valide : ["slug1", "slug2"]
Si aucune page n'est liée, réponds : []
"""

MULTI_UPDATE_PROMPT = """\
Tu maintiens un wiki selon ce schéma :
{schema}

Nouveau document à intégrer :
Titre : {title} | Tags : {tags} | Date : {date}
{text}

Pages wiki existantes liées :
{related_pages}

Génère toutes les mises à jour nécessaires.
Pour chaque page à créer ou modifier, utilise ce format EXACT :

<page slug="{new_slug}">
[contenu complet de la page en Markdown avec frontmatter]
</page>

Règles :
- Crée une page pour le document source (slug : {new_slug})
- Mets à jour les pages liées : nouvelles informations, corrections, cross-refs [[slug]]
- N'inclus QUE les pages qui changent réellement
- Réponds UNIQUEMENT avec les balises <page>, sans commentaire
"""
```

- [ ] **Step 2 : Ajouter les deux fonctions async à la fin du fichier**

À la fin de `backend/app/services/ollama_service.py`, ajouter :

```python
async def identify_related_pages(text: str, title: str, index_content: str) -> list[str]:
    prompt = IDENTIFY_RELATED_PROMPT.format(
        title=title,
        text=text,
        index=index_content or "(index vide)",
    )
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/generate",
            json={"model": settings.ollama_model, "prompt": prompt, "stream": False},
        )
        response.raise_for_status()
        raw = response.json()["response"].strip()
    try:
        slugs = json.loads(raw)
        if isinstance(slugs, list):
            return [s for s in slugs if isinstance(s, str)]
    except (json.JSONDecodeError, ValueError):
        pass
    return []


async def compile_multi_page(
    text: str,
    title: str,
    tags: list[str],
    date: str,
    schema: str,
    related_pages: dict[str, str],
    new_slug: str,
) -> str:
    pages_block = (
        "\n\n".join(f"=== {slug} ===\n{content}" for slug, content in related_pages.items())
        if related_pages
        else "(aucune page liée)"
    )
    prompt = MULTI_UPDATE_PROMPT.format(
        schema=schema,
        title=title,
        tags=json.dumps(tags, ensure_ascii=False),
        date=date,
        text=text,
        related_pages=pages_block,
        new_slug=new_slug,
    )
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/generate",
            json={"model": settings.ollama_model, "prompt": prompt, "stream": False},
        )
        response.raise_for_status()
        return response.json()["response"]
```

- [ ] **Step 3 : Vérifier l'import et la syntaxe**

```bash
cd backend && python -c "from app.services.ollama_service import identify_related_pages, compile_multi_page; print('OK')"
```

Attendu : `OK`

- [ ] **Step 4 : Commit**

```bash
git add backend/app/services/ollama_service.py
git commit -m "feat: add identify_related_pages and compile_multi_page to ollama_service"
```

---

## Task 4: ingest_service.py + models/ingest.py + test_ingest.py

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
```

- [ ] **Step 2 : Réécrire ingest_service.py**

Remplacer le contenu de `backend/app/services/ingest_service.py` :

```python
import re
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
    today = date.today().isoformat()
    effective_title = title or "Source sans titre"
    slug = _slugify(effective_title)
    new_slug = f"imports--{slug}"

    raw_path = Path(settings.raw_path) / "imports" / f"{slug}.md"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(text)

    schema = schema_service.load_or_create()
    index_content = wiki_manager.load_index()

    related_slugs = await identify_related_pages(text, effective_title, index_content)
    related_pages = wiki_manager.load_pages(related_slugs)

    xml_output = await compile_multi_page(
        text, effective_title, tags, today, schema, related_pages, new_slug
    )

    updates = wiki_manager.parse_xml_updates(xml_output)
    written_slugs = wiki_manager.apply_updates(updates)

    wiki_manager.rebuild_index_file()
    pages_updated = [s for s in written_slugs if s != new_slug]
    wiki_manager.append_log(
        f"## [{today}] ingest | {slug}\n"
        f"- Pages créées : {new_slug}\n"
        f"- Pages mises à jour : {', '.join(pages_updated) or '—'}\n"
    )

    rebuild_index()

    wiki_path = Path(settings.wiki_path) / "imports" / f"{slug}.md"
    return {
        "slug": new_slug,
        "raw_path": str(raw_path),
        "wiki_path": str(wiki_path),
        "title": effective_title,
        "pages_updated": pages_updated,
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
    wiki_path.write_text(markdown)

    return {
        "slug": f"imports--{slug}",
        "raw_path": str(raw_path),
        "wiki_path": str(wiki_path),
        "title": effective_title,
        "pages_updated": [],
    }
```

- [ ] **Step 3 : Mettre à jour test_ingest.py**

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
MOCK_XML_RAPPORT = f'<page slug="imports--rapport">{MOCK_MARKDOWN}</page>'


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
        "---\ntitle: Existing\n---\n\n## Résumé\n\nPage existante.\n"
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
cd backend && python -m pytest tests/ -v
```

Attendu : tous les tests passent (aucun FAILED). Si des tests échouent, corriger avant de continuer.

- [ ] **Step 5 : Commit**

```bash
git add backend/app/models/ingest.py backend/app/services/ingest_service.py backend/tests/test_ingest.py
git commit -m "feat: implement karpathy multi-page ingest flow (2 LLM calls)"
```

---

## Task 5: Frontend

**Files:**
- Modify: `frontend/types/api.ts`
- Modify: `frontend/components/ingest/IngestText.vue`
- Modify: `frontend/components/ingest/IngestFile.vue`

- [ ] **Step 1 : Mettre à jour frontend/types/api.ts**

Dans `frontend/types/api.ts`, remplacer l'interface `IngestResult` :

```typescript
export interface IngestResult {
  slug: string
  raw_path: string
  wiki_path: string
  title: string
  pages_updated: string[]
}
```

- [ ] **Step 2 : Mettre à jour IngestText.vue**

Remplacer le contenu de `frontend/components/ingest/IngestText.vue` :

```vue
<template>
  <form class="space-y-4" @submit.prevent="handleSubmit">
    <div class="space-y-1">
      <label class="block text-sm text-gray-300">Titre <span class="text-red-400">*</span></label>
      <input
        v-model="title"
        type="text"
        required
        placeholder="Titre de la page wiki"
        class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500"
      />
    </div>

    <div class="space-y-1">
      <label class="block text-sm text-gray-300">Tags <span class="text-gray-500">(séparés par virgule)</span></label>
      <input
        v-model="tagsInput"
        type="text"
        placeholder="livraison, logistique"
        class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500"
      />
    </div>

    <div class="space-y-1">
      <label class="block text-sm text-gray-300">Contenu <span class="text-red-400">*</span></label>
      <textarea
        v-model="text"
        required
        rows="8"
        placeholder="Colle le texte brut à structurer..."
        class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500 resize-y"
      />
    </div>

    <p v-if="error" class="text-red-400 text-sm">{{ error }}</p>

    <div v-if="result" class="p-3 bg-green-900/30 border border-green-700 rounded-lg space-y-1">
      <p class="text-green-400 text-sm font-medium">✓ {{ result.slug }} créé</p>
      <p v-for="s in result.pages_updated" :key="s" class="text-blue-300 text-xs">↻ {{ s }} mis à jour</p>
      <NuxtLink :to="`/wiki/${result.slug}`" class="text-blue-400 text-xs hover:underline">
        Voir la page →
      </NuxtLink>
    </div>

    <button
      type="submit"
      :disabled="loading"
      class="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
    >
      {{ loadingLabel }}
    </button>
  </form>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'

const { result, loading, error, ingestText, reset } = useIngest()

const title = ref('')
const tagsInput = ref('')
const text = ref('')
const phase = ref<'analyse' | 'compilation'>('analyse')
let phaseTimer: ReturnType<typeof setTimeout> | null = null

const loadingLabel = computed(() => {
  if (!loading.value) return 'Ingérer →'
  return phase.value === 'analyse' ? 'Analyse des pages liées...' : 'Compilation du wiki...'
})

onUnmounted(() => {
  if (phaseTimer) clearTimeout(phaseTimer)
})

async function handleSubmit() {
  reset()
  phase.value = 'analyse'
  phaseTimer = setTimeout(() => { phase.value = 'compilation' }, 8000)
  const tags = tagsInput.value.split(',').map((t) => t.trim()).filter(Boolean)
  await ingestText(text.value, title.value, tags)
  if (phaseTimer) { clearTimeout(phaseTimer); phaseTimer = null }
  if (result.value) {
    title.value = ''
    tagsInput.value = ''
    text.value = ''
  }
}
</script>
```

- [ ] **Step 3 : Mettre à jour IngestFile.vue**

Remplacer le contenu de `frontend/components/ingest/IngestFile.vue` :

```vue
<template>
  <div class="space-y-4">
    <div
      class="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors"
      :class="isDragging ? 'border-blue-500 bg-blue-950/20' : 'border-gray-700 hover:border-gray-600'"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="onDragLeave"
      @drop.prevent="onDrop"
      @click="fileInput?.click()"
    >
      <FolderOpen class="mx-auto w-8 h-8 text-gray-500 mb-2" />
      <p class="text-sm text-gray-400">
        Glissez des fichiers ici ou
        <span class="text-blue-400">cliquez pour sélectionner</span>
      </p>
      <p class="text-xs text-gray-600 mt-1">.md .txt .pdf .docx — max 10 Mo</p>
      <input
        ref="fileInput"
        type="file"
        multiple
        accept=".md,.txt,.pdf,.docx"
        class="hidden"
        @change="onFileInput"
      />
    </div>

    <div>
      <label class="block text-sm text-gray-400 mb-1">Tags (appliqués à tous les fichiers)</label>
      <input
        v-model="tagsInput"
        type="text"
        placeholder="tag1, tag2"
        class="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500"
        :disabled="isProcessing"
      />
    </div>

    <ul v-if="entries.length" class="space-y-2">
      <li
        v-for="entry in entries"
        :key="entry.file.name"
        class="flex items-start justify-between text-sm rounded px-3 py-2 bg-gray-900"
      >
        <span class="text-gray-300 truncate max-w-xs mt-0.5">{{ entry.file.name }}</span>
        <span class="ml-4 shrink-0 text-right">
          <span v-if="entry.status === 'pending'" class="text-gray-500">en attente</span>
          <span v-else-if="entry.status === 'processing'" class="text-blue-400 animate-pulse">
            {{ processingPhase === 'analyse' ? 'Analyse des pages liées...' : 'Compilation du wiki...' }}
          </span>
          <span v-else-if="entry.status === 'done'" class="text-green-400">
            <span>✓ <NuxtLink :to="`/wiki/${entry.slug}`" class="underline hover:text-white">{{ entry.slug }}</NuxtLink></span>
            <span v-for="s in entry.pagesUpdated" :key="s" class="block text-xs text-blue-300 mt-0.5">↻ {{ s }}</span>
          </span>
          <span v-else class="text-red-400">✗ {{ entry.error }}</span>
        </span>
      </li>
    </ul>

    <div v-if="rejectedMessage" class="text-sm text-yellow-400 bg-yellow-950/30 rounded px-3 py-2">
      {{ rejectedMessage }}
    </div>

    <div class="flex gap-2">
      <button
        :disabled="!entries.length || isProcessing"
        class="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-white font-medium"
        @click="ingestAll"
      >
        Tout ingérer →
      </button>
      <button
        :disabled="isProcessing"
        class="px-4 py-2 text-sm bg-gray-800 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-white"
        @click="clearAll"
      >
        Effacer
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import { FolderOpen } from 'lucide-vue-next'
import { useIngest } from '~/composables/useIngest'

interface FileEntry {
  file: File
  status: 'pending' | 'processing' | 'done' | 'error'
  slug?: string
  pagesUpdated?: string[]
  error?: string
}

const ALLOWED_EXTS = new Set(['.md', '.txt', '.pdf', '.docx'])
const MAX_SIZE = 10 * 1024 * 1024

const fileInput = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const tagsInput = ref('')
const entries = ref<FileEntry[]>([])
const rejectedMessage = ref('')
const processingPhase = ref<'analyse' | 'compilation'>('analyse')
let phaseTimer: ReturnType<typeof setTimeout> | null = null

const isProcessing = computed(() => entries.value.some((e) => e.status === 'processing'))

const { ingestFile } = useIngest()

onUnmounted(() => {
  if (phaseTimer) clearTimeout(phaseTimer)
})

function addFiles(files: FileList | File[]) {
  const rejected: string[] = []
  for (const file of Array.from(files)) {
    const ext = '.' + (file.name.split('.').pop() ?? '').toLowerCase()
    if (!ALLOWED_EXTS.has(ext)) {
      rejected.push(`${file.name} (format non supporté)`)
      continue
    }
    if (file.size > MAX_SIZE) {
      rejected.push(`${file.name} (> 10 Mo)`)
      continue
    }
    if (!entries.value.some((e) => e.file.name === file.name && e.status !== 'error')) {
      entries.value.push({ file, status: 'pending' })
    }
  }
  rejectedMessage.value = rejected.length ? `Fichiers rejetés : ${rejected.join(', ')}` : ''
}

function onDrop(e: DragEvent) {
  isDragging.value = false
  if (e.dataTransfer?.files) addFiles(e.dataTransfer.files)
}

function onDragLeave(e: DragEvent) {
  if (!(e.currentTarget as Element).contains(e.relatedTarget as Node | null)) {
    isDragging.value = false
  }
}

function onFileInput(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files) addFiles(input.files)
  input.value = ''
}

async function ingestAll() {
  if (isProcessing.value) return
  rejectedMessage.value = ''
  const tags = tagsInput.value.split(',').map((t) => t.trim()).filter(Boolean)
  for (const entry of entries.value) {
    if (entry.status !== 'pending') continue
    entry.status = 'processing'
    processingPhase.value = 'analyse'
    phaseTimer = setTimeout(() => { processingPhase.value = 'compilation' }, 8000)
    try {
      const result = await ingestFile(entry.file, tags)
      if (phaseTimer) { clearTimeout(phaseTimer); phaseTimer = null }
      entry.status = 'done'
      entry.slug = result.slug
      entry.pagesUpdated = result.pages_updated
    } catch (err: unknown) {
      if (phaseTimer) { clearTimeout(phaseTimer); phaseTimer = null }
      entry.status = 'error'
      entry.error = err instanceof Error ? err.message : 'Erreur inconnue'
    }
  }
}

function clearAll() {
  if (!isProcessing.value) {
    entries.value = []
    rejectedMessage.value = ''
  }
}
</script>
```

- [ ] **Step 4 : Vérifier la compilation TypeScript**

```bash
cd frontend && npx nuxi typecheck 2>&1 | tail -20
```

Attendu : aucune erreur TypeScript sur les fichiers modifiés.

- [ ] **Step 5 : Commit**

```bash
git add frontend/types/api.ts frontend/components/ingest/IngestText.vue frontend/components/ingest/IngestFile.vue
git commit -m "feat: display pages_updated and loading phases in ingest UI"
```

---

## Vérification finale

- [ ] Lancer la suite complète des tests backend :

```bash
cd backend && python -m pytest tests/ -v
```

Attendu : tous les tests passent.

- [ ] Vérifier l'import de tous les nouveaux modules :

```bash
cd backend && python -c "
from app.services.wiki_manager import load_index, load_pages, parse_xml_updates, apply_updates, rebuild_index_file, append_log
from app.services.schema_service import load_or_create
from app.services.ollama_service import identify_related_pages, compile_multi_page
from app.services.ingest_service import ingest_text
print('Tous les imports OK')
"
```

Attendu : `Tous les imports OK`
