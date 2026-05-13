# OpenWikiLLM — Karpathy Pattern : Ingest Multi-Pages (Sub-projet 1)

## Objectif

Transformer l'ingest d'un système "1 document → 1 page wiki" en un système "1 document → N pages wiki mises à jour", selon le pattern décrit par Andrej Karpathy. Chaque ingest analyse les pages existantes, crée la nouvelle page, met à jour les pages liées, et maintient automatiquement `index.md` et `log.md`.

## Architecture

**Approche :** 2 appels Ollama par ingest (synchrone). Appel 1 identifie les pages liées via `index.md`. Appel 2 génère toutes les mises à jour en XML. Le backend parse et applique les écritures atomiquement.

**Périmètre :** texte et fichiers (.md/.txt/.pdf/.docx). L'ingest image reste en mode single-page (évolution future).

## Nouveaux fichiers wiki

Trois fichiers maintenus automatiquement à la racine de `wiki/` :

### `wiki/schema.md`
Créé au premier ingest si absent. Editable manuellement par l'utilisateur. Contenu par défaut :

```markdown
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
```

### `wiki/index.md`
Catalogue de toutes les pages, mis à jour à chaque ingest. Format :

```markdown
# Index du wiki

<!-- Mis à jour automatiquement — ne pas modifier manuellement -->

## imports

| Page | Résumé |
|------|--------|
| [adv-rag](imports/adv-rag.md) | Procédures ADV ↔ SC : tags Groove, annulations Holzmann/Zipper |
```

Organisé par catégorie (dossier dans `wiki/`). Lu par le LLM en début d'ingest pour naviguer le wiki sans charger toutes les pages.

### `wiki/log.md`
Journal append-only, parseable avec `grep` :

```markdown
# Journal des ingestions

## [2026-05-13] ingest | adv-rag
- Source : adv-rag.md
- Pages créées : imports--adv-rag
- Pages mises à jour : —
- Durée : 42s
```

## Backend

### Nouveaux modules

#### `backend/app/services/wiki_manager.py`

Interface unique pour toutes les opérations multi-fichiers sur le wiki. Responsabilités claires et testables indépendamment.

```python
def load_index() -> str
    # Lit wiki/index.md. Retourne "" si absent.

def load_pages(slugs: list[str]) -> dict[str, str]
    # Lit N pages par slug (ex: "imports--adv-rag" → wiki/imports/adv-rag.md).
    # Ignore silencieusement les slugs inexistants.

def parse_xml_updates(xml: str) -> dict[str, str]
    # Parse <page slug="x">contenu</page> → {"x": "contenu"}.
    # Lève ValueError si aucune balise trouvée.

def apply_updates(updates: dict[str, str]) -> list[str]
    # Écrit tous les fichiers. Retourne la liste des slugs écrits.
    # Crée les répertoires manquants.

def rebuild_index_file() -> None
    # Relit tous les fichiers wiki/, extrait title + première ligne de ## Résumé,
    # régénère wiki/index.md par catégorie (dossier).

def append_log(entry: str) -> None
    # Ajoute une entrée en tête de wiki/log.md (ordre antéchronologique).
```

#### `backend/app/services/schema_service.py`

```python
def load_or_create() -> str
    # Lit wiki/schema.md.
    # Si absent : crée le fichier avec le contenu par défaut, retourne ce contenu.
```

### Modifications `ollama_service.py`

Deux nouveaux prompts, deux nouvelles fonctions async :

#### `identify_related_pages(text, title, index_content) -> list[str]`

Prompt `IDENTIFY_RELATED_PROMPT` :
```
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
```

Retourne `list[str]`. En cas d'échec de parsing JSON → retourne `[]` (pas d'erreur bloquante).

#### `compile_multi_page(text, title, tags, date, schema, related_pages) -> str`

Prompt `MULTI_UPDATE_PROMPT` :
```
Tu maintiens un wiki selon ce schéma :
{schema}

Nouveau document à intégrer :
Titre : {title} | Tags : {tags} | Date : {date}
{text}

Pages wiki existantes liées :
{related_pages}

Génère toutes les mises à jour nécessaires.
Pour chaque page à créer ou modifier, utilise ce format EXACT :

<page slug="{slug}">
[contenu complet de la page en Markdown avec frontmatter]
</page>

Règles :
- Crée une page pour le document source (slug : {new_slug})
- Mets à jour les pages liées : nouvelles informations, corrections, cross-refs [[slug]]
- N'inclus QUE les pages qui changent réellement
- Réponds UNIQUEMENT avec les balises <page>, sans commentaire
```

`related_pages` est formaté comme :
```
=== imports--adv-rag ===
[contenu complet de la page]

=== imports--holzmann ===
[contenu complet de la page]
```

### Modifications `ingest_service.py`

Nouveau flux pour `ingest_text` (et appelé depuis `ingest_file` via `ingest_text`) :

