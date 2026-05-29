# Google Drive Connector Design

## Goal

Ajouter un connecteur Google Drive permettant à l'utilisateur de :
1. Configurer ses credentials OAuth dans la page Settings (section Connecteurs)
2. Parcourir ses fichiers/dossiers Drive depuis la page Ingest et déclencher l'ingestion — même pipeline que l'upload manuel existant

## Architecture

```
Settings page                   Ingest page
[Section Connecteurs]           [Onglet Google Drive]
  ↓ "Connecter"                   ↓ browse / ingest
GET /api/connectors/google-drive/auth-url
  ↓ redirect → Google OAuth
GET /api/connectors/google-drive/callback?code=...
  ↓ échange tokens → config.json
  ↓ redirect → /settings?connected=google-drive

                                GET /api/connectors/google-drive/files?folder_id=root
                                POST /api/connectors/google-drive/ingest
                                  ↓ download fichier Drive
                                  ↓ → pipeline ingest existant
```

**Stack :** Python / FastAPI / httpx (pas de SDK Google). Credentials et tokens OAuth stockés dans `config.json` via `config_store` (même mécanique que les clés API LLM). Scope Drive : `drive.readonly`.

---

## Backend

### Nouveaux fichiers

```
backend/app/
├── models/settings.py              ← ajout GoogleDriveConfig, ConnectorsConfig, AppSettings étendu
├── core/config.py                  ← ajout app_url (env OPENWIKILLM_APP_URL)
├── api/connectors.py               ← 5 routes
└── services/connectors/
    ├── __init__.py
    └── google_drive.py             ← OAuth + Drive API via httpx
```

### Modèles — `models/settings.py`

```python
class GoogleDriveConfig(BaseModel):
    client_id: str = ""
    client_secret: str = ""    # masqué "****" en GET
    access_token: str = ""     # masqué "****" en GET
    refresh_token: str = ""    # masqué "****" en GET
    token_expiry: str = ""     # ISO datetime, non masqué

class ConnectorsConfig(BaseModel):
    google_drive: GoogleDriveConfig = GoogleDriveConfig()

class AppSettings(BaseModel):
    llm: LLMConfig = LLMConfig()
    ingest: IngestConfig = IngestConfig()
    connectors: ConnectorsConfig = ConnectorsConfig()
```

### Config — `core/config.py`

Ajout d'un champ :
```python
app_url: str = Field(default="http://localhost:3000", validation_alias="OPENWIKILLM_APP_URL")
backend_url: str = Field(default="http://localhost:8088", validation_alias="OPENWIKILLM_BACKEND_URL")
```

Ajout dans `.env` :
```
OPENWIKILLM_APP_URL=http://localhost:3000
OPENWIKILLM_BACKEND_URL=http://localhost:8088
```

### `services/connectors/google_drive.py`

Toutes les interactions avec Google via `httpx.AsyncClient`. Pas de SDK.

**Constantes :**
```python
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_DRIVE_API = "https://www.googleapis.com/drive/v3"
SCOPES = "https://www.googleapis.com/auth/drive.readonly"
GOOGLE_DOCS_MIME = "application/vnd.google-apps.document"
EXPORT_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
SUPPORTED_MIMES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    GOOGLE_DOCS_MIME,
}
```

**Fonctions publiques :**

```python
def build_auth_url(client_id: str, redirect_uri: str) -> str:
    """Génère l'URL OAuth Google avec state aléatoire."""

async def exchange_code(code: str, client_id: str, client_secret: str, redirect_uri: str) -> GoogleDriveConfig:
    """Échange code → access_token + refresh_token. Retourne GoogleDriveConfig mis à jour."""

async def refresh_token_if_needed(cfg: GoogleDriveConfig) -> GoogleDriveConfig:
    """Rafraîchit le token si expiré dans moins de 60s. Retourne cfg éventuellement mis à jour."""

async def list_files(cfg: GoogleDriveConfig, folder_id: str = "root") -> list[dict]:
    """Liste fichiers et dossiers d'un dossier. Filtre sur SUPPORTED_MIMES + dossiers."""

async def download_file(cfg: GoogleDriveConfig, file_id: str, mime_type: str) -> tuple[bytes, str]:
    """Télécharge le fichier. Google Docs → export docx. Retourne (bytes, filename)."""
```

`refresh_token_if_needed` est appelé en tête de `list_files` et `download_file`. Si le token est rafraîchi, le nouveau `GoogleDriveConfig` est sauvegardé via `config_store.save()`.

