# OpenWikiLLM — Karpathy Pattern : Catégories Wiki + Log Enrichi (Sub-projet 2)

## Objectif

Implémenter la vision complète du pattern Karpathy : chaque ingest produit non seulement une page `source` dans `imports/`, mais aussi des pages `concept--` et `entity--` extraites automatiquement par le LLM. Le journal `wiki/log.md` est enrichi avec durée, tags, et répartition par catégorie. Une page `/log` dans le frontend expose ce journal.

## Architecture

**Périmètre :**
- Modification du prompt `MULTI_UPDATE_PROMPT` dans `ollama_service.py`
- Modifications de `ingest_service.py` : durée, catégorisation des slugs, log enrichi
- Ajout de `load_log()` dans `wiki_manager.py`
- Nouveau endpoint `GET /api/wiki/log` dans `backend/app/api/log.py`
- Nouveau modèle `LogResponse` dans `backend/app/models/log.py`
- Mise à jour `IngestResult` : ajout `concepts_created` et `entities_created`
- Nouveau fichier `frontend/pages/log.vue`
- Mise à jour `frontend/components/AppSidebar.vue` (lien Journal)
- Mise à jour frontend `IngestText.vue` et `IngestFile.vue` (affichage concepts/entités)
- Mise à jour `frontend/types/api.ts`

**Pas de nouvel appel LLM** : même flux à 2 appels. La catégorisation est faite par le LLM dans l'appel 2, et par le backend (tri des slugs par préfixe) au retour.

## Modifications `ollama_service.py`

### `MULTI_UPDATE_PROMPT` — section Règles

Remplacer la section Règles actuelle par :

```
Règles :
- Crée une page de type `source` pour le document (slug : {new_slug})
- Si le document contient des concepts métier distincts, crée ou mets à jour les pages concept-- correspondantes (ex: concept--groove-tags)
- Si le document mentionne des entités (personnes, fournisseurs, outils, systèmes), crée ou mets à jour les pages entity-- correspondantes (ex: entity--alizee)
- Mets à jour les pages liées existantes : nouvelles informations, corrections, cross-refs [[slug]]
- N'inclus QUE les pages qui changent réellement
- Réponds UNIQUEMENT avec les balises <page>, sans commentaire
```

## Modifications `ingest_service.py`

### `ingest_text` — nouveau flux

```python
import time

async def ingest_text(text: str, title: str | None, tags: list[str]) -> dict:
    start = time.monotonic()
    today = date.today().isoformat()
    effective_title = title or "Source sans titre"
    slug = _slugify(effective_title)
    new_slug = f"imports--{slug}"

    # 1. Raw
    raw_path = Path(settings.raw_path) / "imports" / f"{slug}.md"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(text, encoding="utf-8")

    # 2. Schema + index
    schema = schema_service.load_or_create()
    index_content = wiki_manager.load_index()

    # 3. Appel 1 : pages liées
    related_slugs = await identify_related_pages(text, effective_title, index_content)
    related_pages = wiki_manager.load_pages(related_slugs)

    # 4. Appel 2 : générer XML multi-pages
    xml_output = await compile_multi_page(
        text, effective_title, tags, today, schema, related_pages, new_slug
    )

    # 5. Parser + appliquer
    updates = wiki_manager.parse_xml_updates(xml_output)
    written_slugs = wiki_manager.apply_updates(updates)

    # 6. Catégoriser les slugs écrits
    concepts_created = [s for s in written_slugs if s.startswith("concept--")]
    entities_created = [s for s in written_slugs if s.startswith("entity--")]
    # pages_updated = imports mis à jour (hors nouvelle source) — pas de chevauchement avec concepts/entities
    pages_updated = [s for s in written_slugs if s.startswith("imports--") and s != new_slug]

    # 7. Index + log enrichi
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

    # 8. Index SQLite FTS
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
```

## Modifications `wiki_manager.py`

### Nouvelle fonction `load_log`

```python
def load_log() -> str:
    log_path = Path(settings.wiki_path) / "log.md"
    if not log_path.exists():
        return ""
    return log_path.read_text(encoding="utf-8")
```

## Nouveau `backend/app/models/log.py`

```python
from pydantic import BaseModel


class LogResponse(BaseModel):
    content: str
```

## Modifications `backend/app/models/ingest.py`

