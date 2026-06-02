# Design — Outils MCP wiki_guide, wiki_write, wiki_delete

## Objectif

Compléter le serveur MCP d'OpenWikiLLM avec trois outils manquants :
- `wiki_guide` — découverte du contenu disponible
- `wiki_write` — création ou mise à jour d'une page wiki
- `wiki_delete` — dépréciation d'une page wiki

Tous les outils conservent le préfixe `wiki_` pour cohérence avec l'existant.

## Contexte

Outils MCP actuels : `wiki_list_pages`, `wiki_read_page`, `wiki_search`, `wiki_rebuild_index`, `wiki_list_stale`, `wiki_list_references`.

`wiki_write` et `wiki_delete` permettent aux agents IA de modifier le wiki directement via MCP, sans passer par l'API REST ni le pipeline d'ingestion Ollama.

## Décisions

- **wiki_write** : écriture structurée (champs séparés, le backend assemble le frontmatter) — pas d'écriture Markdown brut
- **wiki_delete** : dépréciation douce (`status → deprecated`) — pas de suppression physique
- **Resync systématique** : `wiki_write` rebuilde l'index FTS5 et le graphe de références après chaque écriture, identique au comportement de `ingest_service.py`

## Outils

### `wiki_guide() → str`

Retourne le contenu de `wiki/index.md` — index structuré par catégorie avec slugs et résumés, généré automatiquement par le système.

Appelle `wiki_manager.load_index()`.

Retourne une chaîne vide si l'index n'existe pas encore.

### `wiki_write(slug, title, content, type, status, tags, confidence) → dict`

| Paramètre | Type | Obligatoire | Défaut |
|---|---|---|---|
| `slug` | str | oui | — |
| `title` | str | oui | — |
| `content` | str | oui | — |
| `type` | str | non | `"concept"` |
| `status` | str | non | `"draft"` |
| `tags` | list[str] | non | `[]` |
| `confidence` | str | non | `"medium"` |

**Flux :**
1. Assemble le frontmatter YAML avec les champs fournis + `updated_at` (date du jour)
2. Concatène frontmatter + `content` en Markdown complet
3. `wiki_manager.apply_updates({slug: markdown})` → écrit le fichier
4. `rebuild_index()` → resync FTS5
5. `rebuild_references()` → resync graphe
6. Retourne `{"slug": slug, "written": True}`

### `wiki_delete(slug) → dict`

**Flux :**
1. Vérifie que la page existe
2. `wiki_manager.set_deprecated(slug)` → `status: deprecated` dans le frontmatter
3. Retourne `{"slug": slug, "deprecated": True}`

Si le slug est introuvable : retourne `{"slug": slug, "deprecated": False}`.

Pas de rebuild de l'index (la page reste dans FTS5 mais `answer_service` filtre sur `status`).

## Fichiers modifiés

| Fichier | Changement |
|---|---|
| `backend/app/mcp/server.py` | Ajout des 3 outils |
| `backend/app/services/wiki_manager.py` | Ajout `set_deprecated(slug)` |
| `backend/tests/test_mcp_tools.py` | Tests des 3 nouveaux outils |

## Tests

- `wiki_guide` : retourne le contenu de `index.md` ; chaîne vide si absent
- `wiki_write` nouvelle page : fichier créé avec bon frontmatter et contenu
- `wiki_write` page existante : fichier écrasé, `rebuild_index` et `rebuild_references` appelés
- `wiki_delete` slug existant : `status: deprecated` dans le frontmatter
- `wiki_delete` slug inexistant : retourne `{"slug": ..., "deprecated": False}`

## Limites connues

- `wiki_write` ne passe pas par Ollama : le contenu n'est pas structuré/enrichi automatiquement
- `wiki_delete` ne retire pas la page de l'index FTS5 immédiatement (exclue des réponses via `answer_service`, visible dans `wiki_search`)
- Le serveur MCP ne vérifie pas `X-API-Key` (limitation existante)
