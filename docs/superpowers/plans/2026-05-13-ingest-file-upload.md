# Ingest File Upload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter un onglet "Fichiers" dans la page Ingest permettant d'uploader plusieurs fichiers (.md/.txt/.pdf/.docx) et de les ingérer séquentiellement avec statut par fichier en temps réel.

**Architecture:** Nouvel endpoint `POST /api/ingest/file` (multipart) qui extrait le texte via un module `file_extractor.py`, puis délègue à `ingest_text()` existant. Le frontend gère un tableau `FileEntry[]` avec statut réactif, traitement séquentiel dans `IngestFile.vue`, et `ingestFile()` ajouté à `useIngest.ts`.

**Tech Stack:** FastAPI (UploadFile/Form), pdfplumber, python-docx, Nuxt 3, Vue 3 Composition API, Vitest

---

## File Structure

| Action   | Fichier | Rôle |
|----------|---------|------|
| Modify   | `backend/pyproject.toml` | Ajouter pdfplumber, python-docx (prod) + fpdf2 (dev) |
| Create   | `backend/app/services/file_extractor.py` | Extraction texte depuis bytes selon extension |
| Create   | `backend/tests/test_file_extractor.py` | Tests unitaires extracteurs |
| Modify   | `backend/app/api/ingest.py` | Ajouter endpoint `POST /api/ingest/file` |
| Modify   | `backend/tests/test_ingest.py` | Ajouter tests endpoint fichier |
| Modify   | `frontend/composables/useIngest.ts` | Ajouter méthode `ingestFile()` |
| Modify   | `frontend/tests/composables/useIngest.test.ts` | Ajouter test `ingestFile` |
| Create   | `frontend/components/ingest/IngestFile.vue` | Composant drag-and-drop + liste + actions |
| Modify   | `frontend/pages/ingest.vue` | Ajouter 3ème onglet Fichiers |

---

## Task 1: Backend dependencies + file extractor service

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/app/services/file_extractor.py`
- Create: `backend/tests/test_file_extractor.py`

- [ ] **Step 1: Ajouter les dépendances dans pyproject.toml**

Remplacer le bloc `dependencies` et `dev` par :

```toml
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.29.0",
    "fastmcp>=2.0.0",
    "python-frontmatter>=1.1.0",
    "pydantic-settings>=2.2.0",
    "httpx>=0.27.0",
    "pdfplumber>=0.11.0",
    "python-docx>=1.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
    "fpdf2>=2.7.0",
]
```

- [ ] **Step 2: Écrire les tests échouants pour file_extractor**

Créer `backend/tests/test_file_extractor.py` :

```python
import pytest
from io import BytesIO
from fpdf import FPDF
from docx import Document as DocxDocument
from app.services.file_extractor import extract_text


def _make_pdf(text: str) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(200, 10, txt=text)
    return bytes(pdf.output())


def _make_docx(text: str) -> bytes:
    buf = BytesIO()
    doc = DocxDocument()
    doc.add_paragraph(text)
    doc.save(buf)
    return buf.getvalue()


async def test_extract_txt():
    result = await extract_text(b"Hello world", "notes.txt")
    assert result == "Hello world"


async def test_extract_md():
    result = await extract_text(b"# Titre\n\nContenu", "doc.md")
    assert result == "# Titre\n\nContenu"


async def test_extract_pdf():
    data = _make_pdf("Hello PDF")
    result = await extract_text(data, "fichier.pdf")
    assert "Hello" in result


async def test_extract_docx():
    data = _make_docx("Texte du docx")
    result = await extract_text(data, "fichier.docx")
    assert "Texte du docx" in result


async def test_extract_invalid():
    with pytest.raises(ValueError, match="non support"):
        await extract_text(b"data", "script.exe")
```

- [ ] **Step 3: Vérifier que les tests échouent**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend
pip install -e ".[dev]"
pytest tests/test_file_extractor.py -v
```

