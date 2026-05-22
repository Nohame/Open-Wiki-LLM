# LLM Provider Settings Design

## Goal

Ajouter une page Settings permettant de configurer le provider LLM (Ollama, OpenAI, Gemini, Anthropic, Custom) et les paramètres d'ingestion, avec persistance dans un `config.json` côté serveur. La page apparaît en mode setup au premier démarrage (après login), et reste accessible depuis la navigation.

## Architecture

```
Démarrage frontend
   ↓ middleware auth.global.ts → non auth → /login
   ↓ auth ok → GET /api/settings → isConfigured() ?
   ↓ non configuré → /settings (mode setup)
   ↓ configuré → app normale
```

Le backend maintient un `config.json` dans `data_path/config.json`. Au premier démarrage, s'il n'existe pas, les valeurs sont bootstrappées depuis le `.env` actuel (rétrocompatibilité). Toute la logique LLM passe par une interface commune `LLMProvider` implémentée par chaque provider. Un `llm_service.py` factory lit la config et retourne le provider actif.

## Tech Stack

- Backend : Python / FastAPI / httpx (pas de SDK LLM externe)
- Frontend : Nuxt 3 / Vue 3 / Tailwind CSS
- Stockage config : JSON file dans volume Docker

---

## Backend

### Nouveaux fichiers

```
backend/app/
├── core/
│   └── config_store.py
├── services/
│   └── providers/
│       ├── base.py
│       ├── ollama.py
│       ├── openai_provider.py
│       ├── gemini_provider.py
│       ├── anthropic_provider.py
│       └── custom_provider.py
│   └── llm_service.py
├── models/
│   └── settings.py
└── api/
    └── settings.py
```

### `config_store.py`

Lit et écrit `config.json` dans `settings.data_path`. Si le fichier n'existe pas, retourne une config bootstrappée depuis les valeurs `.env`. N'écrit pas le fichier à la lecture — uniquement à la sauvegarde (`PUT /api/settings`).

### `providers/base.py`

Interface abstraite :

```python
class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str: ...

    @abstractmethod
    async def generate_with_image(self, prompt: str, image_b64: str) -> str: ...
```

### Providers

Chaque provider (`ollama.py`, `openai_provider.py`, `gemini_provider.py`, `anthropic_provider.py`, `custom_provider.py`) implémente `LLMProvider` via `httpx.AsyncClient`. Pas de SDK externe.

| Provider   | Endpoint                                                            | Auth             |
|------------|---------------------------------------------------------------------|------------------|
| Ollama     | `{base_url}/api/generate`                                           | aucune           |
| OpenAI     | `https://api.openai.com/v1/chat/completions`                        | `Bearer api_key` |
| Gemini     | `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` | `?key=api_key`   |
| Anthropic  | `https://api.anthropic.com/v1/messages`                             | `x-api-key`      |
| Custom     | `{base_url}/v1/chat/completions`                                    | `Bearer api_key` |

### `llm_service.py`

Factory qui lit la config active et instancie le bon provider :

```python
def get_provider() -> LLMProvider:
    config = config_store.load()
    provider_name = config.llm.provider
    provider_config = getattr(config.llm, provider_name)
    # instancie et retourne le bon provider
```

### `ollama_service.py` (refactor)

Les 4 fonctions existantes (`compile_to_markdown`, `compile_image_to_markdown`, `identify_related_pages`, `compile_multi_page`) sont conservées mais appellent désormais `llm_service.get_provider()`. Le fichier reste en place pour ne pas casser les imports existants.

### `models/settings.py`

```python
class OllamaConfig(BaseModel):
    base_url: str = "http://host.docker.internal:11434"
    model: str = "mistral"
    vision_model: str = "llava"

class OpenAIConfig(BaseModel):
    api_key: str = ""
    model: str = "gpt-4o"
    vision_model: str = "gpt-4o"

class GeminiConfig(BaseModel):
    api_key: str = ""
    model: str = "gemini-1.5-pro"
    vision_model: str = "gemini-1.5-pro"

class AnthropicConfig(BaseModel):
    api_key: str = ""
    model: str = "claude-opus-4-7"
    vision_model: str = "claude-opus-4-7"

class CustomConfig(BaseModel):
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    vision_model: str = ""

class LLMConfig(BaseModel):
    provider: Literal["ollama", "openai", "gemini", "anthropic", "custom"] = "ollama"
    ollama: OllamaConfig = OllamaConfig()
    openai: OpenAIConfig = OpenAIConfig()
    gemini: GeminiConfig = GeminiConfig()
    anthropic: AnthropicConfig = AnthropicConfig()
    custom: CustomConfig = CustomConfig()

class IngestConfig(BaseModel):
    max_text_chars: int = 30000

class AppSettings(BaseModel):
    llm: LLMConfig = LLMConfig()
    ingest: IngestConfig = IngestConfig()
```

