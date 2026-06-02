# MCP wiki_guide / wiki_write / wiki_delete — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter trois outils MCP (`wiki_guide`, `wiki_write`, `wiki_delete`) au serveur OpenWikiLLM avec le préfixe `wiki_`.

**Architecture:** `wiki_manager.set_deprecated()` est ajouté en miroir de `set_stale()`. Les trois outils sont déclarés dans `mcp/server.py` et appellent les services existants. `wiki_write` rebuilde l'index FTS5 et le graphe de références après chaque écriture pour maintenir la cohérence du système.

**Tech Stack:** Python 3.11, FastAPI, FastMCP 3.x, python-frontmatter, SQLite FTS5, pytest

---

## File Map

| Fichier | Action |
|---|---|
| `backend/app/services/wiki_manager.py` | Modifier — ajouter `set_deprecated(slug)` |
| `backend/app/mcp/server.py` | Modifier — ajouter 3 imports + 3 outils |
| `backend/tests/test_mcp_tools.py` | Modifier — ajouter 7 tests |

---

## Task 1 : `set_deprecated` dans wiki_manager

**Files:**
- Modify: `backend/app/services/wiki_manager.py`
- Test: `backend/tests/test_stale_wiki_manager.py` (fichier existant, même pattern)

- [ ] **Step 1 : Écrire le test échouant**

Ouvrir `backend/tests/test_stale_wiki_manager.py` et ajouter à la fin :

```python
def test_set_deprecated_marks_status(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "wiki_path", str(tmp_path))
    p = tmp_path / "concept" / "old.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("---\ntitle: Old\nstatus: draft\n---\n\n# Old\n", encoding="utf-8")
    from app.services.wiki_manager import set_deprecated
    result = set_deprecated("concept--old")
    assert result is True
    post = fm.load(str(p))
    assert post.metadata["status"] == "deprecated"


def test_set_deprecated_unknown_slug_returns_false(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "wiki_path", str(tmp_path))
    from app.services.wiki_manager import set_deprecated
    result = set_deprecated("concept--unknown")
    assert result is False
```

S'assurer que `import frontmatter as fm` est présent en tête du fichier (il l'est déjà).

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
cd backend && python -m pytest tests/test_stale_wiki_manager.py::test_set_deprecated_marks_status tests/test_stale_wiki_manager.py::test_set_deprecated_unknown_slug_returns_false -v
```

Expected: `FAILED` avec `ImportError: cannot import name 'set_deprecated'`

- [ ] **Step 3 : Implémenter `set_deprecated` dans wiki_manager**

Ouvrir `backend/app/services/wiki_manager.py`. Après la fonction `set_stale` (ligne ~29), ajouter :

```python
def set_deprecated(slug: str) -> bool:
    path = _slug_to_path(slug)
    if not path.exists():
        logger.warning("set_deprecated: slug introuvable : %s", slug)
        return False
    try:
        post = fm.load(str(path))
    except Exception:
        logger.warning("set_deprecated: frontmatter malformé pour %s", slug)
        return False
    post.metadata["status"] = "deprecated"
    path.write_text(fm.dumps(post), encoding="utf-8")
    return True
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
cd backend && python -m pytest tests/test_stale_wiki_manager.py -v
```

Expected: tous les tests `PASSED`

- [ ] **Step 5 : Commit**

```bash
git add backend/app/services/wiki_manager.py backend/tests/test_stale_wiki_manager.py
git commit -m "feat(wiki_manager): add set_deprecated function"
```

---

## Task 2 : `wiki_guide` — outil MCP

**Files:**
- Modify: `backend/app/mcp/server.py`
- Test: `backend/tests/test_mcp_tools.py`

- [ ] **Step 1 : Écrire les tests échouants**

Ouvrir `backend/tests/test_mcp_tools.py`. Ajouter les tests à la fin du fichier (les imports se font inline comme pour `wiki_list_stale` et `wiki_list_references`) :

```python
def test_wiki_guide_empty(wiki_env):
    from app.mcp.server import wiki_guide
    result = wiki_guide()
    assert result == ""


