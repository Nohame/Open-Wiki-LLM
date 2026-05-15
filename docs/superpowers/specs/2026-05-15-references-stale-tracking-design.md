# OpenWikiLLM — Graph de Références & Stale Tracking (Sub-projet 3)

## Objectif

Tracker les dépendances entre pages wiki et leurs sources d'import, détecter automatiquement les pages devenues obsolètes après un nouvel ingest, et exposer ces informations aux agents via MCP et au frontend via un badge.

## Architecture

**Approche hybride :**
- Stale flag dans le frontmatter markdown (`stale: true`) — source de vérité, survit aux rebuilds
- Table SQLite `page_references(page_slug, source_slug)` — cache rebuild-able pour requêtes rapides
- Pas de watcher filesystem pour ce sub-projet

**Source de données pour les références :** champ `sources: list[str]` déjà présent dans chaque frontmatter de page wiki, rempli par le LLM lors de l'ingest.

## Fichiers touchés

| Statut | Fichier |
|--------|---------|
| Créer | `backend/app/services/reference_service.py` |
| Créer | `backend/app/api/references.py` |
| Créer | `backend/app/models/references.py` |
| Créer | `backend/tests/test_reference_service.py` |
| Créer | `backend/tests/test_references_endpoint.py` |
| Créer | `backend/tests/test_stale_endpoint.py` |
| Modifier | `backend/app/storage/search.py` — table `page_references` |
| Modifier | `backend/app/services/wiki_manager.py` — `set_stale()` |
| Modifier | `backend/app/services/ingest_service.py` — post-ingest stale logic |
| Modifier | `backend/app/mcp/server.py` — `wiki_list_stale`, `wiki_list_references` |
| Modifier | `backend/app/api/pages.py` — `PATCH /api/pages/{slug}/stale` |
| Modifier | `backend/app/models/page.py` — champ `stale: bool = False` |
| Modifier | `backend/app/main.py` — enregistrer references router |
| Modifier | `frontend/types/api.ts` — `WikiPage.stale` + `PageReferences` |
| Modifier | `frontend/pages/wiki/[slug].vue` (ou équivalent) — badge Obsolète + bouton |

## Section 1 : Table SQLite `page_references`

### Schema

Dans `backend/app/storage/search.py`, ajouter à la création du DB :

```python
conn.execute("""
    CREATE TABLE IF NOT EXISTS page_references (
        page_slug TEXT NOT NULL,
        source_slug TEXT NOT NULL,
        PRIMARY KEY (page_slug, source_slug)
    )
""")
```

La table est dans le même fichier `search.db`. Elle est entièrement rebuild-able depuis les frontmatters.

## Section 2 : `reference_service.py`

### Fonctions

```python
def rebuild_references() -> None:
    """
    Parcourt tous les .md dans wiki/, extrait sources[] du frontmatter,
    remplace entièrement page_references dans SQLite.
    """

def get_references(slug: str) -> dict:
    """
    Retourne:
    - references: list[str] — sources[] de la page slug
    - referenced_by: list[str] — pages qui ont slug dans leurs sources[]
    """

def get_stale_pages() -> list[str]:
    """
    Retourne les slugs de toutes les pages avec stale: true dans leur frontmatter.
    Scan filesystem de wiki/ (frontmatter = source de vérité).
    Acceptable pour MVP jusqu'à ~1000 pages.
    """
```

### Logique `rebuild_references`

```python
def rebuild_references() -> None:
    wiki_root = Path(settings.wiki_path)
    rows = []
    for md_file in wiki_root.rglob("*.md"):
        # Convertir chemin en slug : wiki/concept/foo.md → concept--foo
        # Même logique que rebuild_index_file() dans wiki_manager.py
        rel = md_file.relative_to(wiki_root)
        parts = list(rel.parts)
        if len(parts) == 1:
            slug = parts[0].removesuffix(".md")
        else:
            slug = "--".join([*parts[:-1], parts[-1].removesuffix(".md")])
        content = md_file.read_text(encoding="utf-8")
        sources = _extract_sources(content)  # parse frontmatter sources[]
        for source_slug in sources:
            rows.append((slug, source_slug))
    # Remplace atomiquement
    with get_db() as conn:
        conn.execute("DELETE FROM page_references")
        conn.executemany(
            "INSERT OR IGNORE INTO page_references VALUES (?, ?)", rows
        )
```