### `api/settings.py`

```
GET  /api/settings  → AppSettings (clés API masquées "****" si définies)
PUT  /api/settings  → AppSettings → sauvegarde config.json, retourne AppSettings
```

Règle masquage : à la lecture, toute `api_key` non vide est remplacée par `"****"`.
Règle préservation : à l'écriture, si la valeur reçue est `"****"`, on conserve la valeur existante.

### Gestion d'erreurs backend

- `GET /api/settings` : si `config.json` absent → retourne config par défaut (sans écriture)
- `PUT /api/settings` : 422 si valeur invalide (Pydantic)
- Provider indisponible lors d'un ingest → 502 avec message précisant le provider (ex: `"Erreur OpenAI : 401 Invalid API key"`)

---

## Frontend

### Nouveaux fichiers

```
frontend/
├── pages/
│   └── settings.vue
├── components/settings/
│   ├── LLMSettings.vue
│   └── IngestSettings.vue
└── composables/
    └── useSettings.ts
```

### Fichiers modifiés

- `middleware/auth.global.ts` — après auth ok, appelle `useSettings().isConfigured()`. Si `false` → redirect `/settings`
- `components/layout/AppSidebar.vue` — ajout lien "Settings" avec icône `Settings` (lucide)
- `types/api.ts` — ajout types `AppSettings`, `LLMConfig`, `IngestConfig`, `OllamaConfig`, `OpenAIConfig`, `GeminiConfig`, `AnthropicConfig`, `CustomConfig`

### `useSettings.ts`

```typescript
const settings = ref<AppSettings | null>(null)

async function fetchSettings(): Promise<void>   // GET /api/settings
async function saveSettings(s: AppSettings): Promise<void>  // PUT /api/settings
function isConfigured(): boolean  // true si provider actif a base_url ou api_key non vide
```

### `pages/settings.vue`

Deux modes selon si `settings` existe déjà :
- **Mode setup** : titre "Configuration initiale", message d'invitation, pas de bouton retour
- **Mode édition** : titre "Paramètres", accès normal

Structure de la page :
1. Section "LLM" → `<SettingsLLMSettings>`
2. Section "Ingestion" → `<SettingsIngestSettings>`
3. Bouton "Enregistrer" → appelle `saveSettings()` → toast succès/erreur inline

### `LLMSettings.vue`

- Sélecteur de provider en haut (5 options)
- Champs dynamiques selon provider :
  - **Ollama** : `base_url`, `model`, `vision_model`
  - **OpenAI / Gemini / Anthropic** : `api_key` (type password + toggle), `model`, `vision_model`
  - **Custom** : `base_url`, `api_key` (type password + toggle), `model`, `vision_model`

### `IngestSettings.vue`

- Champ numérique `max_text_chars` (min: 1000, max: 100000, step: 1000)

### Règle `isConfigured()`

| Provider          | Condition                      |
|-------------------|-------------------------------|
| ollama / custom   | `base_url` non vide            |
| openai / gemini / anthropic | `api_key` non vide |

### Gestion d'erreurs frontend

- Si `GET /api/settings` échoue au démarrage → pas de blocage (évite boucle infinie de redirect)
- Toast inline après save (pas d'`alert()`)
- Champs `api_key` : `type="password"` avec bouton toggle afficher/masquer

---

## `config.json` — Structure complète

```json
{
  "llm": {
    "provider": "ollama",
    "ollama": {
      "base_url": "http://host.docker.internal:11434",
      "model": "mistral",
      "vision_model": "llava"
    },
    "openai": { "api_key": "", "model": "gpt-4o", "vision_model": "gpt-4o" },
    "gemini": { "api_key": "", "model": "gemini-1.5-pro", "vision_model": "gemini-1.5-pro" },
    "anthropic": { "api_key": "", "model": "claude-opus-4-7", "vision_model": "claude-opus-4-7" },
    "custom": { "base_url": "", "api_key": "", "model": "", "vision_model": "" }
  },
  "ingest": {
    "max_text_chars": 30000
  }
}
```

---

## Limites connues

- Pas de bouton "Tester la connexion" (v2)
- Les clés API sont en clair dans `config.json` — sécurité assurée par les permissions du volume Docker
- `ingest_service.py` lit `MAX_TEXT_CHARS` depuis la config au moment de chaque ingest (pas de cache)