def test_wiki_guide_returns_index_content(wiki_env):
    from app.mcp.server import wiki_guide
    index_path = Path(settings.wiki_path) / "index.md"
    index_path.write_text("# Index du wiki\n\n## concept\n", encoding="utf-8")
    result = wiki_guide()
    assert "# Index du wiki" in result
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
cd backend && python -m pytest tests/test_mcp_tools.py::test_wiki_guide_empty tests/test_mcp_tools.py::test_wiki_guide_returns_index_content -v
```

Expected: `FAILED` avec `ImportError: cannot import name 'wiki_guide'`

- [ ] **Step 3 : Implémenter `wiki_guide` dans server.py**

Ouvrir `backend/app/mcp/server.py`. Ajouter l'import de `wiki_manager` en tête (après les imports existants) :

```python
from ..services import wiki_manager
```

Puis ajouter l'outil à la fin du fichier :

```python
@mcp.tool()
def wiki_guide() -> str:
    """Retourne l'index structuré du wiki : catégories, slugs disponibles et résumés."""
    return wiki_manager.load_index()
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
cd backend && python -m pytest tests/test_mcp_tools.py::test_wiki_guide_empty tests/test_mcp_tools.py::test_wiki_guide_returns_index_content -v
```

Expected: `PASSED`

- [ ] **Step 5 : Commit**

```bash
git add backend/app/mcp/server.py backend/tests/test_mcp_tools.py
git commit -m "feat(mcp): add wiki_guide tool"
```

---

## Task 3 : `wiki_write` — outil MCP

**Files:**
- Modify: `backend/app/mcp/server.py`
- Test: `backend/tests/test_mcp_tools.py`

- [ ] **Step 1 : Écrire les tests échouants**

Ajouter dans `backend/tests/test_mcp_tools.py` :

```python
def test_wiki_write_creates_new_page(wiki_env):
    from app.mcp.server import wiki_write
    result = wiki_write(
        slug="imports--test-write",
        title="Test Write",
        content="## Résumé\n\nContenu créé par agent.",
        type="concept",
        status="draft",
        tags=["test"],
        confidence="medium",
    )
    assert result == {"slug": "imports--test-write", "written": True}
    page_path = Path(settings.wiki_path) / "imports" / "test-write.md"
    assert page_path.exists()
    post = fm.load(str(page_path))
    assert post.metadata["title"] == "Test Write"
    assert post.metadata["status"] == "draft"
    assert post.metadata["tags"] == ["test"]
    assert "Contenu créé par agent" in post.content


def test_wiki_write_updates_existing_page(wiki_env):
    existing = Path(settings.wiki_path) / "imports"
    existing.mkdir(parents=True, exist_ok=True)
    (existing / "existing.md").write_text(
        "---\ntitle: Ancien Titre\nstatus: draft\n---\n\n# Ancien\n",
        encoding="utf-8",
    )
    from app.mcp.server import wiki_write
    result = wiki_write(
        slug="imports--existing",
        title="Nouveau Titre",
        content="## Résumé\n\nContenu mis à jour.",
    )
    assert result["written"] is True
    post = fm.load(str(existing / "existing.md"))
    assert post.metadata["title"] == "Nouveau Titre"
    assert "mis à jour" in post.content
```

S'assurer que `import frontmatter as fm` est présent en tête de `test_mcp_tools.py` (il l'est déjà).

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
cd backend && python -m pytest tests/test_mcp_tools.py::test_wiki_write_creates_new_page tests/test_mcp_tools.py::test_wiki_write_updates_existing_page -v
```

Expected: `FAILED` avec `ImportError: cannot import name 'wiki_write'`

- [ ] **Step 3 : Implémenter `wiki_write` dans server.py**

Ajouter en tête de `backend/app/mcp/server.py` (après les imports existants) :

```python
from datetime import date
import frontmatter as fm
```

Puis ajouter l'outil à la fin du fichier :

```python
@mcp.tool()
def wiki_write(
    slug: str,
    title: str,
    content: str,
    type: str = "concept",
    status: str = "draft",
    tags: list[str] | None = None,
    confidence: str = "medium",
) -> dict:
    """Crée ou met à jour une page wiki. Le backend assemble le frontmatter YAML automatiquement."""
    post = fm.Post(
        content,
        title=title,
        type=type,
        status=status,
        confidence=confidence,
        tags=tags or [],
        sources=[],
        updated_at=date.today().isoformat(),
    )
    wiki_manager.apply_updates({slug: fm.dumps(post)})
    rebuild_index()
    reference_service.rebuild_references()
    return {"slug": slug, "written": True}
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
cd backend && python -m pytest tests/test_mcp_tools.py::test_wiki_write_creates_new_page tests/test_mcp_tools.py::test_wiki_write_updates_existing_page -v
```