```python
class IngestResult(BaseModel):
    slug: str
    raw_path: str
    wiki_path: str
    title: str
    pages_updated: list[str] = []
    concepts_created: list[str] = []
    entities_created: list[str] = []
```

## Nouveau `backend/app/api/log.py`

```python
from fastapi import APIRouter
from ..services import wiki_manager
from ..models.log import LogResponse

router = APIRouter()


@router.get("/wiki/log", response_model=LogResponse)
async def get_log() -> LogResponse:
    return LogResponse(content=wiki_manager.load_log())
```

## Modifications `backend/app/main.py`

Importer et enregistrer le nouveau router :

```python
from .api import log as log_router
app.include_router(log_router.router, prefix="/api")
```

## Frontend

### `frontend/types/api.ts`

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

### `frontend/pages/log.vue`

Page simple qui charge et affiche `wiki/log.md` rendu en markdown :

```vue
<template>
  <div class="max-w-3xl mx-auto py-8 px-4">
    <h1 class="text-xl font-semibold text-white mb-6">Journal des ingestions</h1>
    <div v-if="loading" class="text-gray-400 text-sm">Chargement...</div>
    <div v-else-if="!content" class="text-gray-500 text-sm">Aucune ingestion enregistrée.</div>
    <WikiContent v-else :markdown="content" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
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

### `frontend/components/AppSidebar.vue`

Ajouter un lien `Journal` entre `Wiki` et `Ingérer` :

```typescript
{ path: '/log', label: 'Journal', icon: ScrollText }
```

Importer `ScrollText` depuis `lucide-vue-next`.

### `IngestText.vue` et `IngestFile.vue`

Dans le bloc résultat, afficher `concepts_created` et `entities_created` en plus de `pages_updated` :

```html
<!-- après pages_updated -->
<p v-for="s in result.concepts_created" :key="s" class="text-purple-300 text-xs">+ {{ s }}</p>
<p v-for="s in result.entities_created" :key="s" class="text-yellow-300 text-xs">+ {{ s }}</p>
```

Dans `IngestFile.vue`, ajouter `conceptsCreated?: string[]` et `entitiesCreated?: string[]` à `FileEntry`.

## Tests

### `backend/tests/test_wiki_manager.py` (ajouts)

- `test_load_log_absent` — log.md absent → retourne `""`
- `test_load_log_present` — log.md présent → retourne le contenu

### `backend/tests/test_ingest.py` (modifications)

- Mettre à jour `MOCK_XML` et les mocks existants pour que le retour inclue `concepts_created` et `entities_created`
- `test_ingest_text_multi_page` : vérifier que `concepts_created` et `entities_created` sont présents dans la réponse (listes, potentiellement vides)
- `test_ingest_text_with_concepts` : mock retourne XML avec une page `concept--foo` → vérifier `concepts_created == ["concept--foo"]`
- `test_log_endpoint` : `GET /api/wiki/log` → 200, champ `content` string

### `backend/tests/test_log_endpoint.py` (nouveau)

```python
def test_log_endpoint_empty(client_with_dirs):
    response = client_with_dirs.get("/api/wiki/log")
    assert response.status_code == 200
    assert response.json()["content"] == ""

def test_log_endpoint_with_content(client_with_dirs):
    Path(settings.wiki_path).mkdir(parents=True, exist_ok=True)
    Path(settings.wiki_path, "log.md").write_text("# Journal\n\n## test", encoding="utf-8")
    response = client_with_dirs.get("/api/wiki/log")
    assert response.status_code == 200
    assert "Journal" in response.json()["content"]
```

## Gestion d'erreurs

| Erreur | Comportement |
|--------|--------------|
| `log.md` absent | `load_log()` retourne `""`, endpoint retourne `{"content": ""}` |
| LLM ne crée aucun concept/entité | `concepts_created = []`, `entities_created = []` — normal |
| LLM crée des slugs avec préfixe inconnu | Ignorés dans la catégorisation, inclus dans `pages_updated` |

## Limites connues (MVP)

- La qualité de l'extraction concept/entité dépend du LLM — peut être inconstante
- La durée inclut l'écriture fichiers et rebuild index, pas seulement les appels LLM
- Pas de pagination pour le log (acceptable jusqu'à ~500 entrées)
- Le composant `WikiContent` doit exister côté frontend (il est déjà utilisé pour les pages wiki)