Résultat attendu : `ImportError` ou `ModuleNotFoundError` (le module n'existe pas encore).

- [ ] **Step 4: Implémenter `backend/app/services/file_extractor.py`**

```python
from io import BytesIO
from pathlib import Path

import pdfplumber
from docx import Document

ALLOWED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx"}


async def extract_text(file_bytes: bytes, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in {".md", ".txt"}:
        return file_bytes.decode("utf-8")
    if ext == ".pdf":
        return _extract_pdf(file_bytes)
    if ext == ".docx":
        return _extract_docx(file_bytes)
    raise ValueError(f"Extension non supportée : {ext}")


def _extract_pdf(data: bytes) -> str:
    try:
        with pdfplumber.open(BytesIO(data)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        return "\n\n".join(p for p in pages if p.strip())
    except Exception as e:
        raise ValueError(f"PDF illisible : {e}") from e


def _extract_docx(data: bytes) -> str:
    try:
        doc = Document(BytesIO(data))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    except Exception as e:
        raise ValueError(f"DOCX illisible : {e}") from e
```

- [ ] **Step 5: Vérifier que les tests passent**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend
pytest tests/test_file_extractor.py -v
```

Résultat attendu : 5 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add backend/pyproject.toml backend/app/services/file_extractor.py backend/tests/test_file_extractor.py
git commit -m "feat: add file_extractor service with pdf/docx/txt/md support"
```

---

## Task 2: Backend endpoint POST /api/ingest/file

**Files:**
- Modify: `backend/app/api/ingest.py`
- Modify: `backend/tests/test_ingest.py`

- [ ] **Step 1: Écrire les tests échouants pour l'endpoint**

Ajouter à la fin de `backend/tests/test_ingest.py` :

```python
def test_ingest_file_endpoint_txt(client_with_dirs):
    with patch(
        "app.services.ingest_service.compile_to_markdown",
        new=AsyncMock(return_value=MOCK_MARKDOWN),
    ):
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
    with patch(
        "app.services.ingest_service.compile_to_markdown",
        new=AsyncMock(return_value=MOCK_MARKDOWN),
    ):
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
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend
pytest tests/test_ingest.py::test_ingest_file_endpoint_txt -v
```

Résultat attendu : FAILED avec 404 (endpoint inexistant).

- [ ] **Step 3: Implémenter l'endpoint dans `backend/app/api/ingest.py`**

Remplacer le contenu du fichier entier :

```python
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ..core.auth import verify_api_key
from ..models.ingest import IngestResult, IngestTextRequest
from ..services.file_extractor import ALLOWED_EXTENSIONS, extract_text
from ..services.ingest_service import ingest_image, ingest_text

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}

ALLOWED_MIME_TYPES = {
    "text/plain",
    "text/markdown",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

router = APIRouter(prefix="/api", dependencies=[Depends(verify_api_key)])


@router.post("/ingest/text", response_model=IngestResult)
async def ingest_text_endpoint(request: IngestTextRequest) -> IngestResult:
    result = await ingest_text(request.text, request.title, request.tags)
    return IngestResult(**result)


@router.post("/ingest/image", response_model=IngestResult)
async def ingest_image_endpoint(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    tags: str = Form(default=""),
) -> IngestResult:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Type non supporté: {file.content_type}. Formats acceptés: png, jpg, webp, gif",
        )
    image_bytes = await file.read()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    result = await ingest_image(image_bytes, file.filename or "image.png", title, tag_list)
    return IngestResult(**result)


@router.post("/ingest/file", response_model=IngestResult)
async def ingest_file_endpoint(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    tags: str = Form(default=""),
) -> IngestResult:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS or file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Type non supporté: {file.content_type}. Formats acceptés: .md, .txt, .pdf, .docx",
        )
    file_bytes = await file.read()
    try:
        text = await extract_text(file_bytes, file.filename or "")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not text.strip():
        raise HTTPException(status_code=422, detail="Aucun texte extractible")
    effective_title = title or Path(file.filename or "").stem
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    result = await ingest_text(text, effective_title, tag_list)
    return IngestResult(**result)
```

- [ ] **Step 4: Vérifier que les tests passent**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/backend
pytest tests/test_ingest.py -v
```

Résultat attendu : tous les tests PASSED (anciens + 4 nouveaux).

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/ingest.py backend/tests/test_ingest.py
git commit -m "feat: add POST /api/ingest/file endpoint"
```

---

## Task 3: Frontend composable ingestFile + test

**Files:**
- Modify: `frontend/composables/useIngest.ts`
- Modify: `frontend/tests/composables/useIngest.test.ts`

- [ ] **Step 1: Écrire le test échouant**

Remplacer le contenu de `frontend/tests/composables/useIngest.test.ts` :

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

const mockResult = { slug: 'imports--test', raw_path: '/raw/test.md', wiki_path: '/wiki/test.md', title: 'Test' }

const postFormSpy = vi.fn().mockResolvedValue(mockResult)

vi.mock('~/composables/useApi', () => ({
  useApi: () => ({
    post: vi.fn().mockResolvedValue(mockResult),
    postForm: postFormSpy,
    get: vi.fn(),
  }),
}))

vi.mock('#imports', () => ({
  useRuntimeConfig: () => ({ public: { apiBaseUrl: 'http://localhost:8088' } }),
  navigateTo: vi.fn(),
  ref: (v: unknown) => ({ value: v }),
}), { virtual: true })

describe('useIngest', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    postFormSpy.mockClear()
  })

  it('ingestText appelle /api/ingest/text et retourne le résultat', async () => {
    const { useIngest } = await import('~/composables/useIngest')
    const { result, ingestText } = useIngest()
    await ingestText('Mon texte', 'Mon titre', ['tag1'])
    expect(result.value?.slug).toBe('imports--test')
  })

  it('ingestImage appelle /api/ingest/image avec FormData', async () => {
    const { useIngest } = await import('~/composables/useIngest')
    const { result, ingestImage } = useIngest()
    const file = new File(['data'], 'test.png', { type: 'image/png' })
    await ingestImage(file, 'Image test', ['img'])
    expect(result.value?.slug).toBe('imports--test')
  })

  it('ingestFile appelle /api/ingest/file et déduit le title depuis file.name', async () => {
    const { useIngest } = await import('~/composables/useIngest')
    const { ingestFile } = useIngest()
    const file = new File(['contenu'], 'rapport-annuel.pdf', { type: 'application/pdf' })
    const result = await ingestFile(file, ['tag1'])
    expect(postFormSpy).toHaveBeenCalledWith('/api/ingest/file', expect.any(FormData))
    const form = postFormSpy.mock.calls[0][1] as FormData
    expect(form.get('title')).toBe('rapport-annuel')
    expect(result.slug).toBe('imports--test')
  })
})
```

- [ ] **Step 2: Vérifier que le test échoue**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/frontend
npm test -- tests/composables/useIngest.test.ts
```

