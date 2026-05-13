# OpenWikiLLM — Ingest File Upload Design

## Objectif

Ajouter un onglet "Fichiers" dans la page Ingest permettant d'uploader plusieurs fichiers à la fois (`.md`, `.txt`, `.pdf`, `.docx`) et de les ingérer séquentiellement avec un statut par fichier en temps réel.

## Architecture

**Approche :** endpoint unique `POST /api/ingest/file` + traitement séquentiel côté frontend. Réutilise le service `ingest_text` existant — aucune duplication de logique.

**Nouvelles dépendances backend :**
- `pdfplumber` — extraction texte PDF
- `python-docx` — extraction texte DOCX

## Backend

### Nouveau endpoint

`POST /api/ingest/file`

**Paramètres (multipart) :**
- `file` (UploadFile, requis) — fichier à ingérer
- `title` (str, optionnel) — déduit du nom de fichier si absent
- `tags` (str, défaut `""`) — tags séparés par virgule

**Réponse :** `IngestResult` (même modèle que `/api/ingest/text`)

**Types acceptés :**
```python
ALLOWED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx"}
ALLOWED_MIME_TYPES = {
    "text/plain",
    "text/markdown",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
```

Validation double : extension ET content-type. HTTP 415 si non supporté.

### Extracteurs de texte

Nouveau module `backend/app/services/file_extractor.py` :

```python
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
    # pdfplumber.open(BytesIO(data)) → itère pages → page.extract_text()
    # join toutes les pages avec "\n\n", strip final

def _extract_docx(data: bytes) -> str:
    # Document(BytesIO(data)) → [p.text for p in doc.paragraphs if p.text.strip()]
    # join avec "\n\n"
```

**Gestion d'erreurs extraction :**
- Fichier corrompu → `ValueError` remonté → HTTP 422 avec message clair
- Fichier vide après extraction → HTTP 422 "Aucun texte extractible"

### Flux backend

```
POST /api/ingest/file
  → validation extension + mime
  → lecture file.read()
  → extract_text(bytes, filename)
  → title = title or Path(filename).stem
  → tags = parse tags
  → ingest_text(text, title, tags)  ← service existant
  → return IngestResult
```

## Frontend

### Nouveau composant `IngestFile.vue`

Onglet "Fichiers" dans `pages/ingest.vue`. Gère son propre état local.

**Structure UI :**
```
[Zone drag & drop — multi-fichiers .md .txt .pdf .docx]
[Champ Tags — appliqués à tous les fichiers]

rapport-annuel.pdf    ● en cours...
procedure-retour.txt  ✓ imports--procedure-retour  → [voir]
fiche-produit.docx    ✗ Erreur : fichier corrompu

[Tout ingérer →]  [Effacer]
```

**État local par fichier :**
```typescript
interface FileEntry {
  file: File
  status: 'pending' | 'processing' | 'done' | 'error'
  slug?: string
  error?: string
}
```

**Comportement :**
- Drag & drop ou clic pour sélectionner (multiple)
- Validation extension côté client avant ajout à la liste (rejet silencieux avec message)
- Fichiers > 10 MB rejetés côté client
- Clic "Tout ingérer" → traitement séquentiel (await sur chaque fichier)
- Un fichier en erreur n'arrête pas les suivants
- Slug créé affiché comme lien cliquable vers `/wiki/{slug}`
- Bouton "Effacer" reset la liste (uniquement si aucun traitement en cours)

### Extension `useIngest.ts`

Ajout d'une méthode `ingestFile(file: File, tags: string[])` :
- Title déduit de `file.name` (sans extension)
- Appelle `postForm` vers `/api/ingest/file`
- Retourne `IngestResult`

### Modification `pages/ingest.vue`

Ajout d'un 3ème onglet :
```typescript
{ id: 'file' as const, label: 'Fichiers', icon: FolderOpen }
```

```vue
<IngestFile v-else-if="activeTab === 'file'" />
```

## Tests

### Backend
- `test_extract_txt` — extrait texte d'un .txt
- `test_extract_md` — extrait texte d'un .md
- `test_extract_pdf` — extrait texte d'un PDF simple
- `test_extract_docx` — extrait texte d'un .docx simple
- `test_extract_invalid` — ValueError sur extension inconnue
- `test_ingest_file_endpoint_txt` — POST /api/ingest/file avec .txt → IngestResult
- `test_ingest_file_endpoint_unsupported` — POST avec .exe → 415

### Frontend
- `useIngest.ingestFile` — mock useApi.postForm, vérifie title déduit du nom de fichier

## Limites connues (MVP)

- Pas d'extraction d'images dans les PDF/DOCX (texte uniquement)
- Pas de limite sur le nombre de fichiers par batch (pas de pagination)
- Fichiers > 10 MB rejetés côté client mais pas côté serveur (confiance navigateur)
- Encodage UTF-8 uniquement pour .txt/.md (pas de détection automatique d'encodage)
