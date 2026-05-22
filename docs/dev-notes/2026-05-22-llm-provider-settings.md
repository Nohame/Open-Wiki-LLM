# LLM Provider Settings

## Objectif
Ajouter une page `/settings` permettant de configurer le provider LLM (Ollama, OpenAI, Gemini, Anthropic, Custom OpenAI-compatible) et les paramètres d'ingestion (`max_text_chars`), avec persistance dans `data_path/config.json` et redirection automatique au premier démarrage après login.

## Fichiers modifiés

### Backend — Créés
- `backend/app/models/settings.py` — Pydantic models : AppSettings, LLMConfig, *Config, IngestConfig
- `backend/app/core/config_store.py` — `load() / save()` sur `data_path/config.json`
- `backend/app/services/providers/` — LLMProvider ABC + 5 implémentations (Ollama, OpenAI, Gemini, Anthropic, Custom)
- `backend/app/services/llm_service.py` — factory `get_provider() -> LLMProvider`
- `backend/app/api/settings.py` — `GET/PUT /api/settings`
- `backend/tests/test_config_store.py`, `test_providers.py`, `test_api_settings.py`

### Backend — Modifiés
- `backend/app/services/ollama_service.py` — remplace httpx directs par `llm_service.get_provider()`
- `backend/app/services/answer_service.py` — supprime `call_ollama()`, utilise `llm_service.get_provider().generate()`
- `backend/app/services/ingest_service.py` — lit `max_text_chars` depuis `config_store.load()` au lieu de la constante module
- `backend/app/main.py` — enregistre `settings_router`

### Frontend — Créés
- `frontend/composables/useSettings.ts` — `fetchSettings`, `saveSettings`, `isConfigured`
- `frontend/components/settings/LLMSettings.vue` — sélecteur provider + champs dynamiques
- `frontend/components/settings/IngestSettings.vue` — champ max_text_chars
- `frontend/pages/settings.vue` — page settings (mode setup + mode édition)
- `frontend/tests/composables/useSettings.test.ts`

### Frontend — Modifiés
- `frontend/types/api.ts` — AppSettings et types LLM
- `frontend/composables/useApi.ts` — ajout `put<T>()`
- `frontend/middleware/auth.global.ts` — vérifie config LLM après auth, cache via `useState('llm-ready')`
- `frontend/components/layout/AppSidebar.vue` — lien Settings

## Décisions prises

- **Provider pattern** (ABC + factory) plutôt que if/else dans un seul fichier ou dépendance LiteLLM : isolation, testabilité, extensibilité
- **Lazy imports** dans `config_store` : `from .config import settings` à l'intérieur des fonctions pour compatibilité monkeypatch en tests
- **Bootstrap depuis .env** si `config.json` absent (rétrocompatibilité)
- **Masquage API key** : GET retourne `"****"` si non vide, PUT préserve la valeur existante si `"****"` reçu
- **`useState('llm-ready')`** : une seule requête `GET /api/settings` par session côté middleware

## Tests effectués

- Backend : 127 tests, tous passent
- Frontend : 23 tests, tous passent
- isConfigured() : ollama/custom → `base_url` non vide ; openai/gemini/anthropic → `api_key` non vide

## Limites connues

- Pas de bouton "Tester la connexion" (prévu v2)
- Les clés API sont en clair dans `config.json` — sécurité assurée par permissions volume Docker
- Plusieurs `config_store.load()` par ingest (acceptable MVP)
- `ollama_service.py` garde son nom malgré être devenu provider-agnostique

## Prochaines étapes

- Bouton "Tester la connexion" provider
- Logs d'erreur provider dans l'interface (502 avec message provider)
- Rotation des clés API