Résultat attendu : FAILED — `ingestFile is not a function` ou destructuring error.

- [ ] **Step 3: Ajouter `ingestFile` dans `frontend/composables/useIngest.ts`**

Remplacer le contenu du fichier :

```typescript
import { ref } from 'vue'
import { useApi } from '~/composables/useApi'
import type { IngestResult } from '~/types/api'

export function useIngest() {
  const result = ref<IngestResult | null>(null)
  const loading = ref(false)
  const error = ref('')
  const { post, postForm } = useApi()

  async function ingestText(text: string, title: string, tags: string[]) {
    loading.value = true
    error.value = ''
    result.value = null
    try {
      result.value = await post<IngestResult>('/api/ingest/text', { text, title, tags })
    } catch {
      error.value = "Erreur lors de l'ingestion."
    } finally {
      loading.value = false
    }
  }

  async function ingestImage(file: File, title: string, tags: string[]) {
    loading.value = true
    error.value = ''
    result.value = null
    try {
      const form = new FormData()
      form.append('file', file)
      if (title) form.append('title', title)
      form.append('tags', tags.join(','))
      result.value = await postForm<IngestResult>('/api/ingest/image', form)
    } catch {
      error.value = "Erreur lors de l'ingestion."
    } finally {
      loading.value = false
    }
  }

  async function ingestFile(file: File, tags: string[]): Promise<IngestResult> {
    const form = new FormData()
    form.append('file', file)
    form.append('title', file.name.replace(/\.[^.]+$/, ''))
    form.append('tags', tags.join(','))
    return postForm<IngestResult>('/api/ingest/file', form)
  }

  function reset() {
    result.value = null
    error.value = ''
  }

  return { result, loading, error, ingestText, ingestImage, ingestFile, reset }
}
```