### `api/connectors.py`

```
GET  /api/connectors/google-drive/auth-url    → { url: str }
GET  /api/connectors/google-drive/callback    → redirect vers {app_url}/settings?connected=google-drive
DELETE /api/connectors/google-drive           → efface access_token, refresh_token, token_expiry
GET  /api/connectors/google-drive/files       → { files: [...], folder_id: str }
POST /api/connectors/google-drive/ingest      → IngestResult
```

**`GET /auth-url` :**
- Vérifie que `client_id` et `client_secret` sont configurés, sinon 400
- Construit `redirect_uri = f"{settings.backend_url}/api/connectors/google-drive/callback"` où `backend_url` vient de `OPENWIKILLM_BACKEND_URL` (défaut : `http://localhost:8088`)
- Retourne `{ "url": build_auth_url(client_id, redirect_uri) }`

**`GET /callback` :**
- Si `?error=` présent → redirect vers `{app_url}/settings?error=google-drive-denied`
- Échange `code` → tokens via `exchange_code()`
- Fusionne dans la config existante, sauvegarde via `config_store.save()`
- Redirect → `{app_url}/settings?connected=google-drive`
- Ce endpoint ne nécessite **pas** `verify_api_key` (callback Google public)

**`GET /files?folder_id=root` :**
- Vérifie que `access_token` non vide, sinon 401
- Appelle `refresh_token_if_needed()` puis `list_files()`
- Retourne `{ "files": [...], "folder_id": folder_id }`

```python
# Structure de chaque fichier retourné
{
    "id": str,
    "name": str,
    "mimeType": str,
    "size": int | None,
    "modifiedTime": str,   # ISO datetime
    "isFolder": bool,
}
```

**`POST /ingest` :**
- Body : `{ "file_id": str, "title": str | None, "tags": list[str] }`
- `refresh_token_if_needed()` puis `download_file()` → `(bytes, filename)`
- Si taille > 10 Mo → 413
- Extrait le texte via `file_extractor.extract_text(bytes, filename)` existant
- Appelle `ingest_service.ingest_text(text, title, tags)` ou `ingest_service.ingest_image()` selon le type
- Retourne `IngestResult`

**`DELETE /google-drive` :**
- Efface `access_token`, `refresh_token`, `token_expiry` dans la config
- Conserve `client_id` et `client_secret`
- Sauvegarde et retourne 204

### Masquage `api/settings.py`

Extension de `_MASKED_PROVIDERS` existant : ajout masquage des champs `client_secret`, `access_token`, `refresh_token` dans `connectors.google_drive`. Même logique `"****"` : GET masque si non vide, PUT préserve si `"****"` reçu.

### Gestion d'erreurs backend

| Situation | Code | Message |
|-----------|------|---------|
| `client_id` / `client_secret` manquants | 400 | "Configurez d'abord vos credentials Google Drive" |
| Token absent à `/files` ou `/ingest` | 401 | "Session Google Drive expirée, reconnectez-vous" |
| Refresh token invalide | 401 | "Session Google Drive expirée, reconnectez-vous" |
| Fichier > 10 Mo | 413 | "Fichier trop volumineux (max 10 Mo)" |
| Type non supporté | 415 | "Type de fichier non supporté" |
| Erreur API Google | 502 | "Erreur Google Drive : {détail}" |

---

## Frontend

### Nouveaux fichiers

```
frontend/
├── components/settings/
│   └── ConnectorsSettings.vue     ← carte Google Drive
├── components/ingest/
│   └── GoogleDriveTab.vue         ← navigateur de fichiers
└── composables/
    └── useGoogleDrive.ts          ← listFiles(), ingestFile()
```

### Fichiers modifiés

- `frontend/types/api.ts` — ajout `GoogleDriveConfig`, `ConnectorsConfig`, `GoogleDriveFile`, `GoogleDriveListResponse`
- `frontend/pages/settings.vue` — ajout section "Connecteurs" avec `<SettingsConnectorsSettings>`
- `frontend/pages/ingest.vue` — ajout onglet "Google Drive" avec `<IngestGoogleDriveTab>`

### Types — `types/api.ts`