```python
async def ingest_text(text: str, title: str | None, tags: list[str]) -> dict:
    today = date.today().isoformat()
    effective_title = title or "Source sans titre"
    slug = _slugify(effective_title)
    new_slug = f"imports--{slug}"

    # 1. Sauvegarder le raw (inchangé)
    raw_path = Path(settings.raw_path) / "imports" / f"{slug}.md"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(text)

    # 2. Charger schema + index
    schema = schema_service.load_or_create()
    index_content = wiki_manager.load_index()

    # 3. Appel 1 : identifier les pages liées
    related_slugs = await identify_related_pages(text, effective_title, index_content)

    # 4. Charger les pages liées
    related_pages = wiki_manager.load_pages(related_slugs)

    # 5. Appel 2 : générer toutes les mises à jour
    xml_output = await compile_multi_page(
        text, effective_title, tags, today, schema, related_pages, new_slug
    )

    # 6. Parser + appliquer les écritures
    updates = wiki_manager.parse_xml_updates(xml_output)
    written_slugs = wiki_manager.apply_updates(updates)

    # 7. Maintenir index.md et log.md
    wiki_manager.rebuild_index_file()
    pages_updated = [s for s in written_slugs if s != new_slug]
    wiki_manager.append_log(
        f"## [{today}] ingest | {slug}\n"
        f"- Pages créées : {new_slug}\n"
        f"- Pages mises à jour : {', '.join(pages_updated) or '—'}\n"
    )

    # 8. Reconstruire l'index SQLite FTS
    rebuild_index()

    wiki_path = Path(settings.wiki_path) / "imports" / f"{slug}.md"
    return {
        "slug": new_slug,
        "raw_path": str(raw_path),
        "wiki_path": str(wiki_path),
        "title": effective_title,
        "pages_updated": pages_updated,
    }
```

### Modifications `models/ingest.py`

```python
class IngestResult(BaseModel):
    slug: str
    raw_path: str
    wiki_path: str
    title: str
    pages_updated: list[str] = []
```

## Frontend

### `~/types/api.ts`

```typescript
interface IngestResult {
  slug: string
  raw_path: string
  wiki_path: string
  title: string
  pages_updated: string[]
}
```

### `IngestText.vue` et `IngestFile.vue`

Afficher les pages mises à jour dans le résultat :
```
✓ imports--adv-rag créé
  ↻ imports--holzmann mis à jour
  ↻ imports--procedures-sc mis à jour
```

Messages de chargement en deux phases :
- Pendant l'appel 1 : "Analyse des pages liées..."
- Pendant l'appel 2 : "Compilation du wiki..."

## Tests

### Backend

**`backend/tests/test_wiki_manager.py`** (nouveau) :
- `test_parse_xml_updates_single` — une balise `<page>` → dict à 1 entrée
- `test_parse_xml_updates_multiple` — 3 balises → dict à 3 entrées
- `test_parse_xml_updates_malformed` — XML sans balise → `ValueError`
- `test_apply_updates_creates_dirs` — slug `imports--foo` → crée `wiki/imports/foo.md`
- `test_rebuild_index_file` — wiki avec 2 pages → index.md contient 2 lignes
- `test_append_log_creates_file` — premier append crée `log.md`
- `test_append_log_prepends` — second append se retrouve en tête

**`backend/tests/test_schema_service.py`** (nouveau) :
- `test_load_or_create_creates_default` — absent → crée le fichier, retourne le contenu
- `test_load_or_create_reads_existing` — présent → retourne le contenu sans écraser

**`backend/tests/test_ingest.py`** (modifications) :
- Mock les 2 appels Ollama (`identify_related_pages` + `compile_multi_page`)
- `test_ingest_text_multi_page` — vérifie que 2 fichiers sont créés, `pages_updated` non vide, `index.md` mis à jour
- `test_ingest_text_no_related` — `identify_related_pages` retourne `[]` → 1 seul fichier créé
- Mettre à jour `client_with_dirs` fixture pour inclure `wiki_path` dans les chemins temp
- Les tests existants continuent de passer (mocks adaptés)

### Frontend

Pas de nouveau test composable — la signature de `useIngest` ne change pas. Seul `IngestResult` a un champ supplémentaire (optionnel avec `= []`).

## Gestion d'erreurs

| Erreur | Comportement |
|--------|--------------|
| Appel 1 retourne JSON invalide | `related_slugs = []`, on continue sans pages liées |
| Appel 2 retourne XML malformé | HTTP 422 "Erreur de génération wiki" |
| Page liée introuvable sur disque | Ignorée silencieusement dans `load_pages` |
| Écriture fichier impossible (permissions) | Remonte en HTTP 500 |

## Limites connues (MVP)

- Ingest image reste single-page (pas de multi-page)
- `rebuild_index_file` relit tous les fichiers à chaque ingest (acceptable jusqu'à ~500 pages)
- Pas de détection de conflits si deux ingests simultanés modifient la même page
- Le LLM peut retourner des slugs inexistants dans l'appel 1 (ignorés par `load_pages`)
- Timeout Ollama à 120s par appel — à surveiller pour les gros documents