- [ ] **Step 4: Vérifier que les tests passent**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/frontend
npm test -- tests/composables/useIngest.test.ts
```

Résultat attendu : 3 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add frontend/composables/useIngest.ts frontend/tests/composables/useIngest.test.ts
git commit -m "feat: add ingestFile method to useIngest composable"
```

---

## Task 4: IngestFile.vue component

**Files:**
- Create: `frontend/components/ingest/IngestFile.vue`

- [ ] **Step 1: Créer `frontend/components/ingest/IngestFile.vue`**

```vue
<template>
  <div class="space-y-4">
    <div
      class="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors"
      :class="isDragging ? 'border-blue-500 bg-blue-950/20' : 'border-gray-700 hover:border-gray-600'"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
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
        v-for="(entry, i) in entries"
        :key="i"
        class="flex items-center justify-between text-sm rounded px-3 py-2 bg-gray-900"
      >
        <span class="text-gray-300 truncate max-w-xs">{{ entry.file.name }}</span>
        <span class="ml-4 shrink-0">
          <span v-if="entry.status === 'pending'" class="text-gray-500">en attente</span>
          <span v-else-if="entry.status === 'processing'" class="text-blue-400 animate-pulse">en cours...</span>
          <span v-else-if="entry.status === 'done'" class="text-green-400">
            ✓
            <NuxtLink :to="`/wiki/${entry.slug}`" class="ml-1 underline hover:text-white">
              {{ entry.slug }}
            </NuxtLink>
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
import { ref, computed } from 'vue'
import { FolderOpen } from 'lucide-vue-next'
import { useIngest } from '~/composables/useIngest'

interface FileEntry {
  file: File
  status: 'pending' | 'processing' | 'done' | 'error'
  slug?: string
  error?: string
}

const ALLOWED_EXTS = new Set(['.md', '.txt', '.pdf', '.docx'])
const MAX_SIZE = 10 * 1024 * 1024

const fileInput = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const tagsInput = ref('')
const entries = ref<FileEntry[]>([])
const rejectedMessage = ref('')

const isProcessing = computed(() => entries.value.some((e) => e.status === 'processing'))

const { ingestFile } = useIngest()

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
    if (!entries.value.some((e) => e.file.name === file.name)) {
      entries.value.push({ file, status: 'pending' })
    }
  }
  rejectedMessage.value = rejected.length ? `Fichiers rejetés : ${rejected.join(', ')}` : ''
}

function onDrop(e: DragEvent) {
  isDragging.value = false
  if (e.dataTransfer?.files) addFiles(e.dataTransfer.files)
}

function onFileInput(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files) addFiles(input.files)
  input.value = ''
}

async function ingestAll() {
  const tags = tagsInput.value
    .split(',')
    .map((t) => t.trim())
    .filter(Boolean)
  for (const entry of entries.value) {
    if (entry.status !== 'pending') continue
    entry.status = 'processing'
    try {
      const result = await ingestFile(entry.file, tags)
      entry.status = 'done'
      entry.slug = result.slug
    } catch (err: unknown) {
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

- [ ] **Step 2: Vérifier que le build TypeScript ne contient pas d'erreurs**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/frontend
npx nuxi typecheck 2>&1 | head -30
```