```typescript
export interface GoogleDriveConfig {
  client_id: string
  client_secret: string   // "****" si défini
  access_token: string    // "****" si défini
  refresh_token: string   // "****" si défini
  token_expiry: string
}

export interface ConnectorsConfig {
  google_drive: GoogleDriveConfig
}

// AppSettings étendu :
export interface AppSettings {
  llm: LLMConfig
  ingest: IngestConfig
  connectors: ConnectorsConfig
}

export interface GoogleDriveFile {
  id: string
  name: string
  mimeType: string
  size?: number
  modifiedTime: string
  isFolder: boolean
}

export interface GoogleDriveListResponse {
  files: GoogleDriveFile[]
  folder_id: string
}
```

### `useGoogleDrive.ts`

```typescript
export function useGoogleDrive() {
  const { get, post, del } = useApi()

  async function getAuthUrl(): Promise<string>          // GET /api/connectors/google-drive/auth-url → { url }
  async function disconnect(): Promise<void>            // DELETE /api/connectors/google-drive
  async function listFiles(folderId?: string): Promise<GoogleDriveListResponse>  // GET /api/connectors/google-drive/files
  async function ingestFile(fileId: string, title?: string, tags?: string[]): Promise<IngestResult>  // POST /api/connectors/google-drive/ingest

  return { getAuthUrl, disconnect, listFiles, ingestFile }
}
```

### `ConnectorsSettings.vue`

Reçoit `modelValue: ConnectorsConfig`, émet `update:modelValue`.

- Champ `client_id` (texte)
- Champ `client_secret` (password + toggle afficher/masquer)
- Badge statut : vert "Connecté" si `access_token` vaut `"****"` (non vide côté serveur), gris "Non connecté" sinon
- Bouton **"Connecter à Google Drive"** (visible si non connecté) :
  - Vérifie que `client_id` et `client_secret` non vides, sinon toast d'erreur "Enregistrez d'abord vos credentials Google"
  - Appelle `getAuthUrl()` → `window.location.href = url`
- Bouton **"Déconnecter"** (visible si connecté) → `disconnect()` → recharge les settings
- Au retour de l'OAuth (`?connected=google-drive` dans l'URL) : affiche toast succès, retire le query param

### `GoogleDriveTab.vue`

- Si `access_token` vide → message "Connectez Google Drive dans les Paramètres" + lien `/settings`
- Si connecté :
  - Breadcrumb : `Mon Drive > Dossier A > Dossier B`
  - Clic "Mon Drive" ou dossier ancêtre → navigation
  - Liste de fichiers : icône (📁 dossier / 📄 fichier), nom, date de modification
  - Clic dossier → `listFiles(folder.id)`, pousse dans le breadcrumb
  - Bouton "Ingérer" sur chaque fichier → `ingestFile(file.id, file.name)` → affiche `IngestResult` inline (même style que les onglets existants)
  - État loading par fichier pendant l'ingest

### `pages/settings.vue` — modification

Ajout d'une 3ème section après LLM et Ingestion :

```vue
<section class="p-4 bg-gray-900 border border-gray-800 rounded-xl space-y-4">
  <h2 class="text-sm font-semibold text-gray-300 uppercase tracking-wider">Connecteurs</h2>
  <SettingsConnectorsSettings v-model="settings.connectors" />
</section>
```

Détection du retour OAuth dans `onMounted` : si `route.query.connected === 'google-drive'` → toast succès + `router.replace('/settings')`.

### `pages/ingest.vue` — modification

Ajout d'un onglet "Google Drive" dans le système d'onglets existant. L'onglet n'est visible que si `settings.connectors.google_drive.access_token` vaut `"****"` (connecté) — sinon il apparaît grisé avec un tooltip "Non configuré".

---

## `config.json` — structure complète

```json
{
  "llm": { ... },
  "ingest": { "max_text_chars": 30000 },
  "connectors": {
    "google_drive": {
      "client_id": "xxx.apps.googleusercontent.com",
      "client_secret": "GOCSPX-...",
      "access_token": "ya29...",
      "refresh_token": "1//...",
      "token_expiry": "2026-05-29T14:30:00"
    }
  }
}
```

---

## Limites connues

- Un seul compte Google Drive par instance (pas de multi-compte)
- Pas de sync automatique (ingest manuel uniquement)
- Google Sheets, Slides, Forms non supportés (filtrés dans le listing)
- L'onglet Google Drive dans Ingest n'est pas visible si non connecté (pas de partial state)
- Les tokens sont en clair dans `config.json` — sécurité assurée par les permissions du volume Docker