### `_extract_sources(content: str) -> list[str]`

Parse le frontmatter YAML. Si le champ `sources` est absent ou vide, retourne `[]`. Si le frontmatter est malformé, log un warning et retourne `[]` sans lever d'exception.

## Section 3 : `wiki_manager.set_stale`

```python
def set_stale(slug: str, stale: bool) -> None:
    """
    Lit le frontmatter du fichier markdown correspondant à slug,
    met à jour le champ stale, réécrit le fichier.
    Si le fichier n'existe pas ou le frontmatter est malformé : log warning, skip.
    """
    path = _slug_to_path(slug)
    if not path.exists():
        return
    content = path.read_text(encoding="utf-8")
    # Remplacer ou ajouter le champ stale dans le frontmatter YAML
    updated = _set_frontmatter_field(content, "stale", stale)
    path.write_text(updated, encoding="utf-8")
```

La fonction `_set_frontmatter_field(content, key, value)` est privée :
- Si la clé existe dans le frontmatter → remplace la valeur
- Si la clé n'existe pas → l'ajoute avant le `---` fermant
- Utilise manipulation de string (pas de re-parse YAML complet pour éviter de perdre le formatage)

## Section 4 : Logique post-ingest dans `ingest_service.py`

Après `rebuild_index()`, ajouter :

```python
from . import reference_service

# 1. Clear stale sur les pages mises à jour par le LLM
for slug in written_slugs:
    wiki_manager.set_stale(slug, False)

# 2. Rebuild graph de références
reference_service.rebuild_references()

# 3. Marquer stale les pages dépendantes non mises à jour
refs = reference_service.get_references(new_slug)
for dependent_slug in refs["referenced_by"]:
    if dependent_slug not in written_slugs:
        wiki_manager.set_stale(dependent_slug, True)
        stale_marked.append(dependent_slug)
```

Le retour de `ingest_text` est étendu :

```python
return {
    ...
    "stale_marked": stale_marked,  # pages marquées stale lors de cet ingest
}
```

## Section 5 : Modèles Pydantic

### `backend/app/models/page.py`

Ajouter `stale: bool = False` à `WikiPage` :

```python
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
```

### `backend/app/models/references.py`

```python
from pydantic import BaseModel


class PageReferences(BaseModel):
    slug: str
    references: list[str] = []
    referenced_by: list[str] = []
```

### `backend/app/models/ingest.py`

```python
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

## Section 6 : Endpoints API

### `GET /api/pages/{slug}/references`

**Fichier :** `backend/app/api/references.py`

```python
from fastapi import APIRouter, HTTPException
from ..services import reference_service
from ..models.references import PageReferences

router = APIRouter(prefix="/api")


@router.get("/pages/{slug}/references", response_model=PageReferences)
def get_page_references(slug: str) -> PageReferences:
    refs = reference_service.get_references(slug)
    return PageReferences(slug=slug, **refs)
```

**Réponse exemple :**
```json
{
  "slug": "concept--groove",
  "references": ["imports--ticket-system-doc"],
  "referenced_by": ["imports--onboarding-2024"]
}
```

### `PATCH /api/pages/{slug}/stale`

Nouveau modèle dans `backend/app/models/page.py` :

```python
class StaleUpdate(BaseModel):
    stale: bool
```

Dans `backend/app/api/pages.py` :

```python
from ..models.page import StaleUpdate

@router.patch("/pages/{slug}/stale", response_model=WikiPage)
def update_stale(slug: str, body: StaleUpdate) -> WikiPage:
    page = get_page(slug)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    wiki_manager.set_stale(slug, body.stale)
    return get_page(slug)