Résultat attendu : 0 erreurs sur le nouveau fichier.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/ingest/IngestFile.vue
git commit -m "feat: add IngestFile component with drag-and-drop and per-file status"
```

---

## Task 5: Ajouter l'onglet Fichiers dans ingest.vue

**Files:**
- Modify: `frontend/pages/ingest.vue`

- [ ] **Step 1: Modifier `frontend/pages/ingest.vue`**

Remplacer le contenu complet du fichier :

```vue
<template>
  <div class="p-6 max-w-2xl mx-auto space-y-6">
    <h2 class="text-lg font-semibold text-white">Ingestion</h2>

    <div class="flex border-b border-gray-800">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        :class="[
          'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
          activeTab === tab.id
            ? 'border-blue-500 text-blue-400'
            : 'border-transparent text-gray-400 hover:text-white',
        ]"
        @click="activeTab = tab.id"
      >
        <component :is="tab.icon" class="inline w-4 h-4 mr-1" />
        {{ tab.label }}
      </button>
    </div>

    <IngestText v-if="activeTab === 'text'" />
    <IngestImage v-else-if="activeTab === 'image'" />
    <IngestFile v-else-if="activeTab === 'file'" />
  </div>
</template>

<script setup lang="ts">
import { FileText, ImageIcon, FolderOpen } from 'lucide-vue-next'
import IngestFile from '~/components/ingest/IngestFile.vue'

const activeTab = ref<'text' | 'image' | 'file'>('text')
const tabs = [
  { id: 'text' as const, label: 'Texte', icon: FileText },
  { id: 'image' as const, label: 'Image', icon: ImageIcon },
  { id: 'file' as const, label: 'Fichiers', icon: FolderOpen },
]
</script>
```

- [ ] **Step 2: Vérifier le build**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/frontend
npx nuxi typecheck 2>&1 | head -30
```

Résultat attendu : 0 erreurs.

- [ ] **Step 3: Lancer le frontend en dev pour tester l'onglet**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/frontend
npm run dev
```

Ouvrir `http://localhost:3000/ingest` et vérifier :
- L'onglet "Fichiers" est visible à côté de "Texte" et "Image"
- La zone drag-and-drop s'affiche au clic sur l'onglet
- Le champ Tags est présent
- Les boutons "Tout ingérer" et "Effacer" sont présents et désactivés si liste vide
- Ajouter un fichier .txt valide : apparaît dans la liste avec statut "en attente"
- Ajouter un .exe : rejeté avec message jaune
- Ajouter un fichier > 10 Mo : rejeté avec message jaune

- [ ] **Step 4: Commit**

```bash
git add frontend/pages/ingest.vue
git commit -m "feat: add Fichiers tab to ingest page"
```

---

## Task 6: Rebuild Docker et test end-to-end

**Files:** aucun fichier modifié — uniquement rebuild et test

- [ ] **Step 1: Rebuild les deux services Docker**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm
docker compose up -d --build openwikillm-api frontend
```

- [ ] **Step 2: Test end-to-end fichier .txt**

Ouvrir `http://localhost:3000/ingest`, onglet "Fichiers".
- Glisser un fichier .txt contenant du texte
- Cliquer "Tout ingérer"
- Vérifier que le statut passe à "en cours..." puis "✓ imports--<slug>"
- Cliquer le lien → vérifier que la page wiki s'ouvre avec le contenu ingéré

- [ ] **Step 3: Test end-to-end fichier .pdf**

Même test avec un PDF simple (1 page, texte extractible).

- [ ] **Step 4: Test erreur contrôlée**

Uploader un fichier .txt vide (seulement espaces).
Résultat attendu : statut "✗ Aucun texte extractible" sur ce fichier.
Les autres fichiers de la liste ne sont pas affectés.

---

## Notes de documentation

Après chaque commit de tâche, créer ou mettre à jour :
- `docs/dev-notes/2026-05-13-ingest-file-upload.md`
- `CHANGELOG.md`

Format dev-note attendu (CLAUDE.md) :
```md
# Ingest — Upload de fichiers

## Objectif
## Fichiers modifiés
## Décisions prises
## Implémentation
## Tests effectués
## Limites connues
## Prochaines étapes
```