Expected: `PASSED`

- [ ] **Step 5 : Lancer la suite complète**

```bash
cd backend && python -m pytest tests/test_mcp_tools.py -v
```

Expected: tous `PASSED`

- [ ] **Step 6 : Commit**

```bash
git add backend/app/mcp/server.py backend/tests/test_mcp_tools.py
git commit -m "feat(mcp): add wiki_write tool"
```

---

## Task 4 : `wiki_delete` — outil MCP

**Files:**
- Modify: `backend/app/mcp/server.py`
- Test: `backend/tests/test_mcp_tools.py`

- [ ] **Step 1 : Écrire les tests échouants**

Ajouter dans `backend/tests/test_mcp_tools.py` :

```python
def test_wiki_delete_marks_page_deprecated(wiki_env):
    p = Path(settings.wiki_path) / "concept" / "to-deprecate.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("---\ntitle: À déprécier\nstatus: validated\n---\n\n# À déprécier\n", encoding="utf-8")
    from app.mcp.server import wiki_delete
    result = wiki_delete("concept--to-deprecate")
    assert result == {"slug": "concept--to-deprecate", "deprecated": True}
    post = fm.load(str(p))
    assert post.metadata["status"] == "deprecated"


def test_wiki_delete_unknown_slug_returns_false(wiki_env):
    from app.mcp.server import wiki_delete
    result = wiki_delete("concept--inexistant")
    assert result == {"slug": "concept--inexistant", "deprecated": False}
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
cd backend && python -m pytest tests/test_mcp_tools.py::test_wiki_delete_marks_page_deprecated tests/test_mcp_tools.py::test_wiki_delete_unknown_slug_returns_false -v
```

Expected: `FAILED` avec `ImportError: cannot import name 'wiki_delete'`

- [ ] **Step 3 : Implémenter `wiki_delete` dans server.py**

Ajouter à la fin de `backend/app/mcp/server.py` :

```python
@mcp.tool()
def wiki_delete(slug: str) -> dict:
    """Marque une page wiki comme dépréciée (status: deprecated). La page reste sur le disque."""
    deprecated = wiki_manager.set_deprecated(slug)
    return {"slug": slug, "deprecated": deprecated}
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
cd backend && python -m pytest tests/test_mcp_tools.py::test_wiki_delete_marks_page_deprecated tests/test_mcp_tools.py::test_wiki_delete_unknown_slug_returns_false -v
```

Expected: `PASSED`

- [ ] **Step 5 : Lancer toute la suite de tests**

```bash
cd backend && python -m pytest -v
```

Expected: tous `PASSED`

- [ ] **Step 6 : Commit**

```bash
git add backend/app/mcp/server.py backend/tests/test_mcp_tools.py
git commit -m "feat(mcp): add wiki_delete tool"
```

---

## Task 5 : Mise à jour de la documentation

**Files:**
- Modify: `README.md` — section "Outils MCP disponibles"
- Modify: `CHANGELOG.md`

- [ ] **Step 1 : Mettre à jour le tableau MCP dans README.md**

Dans la section `### Outils MCP disponibles`, remplacer le tableau par :

```markdown
| Outil | Description |
|---|---|
| `wiki_guide` | Retourne l'index structuré du wiki (catégories, slugs, résumés) |
| `wiki_search` | Recherche dans le wiki |
| `wiki_read_page` | Lit le contenu d'une page par slug |
| `wiki_list_pages` | Liste toutes les pages (sans contenu) |
| `wiki_write` | Crée ou met à jour une page wiki (champs structurés) |
| `wiki_delete` | Marque une page comme dépréciée |
| `wiki_rebuild_index` | Reconstruit l'index FTS5 |
| `wiki_list_stale` | Liste les pages marquées obsolètes |
| `wiki_list_references` | Retourne le graphe de références d'une page |
```

- [ ] **Step 2 : Mettre à jour CHANGELOG.md**

Dans la section `## [0.1.0]`, sous `### Ajouté`, ajouter :

```markdown
- Outils MCP `wiki_guide`, `wiki_write`, `wiki_delete` — découverte, création/MAJ et dépréciation de pages via MCP
```

- [ ] **Step 3 : Commit**

```bash
git add README.md CHANGELOG.md
git commit -m "docs: add wiki_guide, wiki_write, wiki_delete to MCP docs"
```