```

## Section 7 : MCP Tools

Dans `backend/app/mcp/server.py` :

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

## Section 8 : Frontend

### `frontend/types/api.ts`

Ajouter `stale` à `WikiPage` et `stale_marked` à `IngestResult`, et ajouter `PageReferences` :

```typescript
export interface WikiPage extends WikiPageSummary {
  content: string
  stale: boolean
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
```

### Badge "Obsolète" dans la page wiki

Dans le composant qui affiche une page wiki (`pages/wiki/[slug].vue` ou équivalent), après le titre :

```html
<!-- Badge stale -->
<div v-if="page.stale" class="flex items-center gap-2 mb-4 p-2 bg-red-900/30 border border-red-700 rounded-lg">
  <span class="text-red-400 text-sm font-medium">⚠ Page obsolète</span>
  <span class="text-red-300 text-xs">Une source a été mise à jour depuis la dernière révision de cette page.</span>
  <button
    class="ml-auto text-xs text-red-300 hover:text-white underline"
    @click="markAsCurrent"
  >
    Marquer comme à jour
  </button>
</div>
```

La fonction `markAsCurrent` appelle `PATCH /api/pages/{slug}/stale` avec `{ stale: false }` et recharge la page.

## Section 9 : Gestion d'erreurs

| Cas | Comportement |
|-----|-------------|
| `sources: []` dans frontmatter | Ignoré dans rebuild_references (rien à insérer) |
| Frontmatter malformé lors de rebuild | Log warning, page skippée, rebuild continue |
| `set_stale` sur slug inexistant | Log warning, no-op, pas d'exception |
| `GET /api/pages/{slug}/references` sur slug inexistant | Retourne `PageReferences(slug=slug, references=[], referenced_by=[])` — pas de 404 (le graph peut référencer des slugs sans page) |
| `PATCH /api/pages/{slug}/stale` sur slug inexistant | 404 |
| Erreur pendant post-ingest stale logic | Log error, ingest retourne quand même un résultat (stale_marked peut être incomplet) |

## Section 10 : Tests

### `test_reference_service.py`

- `test_rebuild_references_empty_wiki` — wiki vide → table vide
- `test_rebuild_references_single_page` — page avec `sources: [imports--foo]` → 1 ligne dans page_references
- `test_rebuild_references_no_sources` — page sans sources → aucune ligne
- `test_rebuild_references_malformed_frontmatter` — frontmatter invalide → warning, pas d'exception
- `test_get_references_forward` — page A référence imports--foo → references: [imports--foo]
- `test_get_references_backward` — imports--foo cité par A et B → referenced_by: [A, B]
- `test_get_references_unknown_slug` — slug absent → references: [], referenced_by: []
- `test_get_stale_pages` — pages avec stale: true retournées, autres ignorées

### `test_references_endpoint.py`

- `test_references_endpoint_basic` — GET /api/pages/{slug}/references → 200 + structure correcte
- `test_references_endpoint_unknown` — slug sans références → 200 + listes vides

### `test_stale_endpoint.py`

- `test_set_stale_true` — PATCH stale: true → page.stale == True sur disque
- `test_set_stale_false` — PATCH stale: false → page.stale == False sur disque
- `test_set_stale_unknown` — slug inexistant → 404

### `test_ingest.py` (ajouts)

- `test_ingest_marks_dependents_stale` — page B a `sources: [imports--foo]`, ingest de foo sans mise à jour de B → B.stale == True
- `test_ingest_clears_stale_on_updated` — page B stale, ingest met à jour B → B.stale == False

## Limites connues (MVP)

- `rebuild_references()` est un full-scan de wiki/ à chaque ingest — acceptable jusqu'à ~1000 pages
- Le stale tracking est basé uniquement sur le champ `sources[]` du frontmatter (pas les wikilinks dans le contenu)
- `get_stale_pages()` scanne les fichiers plutôt que d'utiliser une colonne SQLite dénormalisée — acceptable pour MVP
- Pas de notification temps réel au frontend quand une page devient stale (page-reload requis)
- `stale_marked` dans `IngestResult` n'est pas affiché dans le frontend dans ce sub-projet
