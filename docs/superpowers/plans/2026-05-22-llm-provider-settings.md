# LLM Provider Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter la sélection du provider LLM (Ollama, OpenAI, Gemini, Anthropic, Custom) via une page `/settings` persistante côté serveur, avec redirection automatique au premier démarrage après login.

**Architecture:** Un `config.json` dans `data_path/` stocke la config active (persistée entre redémarrages). Le backend expose `LLMProvider` (ABC) implémentée par 5 providers, un `llm_service.py` factory dispatch vers le bon. `ollama_service.py` et `answer_service.py` deviennent des thin wrappers. Le frontend vérifie la config après login via `useState` (une seule requête par session) et redirige vers `/settings` si non configuré.

**Tech Stack:** Python 3.13, FastAPI, httpx, Pydantic v2, Nuxt 3, Vue 3, TypeScript, Tailwind CSS, Vitest

---

## Fichiers touchés

### Backend — Créés
| Fichier | Rôle |
|---------|------|
| `backend/app/models/settings.py` | Pydantic models : AppSettings, LLMConfig, OllamaConfig, OpenAIConfig, GeminiConfig, AnthropicConfig, CustomConfig, IngestConfig |
| `backend/app/core/config_store.py` | load() → AppSettings, save(AppSettings) → None |
| `backend/app/services/providers/__init__.py` | Package marker |
| `backend/app/services/providers/base.py` | LLMProvider ABC : generate(), generate_with_image() |
| `backend/app/services/providers/ollama.py` | Ollama via /api/generate |
| `backend/app/services/providers/openai_provider.py` | OpenAI via /v1/chat/completions |
| `backend/app/services/providers/custom_provider.py` | Custom OpenAI-compatible (base_url configurable) |
| `backend/app/services/providers/gemini_provider.py` | Gemini via generateContent |
| `backend/app/services/providers/anthropic_provider.py` | Anthropic via /v1/messages |
| `backend/app/services/llm_service.py` | Factory → instancie le bon provider depuis config |
| `backend/app/api/settings.py` | GET /api/settings, PUT /api/settings |
| `backend/tests/test_config_store.py` | Tests config_store |
| `backend/tests/test_providers.py` | Tests providers (httpx mocké) |
| `backend/tests/test_api_settings.py` | Tests API settings |

### Backend — Modifiés
| Fichier | Changement |
|---------|-----------|
| `backend/app/services/ollama_service.py` | Remplace appels httpx directs par `llm_service.get_provider()` |
| `backend/app/services/answer_service.py` | Supprime `call_ollama()`, utilise `llm_service.get_provider().generate()` |
| `backend/app/services/ingest_service.py` | Lit `max_text_chars` depuis `config_store.load()` au lieu de la constante module |
| `backend/app/main.py` | Enregistre `settings_router` |
| `backend/tests/test_ingest.py` | Met à jour `test_ingest_text_truncates_large_input` |

### Frontend — Créés
| Fichier | Rôle |
|---------|------|
| `frontend/composables/useSettings.ts` | fetchSettings(), saveSettings(), isConfigured() |
| `frontend/components/settings/LLMSettings.vue` | Sélecteur provider + champs dynamiques |
| `frontend/components/settings/IngestSettings.vue` | max_text_chars |
| `frontend/pages/settings.vue` | Page settings (mode setup + mode édition) |
| `frontend/tests/composables/useSettings.test.ts` | Tests useSettings |

### Frontend — Modifiés
| Fichier | Changement |
|---------|-----------|
| `frontend/types/api.ts` | Ajoute AppSettings et types LLM |
| `frontend/composables/useApi.ts` | Ajoute méthode put<T>() |
| `frontend/middleware/auth.global.ts` | Vérifie config LLM après auth (useState, une fois par session) |
| `frontend/components/layout/AppSidebar.vue` | Ajoute lien Settings (icône Settings lucide) |

---

## Task 1 : Pydantic models — `models/settings.py`

**Files:**
- Create: `backend/app/models/settings.py`

- [ ] **Step 1 : Écrire le test qui échoue**

```python
# backend/tests/test_config_store.py
from app.models.settings import (
    AppSettings, LLMConfig, OllamaConfig, OpenAIConfig,
    GeminiConfig, AnthropicConfig, CustomConfig, IngestConfig,
)

def test_app_settings_defaults():
    s = AppSettings()
    assert s.llm.provider == "ollama"
    assert s.llm.ollama.model == "mistral"
    assert s.llm.openai.api_key == ""
    assert s.ingest.max_text_chars == 30000

def test_app_settings_serializes_roundtrip():
    s = AppSettings()
    s.llm.provider = "openai"
    s.llm.openai.api_key = "sk-test"
    json_str = s.model_dump_json()
    s2 = AppSettings.model_validate_json(json_str)
    assert s2.llm.provider == "openai"
    assert s2.llm.openai.api_key == "sk-test"
```

- [ ] **Step 2 : Vérifier que le test échoue**

```bash
cd backend && python -m pytest tests/test_config_store.py::test_app_settings_defaults -v
```
Attendu : `FAILED — ModuleNotFoundError: No module named 'app.models.settings'`

- [ ] **Step 3 : Implémenter `backend/app/models/settings.py`**

```python
from typing import Literal
from pydantic import BaseModel


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

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
cd backend && python -m pytest tests/test_config_store.py::test_app_settings_defaults tests/test_config_store.py::test_app_settings_serializes_roundtrip -v
```
Attendu : `2 passed`

- [ ] **Step 5 : Commit**

```bash
git add backend/app/models/settings.py backend/tests/test_config_store.py
git commit -m "feat(settings): add AppSettings Pydantic models"
```

---

## Task 2 : Config store — `core/config_store.py`

**Files:**
- Create: `backend/app/core/config_store.py`
- Modify: `backend/tests/test_config_store.py`

- [ ] **Step 1 : Ajouter les tests dans `test_config_store.py`**

```python
# Ajouter à la fin de backend/tests/test_config_store.py
import tempfile
from pathlib import Path
from unittest.mock import patch
from app.core.config import settings as env_settings
from app.core import config_store

def test_load_returns_default_when_no_file():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(env_settings, "data_path", tmp):
            config = config_store.load()
    assert config.llm.provider == "ollama"
    assert config.llm.ollama.base_url == env_settings.ollama_base_url

def test_save_and_load_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(env_settings, "data_path", tmp):
            s = config_store.load()
            s.llm.provider = "openai"
            s.llm.openai.api_key = "sk-test"
            config_store.save(s)
            loaded = config_store.load()
    assert loaded.llm.provider == "openai"
    assert loaded.llm.openai.api_key == "sk-test"

def test_load_bootstraps_from_env():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(env_settings, "data_path", tmp), \
             patch.object(env_settings, "ollama_model", "llama3"):
            config = config_store.load()
    assert config.llm.ollama.model == "llama3"
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
cd backend && python -m pytest tests/test_config_store.py::test_load_returns_default_when_no_file -v
```
Attendu : `FAILED — cannot import name 'config_store' from 'app.core'`

- [ ] **Step 3 : Implémenter `backend/app/core/config_store.py`**

```python
from pathlib import Path
from ..models.settings import AppSettings, OllamaConfig, LLMConfig


def _path() -> Path:
    from .config import settings
    return Path(settings.data_path) / "config.json"


def load() -> AppSettings:
    from .config import settings
    p = _path()
    if p.exists():
        return AppSettings.model_validate_json(p.read_text(encoding="utf-8"))
    return AppSettings(
        llm=LLMConfig(
            ollama=OllamaConfig(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
                vision_model=settings.ollama_vision_model,
            )
        )
    )


def save(config: AppSettings) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(config.model_dump_json(indent=2), encoding="utf-8")
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
cd backend && python -m pytest tests/test_config_store.py -v
```
Attendu : `5 passed`

- [ ] **Step 5 : Commit**

```bash
git add backend/app/core/config_store.py backend/tests/test_config_store.py
git commit -m "feat(settings): add config_store (load/save config.json)"
```

---

## Task 3 : Provider base + Ollama — `providers/`

**Files:**
- Create: `backend/app/services/providers/__init__.py` (vide)
- Create: `backend/app/services/providers/base.py`
- Create: `backend/app/services/providers/ollama.py`
- Create: `backend/tests/test_providers.py`

- [ ] **Step 1 : Écrire les tests**

```python
# backend/tests/test_providers.py
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.providers.base import LLMProvider
from app.services.providers.ollama import OllamaProvider


def test_llmprovider_is_abstract():
    import inspect
    assert inspect.isabstract(LLMProvider)


def _mock_httpx(json_return: dict):
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = json_return
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp
    return mock_client, mock_resp


def test_ollama_generate():
    mock_client, _ = _mock_httpx({"response": "generated"})
    with patch("app.services.providers.ollama.httpx.AsyncClient") as MockCls:
        MockCls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockCls.return_value.__aexit__ = AsyncMock(return_value=None)
        provider = OllamaProvider("http://localhost:11434", "mistral", "llava")
        result = asyncio.run(provider.generate("hello"))
    assert result == "generated"
    mock_client.post.assert_called_once_with(
        "http://localhost:11434/api/generate",
        json={"model": "mistral", "prompt": "hello", "stream": False},
    )


def test_ollama_generate_with_image():
    mock_client, _ = _mock_httpx({"response": "image result"})
    with patch("app.services.providers.ollama.httpx.AsyncClient") as MockCls:
        MockCls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockCls.return_value.__aexit__ = AsyncMock(return_value=None)
        provider = OllamaProvider("http://localhost:11434", "mistral", "llava")
        result = asyncio.run(provider.generate_with_image("describe", "abc123"))
    assert result == "image result"
    call_kwargs = mock_client.post.call_args
    assert call_kwargs[1]["json"]["model"] == "llava"
    assert call_kwargs[1]["json"]["images"] == ["abc123"]
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
cd backend && python -m pytest tests/test_providers.py::test_llmprovider_is_abstract -v
```
Attendu : `FAILED — ModuleNotFoundError`

- [ ] **Step 3 : Implémenter les fichiers**

`backend/app/services/providers/__init__.py` (fichier vide)

`backend/app/services/providers/base.py` :
```python
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str: ...

    @abstractmethod
    async def generate_with_image(self, prompt: str, image_b64: str) -> str: ...
```

`backend/app/services/providers/ollama.py` :
```python
import httpx
from .base import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str, model: str, vision_model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.vision_model = vision_model

    async def generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            return response.json()["response"]

    async def generate_with_image(self, prompt: str, image_b64: str) -> str:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.vision_model,
                    "prompt": prompt,
                    "images": [image_b64],
                    "stream": False,
                },
            )
            response.raise_for_status()
            return response.json()["response"]
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
cd backend && python -m pytest tests/test_providers.py::test_llmprovider_is_abstract tests/test_providers.py::test_ollama_generate tests/test_providers.py::test_ollama_generate_with_image -v
```
Attendu : `3 passed`

- [ ] **Step 5 : Commit**

```bash
git add backend/app/services/providers/ backend/tests/test_providers.py
git commit -m "feat(settings): add LLMProvider ABC and OllamaProvider"
```

---

## Task 4 : Providers OpenAI + Custom

**Files:**
- Create: `backend/app/services/providers/openai_provider.py`
- Create: `backend/app/services/providers/custom_provider.py`
- Modify: `backend/tests/test_providers.py`

- [ ] **Step 1 : Ajouter les tests**

```python
# Ajouter à backend/tests/test_providers.py
from app.services.providers.openai_provider import OpenAIProvider
from app.services.providers.custom_provider import CustomProvider


def test_openai_generate():
    mock_client, _ = _mock_httpx(
        {"choices": [{"message": {"content": "answer"}}]}
    )
    with patch("app.services.providers.openai_provider.httpx.AsyncClient") as MockCls:
        MockCls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockCls.return_value.__aexit__ = AsyncMock(return_value=None)
        provider = OpenAIProvider("sk-test", "gpt-4o", "gpt-4o")
        result = asyncio.run(provider.generate("hello"))
    assert result == "answer"
    call_json = mock_client.post.call_args[1]["json"]
    assert call_json["model"] == "gpt-4o"
    assert call_json["messages"][0]["content"] == "hello"


def test_openai_generate_with_image():
    mock_client, _ = _mock_httpx(
        {"choices": [{"message": {"content": "img answer"}}]}
    )
    with patch("app.services.providers.openai_provider.httpx.AsyncClient") as MockCls:
        MockCls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockCls.return_value.__aexit__ = AsyncMock(return_value=None)
        provider = OpenAIProvider("sk-test", "gpt-4o", "gpt-4o")
        result = asyncio.run(provider.generate_with_image("describe", "b64data"))
    assert result == "img answer"
    content = mock_client.post.call_args[1]["json"]["messages"][0]["content"]
    assert isinstance(content, list)
    types = [item["type"] for item in content]
    assert "text" in types
    assert "image_url" in types


def test_custom_generate_uses_configured_base_url():
    mock_client, _ = _mock_httpx(
        {"choices": [{"message": {"content": "custom answer"}}]}
    )
    with patch("app.services.providers.custom_provider.httpx.AsyncClient") as MockCls:
        MockCls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockCls.return_value.__aexit__ = AsyncMock(return_value=None)
        provider = CustomProvider("https://openrouter.ai/api/v1", "sk-or", "mistral", "mistral")
        result = asyncio.run(provider.generate("hello"))
    assert result == "custom answer"
    url = mock_client.post.call_args[0][0]
    assert url == "https://openrouter.ai/api/v1/chat/completions"
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
cd backend && python -m pytest tests/test_providers.py::test_openai_generate -v
```
Attendu : `FAILED — ModuleNotFoundError: No module named 'app.services.providers.openai_provider'`

- [ ] **Step 3 : Implémenter les providers**

`backend/app/services/providers/openai_provider.py` :
```python
import httpx
from .base import LLMProvider

OPENAI_BASE = "https://api.openai.com/v1"


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, vision_model: str) -> None:
        self.api_key = api_key
        self.model = model
        self.vision_model = vision_model

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    async def generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                f"{OPENAI_BASE}/chat/completions",
                headers=self._headers(),
                json={"model": self.model, "messages": [{"role": "user", "content": prompt}]},
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

    async def generate_with_image(self, prompt: str, image_b64: str) -> str:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                f"{OPENAI_BASE}/chat/completions",
                headers=self._headers(),
                json={
                    "model": self.vision_model,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                        ],
                    }],
                },
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
```

`backend/app/services/providers/custom_provider.py` :
```python
import httpx
from .base import LLMProvider


class CustomProvider(LLMProvider):
    def __init__(self, base_url: str, api_key: str, model: str, vision_model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.vision_model = vision_model

    def _headers(self) -> dict:
        h = {}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    async def generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={"model": self.model, "messages": [{"role": "user", "content": prompt}]},
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

    async def generate_with_image(self, prompt: str, image_b64: str) -> str:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": self.vision_model,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                        ],
                    }],
                },
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
cd backend && python -m pytest tests/test_providers.py -v
```
Attendu : `6 passed`

- [ ] **Step 5 : Commit**

```bash
git add backend/app/services/providers/openai_provider.py backend/app/services/providers/custom_provider.py backend/tests/test_providers.py
git commit -m "feat(settings): add OpenAIProvider and CustomProvider"
```

---

## Task 5 : Providers Gemini + Anthropic

**Files:**
- Create: `backend/app/services/providers/gemini_provider.py`
- Create: `backend/app/services/providers/anthropic_provider.py`
- Modify: `backend/tests/test_providers.py`

- [ ] **Step 1 : Ajouter les tests**

```python
# Ajouter à backend/tests/test_providers.py
from app.services.providers.gemini_provider import GeminiProvider
from app.services.providers.anthropic_provider import AnthropicProvider


def test_gemini_generate():
    mock_client, _ = _mock_httpx(
        {"candidates": [{"content": {"parts": [{"text": "gemini answer"}]}}]}
    )
    with patch("app.services.providers.gemini_provider.httpx.AsyncClient") as MockCls:
        MockCls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockCls.return_value.__aexit__ = AsyncMock(return_value=None)
        provider = GeminiProvider("gemini-key", "gemini-1.5-pro", "gemini-1.5-pro")
        result = asyncio.run(provider.generate("hello"))
    assert result == "gemini answer"
    url = mock_client.post.call_args[0][0]
    assert "gemini-key" in url
    assert "gemini-1.5-pro" in url


def test_anthropic_generate():
    mock_client, _ = _mock_httpx(
        {"content": [{"text": "claude answer"}]}
    )
    with patch("app.services.providers.anthropic_provider.httpx.AsyncClient") as MockCls:
        MockCls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockCls.return_value.__aexit__ = AsyncMock(return_value=None)
        provider = AnthropicProvider("sk-ant-test", "claude-opus-4-7", "claude-opus-4-7")
        result = asyncio.run(provider.generate("hello"))
    assert result == "claude answer"
    headers = mock_client.post.call_args[1]["headers"]
    assert headers["x-api-key"] == "sk-ant-test"
    assert headers["anthropic-version"] == "2023-06-01"
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
cd backend && python -m pytest tests/test_providers.py::test_gemini_generate -v
```
Attendu : `FAILED — ModuleNotFoundError`

- [ ] **Step 3 : Implémenter les providers**

`backend/app/services/providers/gemini_provider.py` :
```python
import httpx
from .base import LLMProvider

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, vision_model: str) -> None:
        self.api_key = api_key
        self.model = model
        self.vision_model = vision_model

    async def generate(self, prompt: str) -> str:
        url = f"{GEMINI_BASE}/{self.model}:generateContent?key={self.api_key}"
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                url,
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
            response.raise_for_status()
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]

    async def generate_with_image(self, prompt: str, image_b64: str) -> str:
        url = f"{GEMINI_BASE}/{self.vision_model}:generateContent?key={self.api_key}"
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                url,
                json={
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}},
                        ]
                    }]
                },
            )
            response.raise_for_status()
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
```

`backend/app/services/providers/anthropic_provider.py` :
```python
import httpx
from .base import LLMProvider

ANTHROPIC_BASE = "https://api.anthropic.com/v1"
ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, vision_model: str) -> None:
        self.api_key = api_key
        self.model = model
        self.vision_model = vision_model

    def _headers(self) -> dict:
        return {"x-api-key": self.api_key, "anthropic-version": ANTHROPIC_VERSION}

    async def generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                f"{ANTHROPIC_BASE}/messages",
                headers=self._headers(),
                json={
                    "model": self.model,
                    "max_tokens": 4096,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            return response.json()["content"][0]["text"]

    async def generate_with_image(self, prompt: str, image_b64: str) -> str:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                f"{ANTHROPIC_BASE}/messages",
                headers=self._headers(),
                json={
                    "model": self.vision_model,
                    "max_tokens": 4096,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64}},
                            {"type": "text", "text": prompt},
                        ],
                    }],
                },
            )
            response.raise_for_status()
            return response.json()["content"][0]["text"]
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
cd backend && python -m pytest tests/test_providers.py -v
```
Attendu : `8 passed`

- [ ] **Step 5 : Commit**

```bash
git add backend/app/services/providers/gemini_provider.py backend/app/services/providers/anthropic_provider.py backend/tests/test_providers.py
git commit -m "feat(settings): add GeminiProvider and AnthropicProvider"
```

---

## Task 6 : LLM Service factory — `llm_service.py`

**Files:**
- Create: `backend/app/services/llm_service.py`
- Modify: `backend/tests/test_providers.py`

- [ ] **Step 1 : Ajouter les tests**

```python
# Ajouter à backend/tests/test_providers.py
import tempfile
from pathlib import Path
from unittest.mock import patch
from app.core.config import settings as env_settings
from app.core import config_store
from app.models.settings import AppSettings, LLMConfig
from app.services import llm_service
from app.services.providers.ollama import OllamaProvider
from app.services.providers.openai_provider import OpenAIProvider
from app.services.providers.gemini_provider import GeminiProvider
from app.services.providers.anthropic_provider import AnthropicProvider
from app.services.providers.custom_provider import CustomProvider


def _config_with_provider(provider_name: str, **kwargs) -> AppSettings:
    s = AppSettings()
    s.llm.provider = provider_name
    for k, v in kwargs.items():
        setattr(getattr(s.llm, provider_name), k, v)
    return s


def test_get_provider_returns_ollama_by_default():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(env_settings, "data_path", tmp):
            provider = llm_service.get_provider()
    assert isinstance(provider, OllamaProvider)


def test_get_provider_returns_openai():
    s = _config_with_provider("openai", api_key="sk-test")
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(env_settings, "data_path", tmp):
            config_store.save(s)
            provider = llm_service.get_provider()
    assert isinstance(provider, OpenAIProvider)


def test_get_provider_returns_custom():
    s = _config_with_provider("custom", base_url="https://openrouter.ai/api/v1")
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(env_settings, "data_path", tmp):
            config_store.save(s)
            provider = llm_service.get_provider()
    assert isinstance(provider, CustomProvider)
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
cd backend && python -m pytest tests/test_providers.py::test_get_provider_returns_ollama_by_default -v
```
Attendu : `FAILED — ModuleNotFoundError: No module named 'app.services.llm_service'`

- [ ] **Step 3 : Implémenter `backend/app/services/llm_service.py`**

```python
from ..core import config_store
from .providers.base import LLMProvider
from .providers.ollama import OllamaProvider
from .providers.openai_provider import OpenAIProvider
from .providers.gemini_provider import GeminiProvider
from .providers.anthropic_provider import AnthropicProvider
from .providers.custom_provider import CustomProvider


def get_provider() -> LLMProvider:
    config = config_store.load()
    llm = config.llm
    p = llm.provider
    if p == "ollama":
        return OllamaProvider(llm.ollama.base_url, llm.ollama.model, llm.ollama.vision_model)
    if p == "openai":
        return OpenAIProvider(llm.openai.api_key, llm.openai.model, llm.openai.vision_model)
    if p == "gemini":
        return GeminiProvider(llm.gemini.api_key, llm.gemini.model, llm.gemini.vision_model)
    if p == "anthropic":
        return AnthropicProvider(llm.anthropic.api_key, llm.anthropic.model, llm.anthropic.vision_model)
    if p == "custom":
        return CustomProvider(llm.custom.base_url, llm.custom.api_key, llm.custom.model, llm.custom.vision_model)
    raise ValueError(f"Provider inconnu : {p}")
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
cd backend && python -m pytest tests/test_providers.py -v
```
Attendu : `11 passed`

- [ ] **Step 5 : Commit**

```bash
git add backend/app/services/llm_service.py backend/tests/test_providers.py
git commit -m "feat(settings): add llm_service factory"
```

---

## Task 7 : Refactorer `ollama_service.py`

**Files:**
- Modify: `backend/app/services/ollama_service.py`

Aucun nouveau test requis ici : les tests existants `test_ingest.py` mockent déjà `compile_multi_page` et `identify_related_pages` au niveau service. On vérifie que la suite complète passe après refacto.

- [ ] **Step 1 : Remplacer le contenu de `backend/app/services/ollama_service.py`**

```python
import base64
import json
from . import llm_service

COMPILE_PROMPT = """\
Tu es un assistant qui structure des textes bruts en pages wiki Markdown.

Voici un texte brut à structurer :

---
{text}
---

Génère une page wiki Markdown avec ce format EXACT (frontmatter inclus) :

```markdown
---
title: {title}
type: concept
status: draft
confidence: medium
sources: []
updated_at: {date}
tags: {tags}
---

# {title}

## Résumé

## Règles connues

## Points à confirmer
```

Réponds UNIQUEMENT avec le Markdown, sans commentaire ni explication.
"""

IMAGE_PROMPT = """\
Tu es un assistant qui analyse des images et structure leur contenu en pages wiki Markdown.

Analyse cette image et génère une page wiki Markdown avec ce format EXACT (frontmatter inclus) :

```markdown
---
title: {title}
type: concept
status: draft
confidence: medium
sources: []
updated_at: {date}
tags: {tags}
---

# {title}

## Description visuelle
(Décris ce que tu vois : schéma, photo, diagramme, capture d'écran...)

## Texte extrait
(Tout le texte lisible dans l'image, mot pour mot)

## Points à confirmer
```

Réponds UNIQUEMENT avec le Markdown, sans commentaire ni explication.
"""

IDENTIFY_RELATED_PROMPT = """\
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
"""

MULTI_UPDATE_PROMPT = """\
Tu maintiens un wiki selon ce schéma :
{schema}

Nouveau document à intégrer :
Titre : {title} | Tags : {tags} | Date : {date}
{text}

Pages wiki existantes liées :
{related_pages}

Génère toutes les mises à jour nécessaires.
Pour chaque page à créer ou modifier, utilise ce format EXACT :

<page slug="{new_slug}">
[contenu complet de la page en Markdown avec frontmatter]
</page>

Règles :
- Crée une page principale pour le document source (slug : {new_slug}, type : concept)
- Si le document contient des concepts métier distincts, crée ou mets à jour les pages concept-- correspondantes (ex: concept--groove-tags, type : concept)
- Si le document mentionne des entités (personnes, fournisseurs, outils, systèmes), crée ou mets à jour les pages entity-- correspondantes (ex: entity--alizee, type : entity)
- Mets à jour les pages liées existantes : nouvelles informations, corrections, cross-refs [[slug]]
- N'inclus QUE les pages qui changent réellement
- Réponds UNIQUEMENT avec les balises <page>, sans commentaire
"""


def _strip_markdown_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        start = 1
        end = len(lines)
        if lines[-1].strip() == "```":
            end = -1
        return "\n".join(lines[start:end]).strip()
    return text


async def compile_image_to_markdown(
    image_bytes: bytes, title: str, tags: list[str], date: str
) -> str:
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    prompt = IMAGE_PROMPT.format(
        title=title,
        tags=json.dumps(tags, ensure_ascii=False),
        date=date,
    )
    provider = llm_service.get_provider()
    return _strip_markdown_fence(await provider.generate_with_image(prompt, image_b64))


async def compile_to_markdown(text: str, title: str, tags: list[str], date: str) -> str:
    prompt = COMPILE_PROMPT.format(
        text=text,
        title=title,
        tags=json.dumps(tags, ensure_ascii=False),
        date=date,
    )
    provider = llm_service.get_provider()
    return _strip_markdown_fence(await provider.generate(prompt))


async def identify_related_pages(text: str, title: str, index_content: str) -> list[str]:
    prompt = IDENTIFY_RELATED_PROMPT.format(
        title=title,
        text=text,
        index=index_content or "(index vide)",
    )
    provider = llm_service.get_provider()
    raw = (await provider.generate(prompt)).strip()
    try:
        slugs = json.loads(raw)
        if isinstance(slugs, list):
            return [s for s in slugs if isinstance(s, str)]
    except (json.JSONDecodeError, ValueError):
        pass
    return []


async def compile_multi_page(
    text: str,
    title: str,
    tags: list[str],
    date: str,
    schema: str,
    related_pages: dict[str, str],
    new_slug: str,
) -> str:
    pages_block = (
        "\n\n".join(f"=== {slug} ===\n{content}" for slug, content in related_pages.items())
        if related_pages
        else "(aucune page liée)"
    )
    prompt = MULTI_UPDATE_PROMPT.format(
        schema=schema,
        title=title,
        tags=json.dumps(tags, ensure_ascii=False),
        date=date,
        text=text,
        related_pages=pages_block,
        new_slug=new_slug,
    )
    provider = llm_service.get_provider()
    return await provider.generate(prompt)
```

- [ ] **Step 2 : Vérifier que les tests existants passent**

```bash
cd backend && python -m pytest tests/test_ingest.py -v
```
Attendu : tous les tests existants `PASSED` (les mocks patchent au-dessus de ollama_service)

- [ ] **Step 3 : Commit**

```bash
git add backend/app/services/ollama_service.py
git commit -m "refactor(settings): ollama_service delegates to llm_service provider"
```

---

## Task 8 : Refactorer `answer_service.py`

**Files:**
- Modify: `backend/app/services/answer_service.py`

- [ ] **Step 1 : Vérifier le test existant**

```bash
cd backend && python -m pytest tests/test_answer.py -v
```
Note: les tests actuels mockent `call_ollama`. Après refacto, il faut vérifier qu'ils passent encore.

- [ ] **Step 2 : Remplacer le contenu de `backend/app/services/answer_service.py`**

```python
from .search_service import search
from .wiki_service import list_pages
from . import llm_service
from ..models.answer import AnswerRequest, AnswerResponse

FALLBACK = "Je ne trouve pas cette information dans le wiki validé."

ANSWER_PROMPT = """\
Tu es un assistant qui répond à des questions à partir d'extraits de wiki.

Question : {question}

Extraits pertinents du wiki :
{context}

Réponds en te basant uniquement sur ces extraits. Si tu ne peux pas répondre, dis-le clairement.
"""


async def answer(request: AnswerRequest) -> AnswerResponse:
    results = search(request.question, limit=request.limit)

    if request.mode in ("strict", "validated_only"):
        all_pages = list_pages()
        validated_slugs = {p.slug for p in all_pages if p.status == "validated"}
        results = [r for r in results if r.slug in validated_slugs]

    if not results:
        return AnswerResponse(answer=FALLBACK, mode=request.mode, sources=[])

    context = "\n\n".join(f"[{r.title}]\n{r.snippet}" for r in results)
    prompt = ANSWER_PROMPT.format(question=request.question, context=context)
    llm_answer = await llm_service.get_provider().generate(prompt)

    return AnswerResponse(
        answer=llm_answer,
        mode=request.mode,
        sources=[r.slug for r in results],
    )
```

- [ ] **Step 3 : Mettre à jour `backend/tests/test_answer.py`**

Ouvrir `backend/tests/test_answer.py`. Remplacer tout mock sur `answer_service.call_ollama` par un mock sur `app.services.llm_service.get_provider` :

```python
# Dans chaque test qui mockait call_ollama, remplacer :
# patch("app.services.answer_service.call_ollama", new=AsyncMock(return_value="réponse"))
# par :
from unittest.mock import AsyncMock, MagicMock, patch

def _mock_provider(response: str):
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value=response)
    return mock_provider

# Dans le test :
with patch("app.services.answer_service.llm_service.get_provider", return_value=_mock_provider("réponse")):
    ...
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
cd backend && python -m pytest tests/test_answer.py -v
```
Attendu : tous `PASSED`

- [ ] **Step 5 : Commit**

```bash
git add backend/app/services/answer_service.py backend/tests/test_answer.py
git commit -m "refactor(settings): answer_service uses llm_service provider"
```

---

## Task 9 : API Settings — `api/settings.py` + `main.py`

**Files:**
- Create: `backend/app/api/settings.py`
- Create: `backend/tests/test_api_settings.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1 : Écrire les tests**

```python
# backend/tests/test_api_settings.py
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.core import config_store
from app.models.settings import AppSettings


def _client(tmp: str) -> TestClient:
    from unittest.mock import patch
    # monkeypatch via module-level: utiliser TestClient avec override via fixture
    return TestClient(app)


import pytest
from unittest.mock import patch


@pytest.fixture
def client_settings(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setattr(settings, "data_path", tmp)
        monkeypatch.setattr(settings, "api_key", "")
        yield TestClient(app)


def test_get_settings_returns_defaults(client_settings):
    response = client_settings.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["llm"]["provider"] == "ollama"
    assert data["ingest"]["max_text_chars"] == 30000


def test_get_settings_masks_api_key(client_settings, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_path", str(tmp_path))
    s = AppSettings()
    s.llm.provider = "openai"
    s.llm.openai.api_key = "sk-real-key"
    config_store.save(s)
    response = client_settings.get("/api/settings")
    assert response.json()["llm"]["openai"]["api_key"] == "****"


def test_put_settings_saves_and_returns(client_settings):
    payload = {
        "llm": {
            "provider": "openai",
            "ollama": {"base_url": "http://host.docker.internal:11434", "model": "mistral", "vision_model": "llava"},
            "openai": {"api_key": "sk-new", "model": "gpt-4o", "vision_model": "gpt-4o"},
            "gemini": {"api_key": "", "model": "gemini-1.5-pro", "vision_model": "gemini-1.5-pro"},
            "anthropic": {"api_key": "", "model": "claude-opus-4-7", "vision_model": "claude-opus-4-7"},
            "custom": {"base_url": "", "api_key": "", "model": "", "vision_model": ""},
        },
        "ingest": {"max_text_chars": 20000},
    }
    response = client_settings.put("/api/settings", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["llm"]["provider"] == "openai"
    assert data["llm"]["openai"]["api_key"] == "****"
    assert data["ingest"]["max_text_chars"] == 20000


def test_put_settings_preserves_existing_api_key_when_masked(client_settings, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_path", str(tmp_path))
    s = AppSettings()
    s.llm.openai.api_key = "sk-original"
    config_store.save(s)

    payload = {
        "llm": {
            "provider": "openai",
            "ollama": {"base_url": "", "model": "mistral", "vision_model": "llava"},
            "openai": {"api_key": "****", "model": "gpt-4o", "vision_model": "gpt-4o"},
            "gemini": {"api_key": "", "model": "gemini-1.5-pro", "vision_model": "gemini-1.5-pro"},
            "anthropic": {"api_key": "", "model": "claude-opus-4-7", "vision_model": "claude-opus-4-7"},
            "custom": {"base_url": "", "api_key": "", "model": "", "vision_model": ""},
        },
        "ingest": {"max_text_chars": 30000},
    }
    client_settings.put("/api/settings", json=payload)
    saved = config_store.load()
    assert saved.llm.openai.api_key == "sk-original"
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
cd backend && python -m pytest tests/test_api_settings.py::test_get_settings_returns_defaults -v
```
Attendu : `FAILED — 404 Not Found` (route pas encore enregistrée)

- [ ] **Step 3 : Créer `backend/app/api/settings.py`**

```python
from fastapi import APIRouter, Depends
from ..core.auth import verify_api_key
from ..core import config_store
from ..models.settings import AppSettings

router = APIRouter(prefix="/api", dependencies=[Depends(verify_api_key)])

_MASKED = "****"
_MASKED_PROVIDERS = ("openai", "gemini", "anthropic", "custom")


def _mask(s: AppSettings) -> AppSettings:
    data = s.model_dump()
    for p in _MASKED_PROVIDERS:
        if data["llm"][p]["api_key"]:
            data["llm"][p]["api_key"] = _MASKED
    return AppSettings.model_validate(data)


def _merge_keys(existing: AppSettings, incoming: AppSettings) -> AppSettings:
    data = incoming.model_dump()
    for p in _MASKED_PROVIDERS:
        if data["llm"][p]["api_key"] == _MASKED:
            data["llm"][p]["api_key"] = getattr(existing.llm, p).api_key
    return AppSettings.model_validate(data)


@router.get("/settings", response_model=AppSettings)
def get_settings() -> AppSettings:
    return _mask(config_store.load())


@router.put("/settings", response_model=AppSettings)
def update_settings(body: AppSettings) -> AppSettings:
    existing = config_store.load()
    merged = _merge_keys(existing, body)
    config_store.save(merged)
    return _mask(merged)
```

- [ ] **Step 4 : Enregistrer le router dans `backend/app/main.py`**

Ajouter dans `main.py` (après les imports existants) :
```python
from .api.settings import router as settings_router
```
Et dans la liste des `app.include_router(...)` :
```python
app.include_router(settings_router)
```

- [ ] **Step 5 : Vérifier que les tests passent**

```bash
cd backend && python -m pytest tests/test_api_settings.py -v
```
Attendu : `4 passed`

- [ ] **Step 6 : Commit**

```bash
git add backend/app/api/settings.py backend/app/main.py backend/tests/test_api_settings.py
git commit -m "feat(settings): add GET/PUT /api/settings endpoints"
```

---

## Task 10 : Mettre à jour `ingest_service.py`

**Files:**
- Modify: `backend/app/services/ingest_service.py`
- Modify: `backend/tests/test_ingest.py`

- [ ] **Step 1 : Mettre à jour le test de troncature dans `test_ingest.py`**

Trouver `test_ingest_text_truncates_large_input` et le remplacer par :

```python
def test_ingest_text_truncates_large_input(client_with_dirs):
    """Un texte dépassant max_text_chars doit être tronqué avant envoi au LLM."""
    from app.core import config_store
    from app.models.settings import AppSettings, IngestConfig
    captured = {}

    async def fake_compile(text, *args, **kwargs):
        captured["text"] = text
        return MOCK_XML

    # Vérifier la valeur par défaut depuis la config
    with patch("app.services.ingest_service.identify_related_pages", new=AsyncMock(return_value=[])), \
         patch("app.services.ingest_service.compile_multi_page", new=AsyncMock(side_effect=fake_compile)):
        client_with_dirs.post(
            "/api/ingest/text",
            json={"text": "A" * 40_000, "title": "Test", "tags": []},
        )
    assert len(captured["text"]) == 30000
```

- [ ] **Step 2 : Vérifier que le test passe encore**

```bash
cd backend && python -m pytest tests/test_ingest.py::test_ingest_text_truncates_large_input -v
```
Attendu : `PASSED` (l'ancienne constante vaut encore 30000)

- [ ] **Step 3 : Modifier `ingest_service.py`** pour lire depuis la config

Supprimer la ligne `MAX_TEXT_CHARS = 30_000` et modifier le début de `ingest_text` :

```python
# Supprimer:
# MAX_TEXT_CHARS = 30_000

# Dans ingest_text, remplacer :
# text = text[:MAX_TEXT_CHARS]
# par :
from ..core import config_store as _config_store

async def ingest_text(text: str, title: str | None, tags: list[str]) -> dict:
    start = time.monotonic()
    today = date.today().isoformat()
    effective_title = title or "Source sans titre"
    max_chars = _config_store.load().ingest.max_text_chars
    text = text[:max_chars]
    # ... reste inchangé
```

Attention : `config_store` doit être importé en tête de fichier, pas à l'intérieur de la fonction. Modifier les imports en haut du fichier :

```python
import re
import time
from pathlib import Path
from datetime import date
from .ollama_service import compile_image_to_markdown, identify_related_pages, compile_multi_page
from . import wiki_manager, schema_service, reference_service
from .search_service import rebuild_index
from ..core.config import settings
from ..core import config_store
```

Et le début de `ingest_text` :
```python
async def ingest_text(text: str, title: str | None, tags: list[str]) -> dict:
    start = time.monotonic()
    today = date.today().isoformat()
    effective_title = title or "Source sans titre"
    text = text[:config_store.load().ingest.max_text_chars]
    slug = _slugify(effective_title)
    # ... reste inchangé
```

- [ ] **Step 4 : Vérifier que tous les tests ingest passent**

```bash
cd backend && python -m pytest tests/test_ingest.py -v
```
Attendu : tous `PASSED`

- [ ] **Step 5 : Vérifier la suite complète**

```bash
cd backend && python -m pytest -v
```
Attendu : toute la suite `PASSED`

- [ ] **Step 6 : Commit**

```bash
git add backend/app/services/ingest_service.py backend/tests/test_ingest.py
git commit -m "feat(settings): ingest reads max_text_chars from config_store"
```

---

## Task 11 : Types frontend + méthode `put` dans `useApi`

**Files:**
- Modify: `frontend/types/api.ts`
- Modify: `frontend/composables/useApi.ts`

- [ ] **Step 1 : Ajouter les types dans `frontend/types/api.ts`**

À la fin du fichier, ajouter :

```typescript
export interface OllamaConfig {
  base_url: string
  model: string
  vision_model: string
}

export interface OpenAIConfig {
  api_key: string
  model: string
  vision_model: string
}

export interface GeminiConfig {
  api_key: string
  model: string
  vision_model: string
}

export interface AnthropicConfig {
  api_key: string
  model: string
  vision_model: string
}

export interface CustomConfig {
  base_url: string
  api_key: string
  model: string
  vision_model: string
}

export interface LLMConfig {
  provider: 'ollama' | 'openai' | 'gemini' | 'anthropic' | 'custom'
  ollama: OllamaConfig
  openai: OpenAIConfig
  gemini: GeminiConfig
  anthropic: AnthropicConfig
  custom: CustomConfig
}

export interface IngestConfig {
  max_text_chars: number
}

export interface AppSettings {
  llm: LLMConfig
  ingest: IngestConfig
}
```

- [ ] **Step 2 : Ajouter `put<T>()` dans `frontend/composables/useApi.ts`**

Après la fonction `patch`, avant `del`, ajouter :

```typescript
  async function put<T>(path: string, body: unknown): Promise<T> {
    return $fetch<T>(`${baseUrl}${path}`, {
      method: 'PUT',
      headers: headers({ 'Content-Type': 'application/json' }),
      body: body as Record<string, unknown>,
      onResponseError,
    })
  }
```

Mettre à jour le `return` pour inclure `put` :

```typescript
  return { get, post, postForm, patch, put, del }
```

- [ ] **Step 3 : Vérifier que le build TypeScript ne remonte pas d'erreurs**

```bash
cd frontend && npx nuxi typecheck 2>&1 | head -30
```
Attendu : pas d'erreur sur les fichiers modifiés

- [ ] **Step 4 : Commit**

```bash
git add frontend/types/api.ts frontend/composables/useApi.ts
git commit -m "feat(settings): add AppSettings types and useApi.put method"
```

---

## Task 12 : Composable `useSettings.ts`

**Files:**
- Create: `frontend/composables/useSettings.ts`
- Create: `frontend/tests/composables/useSettings.test.ts`

- [ ] **Step 1 : Écrire les tests**

```typescript
// frontend/tests/composables/useSettings.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// Mock useApi
const mockGet = vi.fn()
const mockPut = vi.fn()
vi.mock('~/composables/useApi', () => ({
  useApi: () => ({ get: mockGet, put: mockPut }),
}))
vi.mock('~/stores/auth', () => ({
  useAuthStore: () => ({ apiKey: '', isAuthenticated: true, loadFromStorage: vi.fn(), logout: vi.fn() }),
}))
vi.mock('#app', () => ({
  useRuntimeConfig: () => ({ public: { apiBaseUrl: 'http://localhost:8088' } }),
  navigateTo: vi.fn(),
  useState: (key: string, init: () => unknown) => {
    const { ref } = require('vue')
    return ref(init())
  },
}))

import { useSettings } from '~/composables/useSettings'
import type { AppSettings } from '~/types/api'

const defaultSettings: AppSettings = {
  llm: {
    provider: 'ollama',
    ollama: { base_url: 'http://localhost:11434', model: 'mistral', vision_model: 'llava' },
    openai: { api_key: '', model: 'gpt-4o', vision_model: 'gpt-4o' },
    gemini: { api_key: '', model: 'gemini-1.5-pro', vision_model: 'gemini-1.5-pro' },
    anthropic: { api_key: '', model: 'claude-opus-4-7', vision_model: 'claude-opus-4-7' },
    custom: { base_url: '', api_key: '', model: '', vision_model: '' },
  },
  ingest: { max_text_chars: 30000 },
}

describe('useSettings', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockGet.mockReset()
    mockPut.mockReset()
  })

  it('fetchSettings populates settings', async () => {
    mockGet.mockResolvedValue(defaultSettings)
    const { settings, fetchSettings } = useSettings()
    await fetchSettings()
    expect(settings.value).toEqual(defaultSettings)
  })

  it('isConfigured returns true for ollama with base_url', async () => {
    mockGet.mockResolvedValue(defaultSettings)
    const { fetchSettings, isConfigured } = useSettings()
    await fetchSettings()
    expect(isConfigured()).toBe(true)
  })

  it('isConfigured returns false for openai without api_key', async () => {
    const s = { ...defaultSettings, llm: { ...defaultSettings.llm, provider: 'openai' as const } }
    mockGet.mockResolvedValue(s)
    const { fetchSettings, isConfigured } = useSettings()
    await fetchSettings()
    expect(isConfigured()).toBe(false)
  })

  it('saveSettings calls PUT and updates settings', async () => {
    const updated = { ...defaultSettings, ingest: { max_text_chars: 20000 } }
    mockPut.mockResolvedValue(updated)
    const { settings, saveSettings } = useSettings()
    await saveSettings(updated)
    expect(mockPut).toHaveBeenCalledWith('/api/settings', updated)
    expect(settings.value?.ingest.max_text_chars).toBe(20000)
  })
})
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
cd frontend && npx vitest run tests/composables/useSettings.test.ts 2>&1 | tail -20
```
Attendu : `FAIL — Cannot find module '~/composables/useSettings'`

- [ ] **Step 3 : Créer `frontend/composables/useSettings.ts`**

```typescript
import type { AppSettings } from '~/types/api'

export function useSettings() {
  const { get, put } = useApi()
  const settings = ref<AppSettings | null>(null)
  const saving = ref(false)
  const saveError = ref<string | null>(null)

  async function fetchSettings(): Promise<void> {
    settings.value = await get<AppSettings>('/api/settings')
  }

  async function saveSettings(s: AppSettings): Promise<void> {
    saving.value = true
    saveError.value = null
    try {
      settings.value = await put<AppSettings>('/api/settings', s)
    } catch (e: unknown) {
      saveError.value = e instanceof Error ? e.message : 'Erreur lors de la sauvegarde'
      throw e
    } finally {
      saving.value = false
    }
  }

  function isConfigured(): boolean {
    if (!settings.value) return false
    const { provider } = settings.value.llm
    if (provider === 'ollama') return !!settings.value.llm.ollama.base_url
    if (provider === 'custom') return !!settings.value.llm.custom.base_url
    const cfg = settings.value.llm[provider as 'openai' | 'gemini' | 'anthropic']
    return !!cfg.api_key && cfg.api_key !== ''
  }

  return { settings, saving, saveError, fetchSettings, saveSettings, isConfigured }
}
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
cd frontend && npx vitest run tests/composables/useSettings.test.ts
```
Attendu : `4 passed`

- [ ] **Step 5 : Commit**

```bash
git add frontend/composables/useSettings.ts frontend/tests/composables/useSettings.test.ts
git commit -m "feat(settings): add useSettings composable"
```

---

## Task 13 : Middleware — vérification config LLM après login

**Files:**
- Modify: `frontend/middleware/auth.global.ts`

- [ ] **Step 1 : Remplacer le contenu de `frontend/middleware/auth.global.ts`**

```typescript
import { useAuthStore } from '~/stores/auth'
import type { AppSettings } from '~/types/api'

function _isLLMConfigured(s: AppSettings): boolean {
  const { provider } = s.llm
  if (provider === 'ollama') return !!s.llm.ollama.base_url
  if (provider === 'custom') return !!s.llm.custom.base_url
  const cfg = s.llm[provider as 'openai' | 'gemini' | 'anthropic']
  return !!cfg.api_key && cfg.api_key !== ''
}

export default defineNuxtRouteMiddleware(async (to) => {
  if (to.path === '/login' || to.path === '/settings') return

  const authStore = useAuthStore()
  authStore.loadFromStorage()

  if (!authStore.isAuthenticated) return navigateTo('/login')

  // Une seule vérification par session grâce à useState
  const llmReady = useState('llm-ready', () => false)
  if (llmReady.value) return

  try {
    const config = useRuntimeConfig()
    const baseUrl = config.public.apiBaseUrl as string
    const headers: Record<string, string> = {}
    if (authStore.apiKey) headers['X-API-Key'] = authStore.apiKey

    const s = await $fetch<AppSettings>(`${baseUrl}/api/settings`, { headers })
    llmReady.value = _isLLMConfigured(s)
  } catch {
    llmReady.value = true  // Ne pas bloquer si le fetch échoue
  }

  if (!llmReady.value) return navigateTo('/settings')
})
```

- [ ] **Step 2 : Vérifier que les tests auth existants passent**

```bash
cd frontend && npx vitest run tests/stores/auth.test.ts
```
Attendu : `PASSED`

- [ ] **Step 3 : Commit**

```bash
git add frontend/middleware/auth.global.ts
git commit -m "feat(settings): middleware redirects to /settings when LLM not configured"
```

---

## Task 14 : Composant `LLMSettings.vue`

**Files:**
- Create: `frontend/components/settings/LLMSettings.vue`

Note : dans Nuxt 3, `components/settings/LLMSettings.vue` s'importe automatiquement comme `<SettingsLLMSettings>`.

- [ ] **Step 1 : Créer `frontend/components/settings/LLMSettings.vue`** avec le contenu complet suivant :

```vue
<template>
  <div class="space-y-4">
    <!-- Sélecteur provider -->
    <div class="space-y-1">
      <label class="block text-xs text-gray-400 uppercase tracking-wider">Provider</label>
      <select
        v-model="local.provider"
        class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
        @change="emit('update:modelValue', { ...local })"
      >
        <option value="ollama">Ollama (local)</option>
        <option value="openai">OpenAI</option>
        <option value="gemini">Google Gemini</option>
        <option value="anthropic">Anthropic</option>
        <option value="custom">Custom (OpenAI-compatible)</option>
      </select>
    </div>

    <!-- Ollama -->
    <template v-if="local.provider === 'ollama'">
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">URL de base</label>
        <input v-model="local.ollama.base_url" placeholder="http://host.docker.internal:11434" :class="inputClass" @input="emit('update:modelValue', { ...local })" />
      </div>
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Modèle texte</label>
        <input v-model="local.ollama.model" placeholder="mistral" :class="inputClass" @input="emit('update:modelValue', { ...local })" />
      </div>
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Modèle vision</label>
        <input v-model="local.ollama.vision_model" placeholder="llava" :class="inputClass" @input="emit('update:modelValue', { ...local })" />
      </div>
    </template>

    <!-- OpenAI -->
    <template v-else-if="local.provider === 'openai'">
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Clé API</label>
        <div class="relative">
          <input v-model="local.openai.api_key" :type="showOpenAIKey ? 'text' : 'password'" placeholder="sk-..." :class="inputClass + ' pr-10'" @input="emit('update:modelValue', { ...local })" />
          <button type="button" class="absolute right-2 top-2 text-gray-400 hover:text-white" @click="showOpenAIKey = !showOpenAIKey">
            <Eye v-if="!showOpenAIKey" class="w-4 h-4" /><EyeOff v-else class="w-4 h-4" />
          </button>
        </div>
      </div>
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Modèle texte</label>
        <input v-model="local.openai.model" placeholder="gpt-4o" :class="inputClass" @input="emit('update:modelValue', { ...local })" />
      </div>
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Modèle vision</label>
        <input v-model="local.openai.vision_model" placeholder="gpt-4o" :class="inputClass" @input="emit('update:modelValue', { ...local })" />
      </div>
    </template>

    <!-- Gemini -->
    <template v-else-if="local.provider === 'gemini'">
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Clé API</label>
        <div class="relative">
          <input v-model="local.gemini.api_key" :type="showGeminiKey ? 'text' : 'password'" placeholder="AIza..." :class="inputClass + ' pr-10'" @input="emit('update:modelValue', { ...local })" />
          <button type="button" class="absolute right-2 top-2 text-gray-400 hover:text-white" @click="showGeminiKey = !showGeminiKey">
            <Eye v-if="!showGeminiKey" class="w-4 h-4" /><EyeOff v-else class="w-4 h-4" />
          </button>
        </div>
      </div>
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Modèle texte</label>
        <input v-model="local.gemini.model" placeholder="gemini-1.5-pro" :class="inputClass" @input="emit('update:modelValue', { ...local })" />
      </div>
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Modèle vision</label>
        <input v-model="local.gemini.vision_model" placeholder="gemini-1.5-pro" :class="inputClass" @input="emit('update:modelValue', { ...local })" />
      </div>
    </template>

    <!-- Anthropic -->
    <template v-else-if="local.provider === 'anthropic'">
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Clé API</label>
        <div class="relative">
          <input v-model="local.anthropic.api_key" :type="showAnthropicKey ? 'text' : 'password'" placeholder="sk-ant-..." :class="inputClass + ' pr-10'" @input="emit('update:modelValue', { ...local })" />
          <button type="button" class="absolute right-2 top-2 text-gray-400 hover:text-white" @click="showAnthropicKey = !showAnthropicKey">
            <Eye v-if="!showAnthropicKey" class="w-4 h-4" /><EyeOff v-else class="w-4 h-4" />
          </button>
        </div>
      </div>
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Modèle texte</label>
        <input v-model="local.anthropic.model" placeholder="claude-opus-4-7" :class="inputClass" @input="emit('update:modelValue', { ...local })" />
      </div>
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Modèle vision</label>
        <input v-model="local.anthropic.vision_model" placeholder="claude-opus-4-7" :class="inputClass" @input="emit('update:modelValue', { ...local })" />
      </div>
    </template>

    <!-- Custom -->
    <template v-else-if="local.provider === 'custom'">
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">URL de base</label>
        <input v-model="local.custom.base_url" placeholder="https://openrouter.ai/api/v1" :class="inputClass" @input="emit('update:modelValue', { ...local })" />
      </div>
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Clé API</label>
        <div class="relative">
          <input v-model="local.custom.api_key" :type="showCustomKey ? 'text' : 'password'" placeholder="sk-..." :class="inputClass + ' pr-10'" @input="emit('update:modelValue', { ...local })" />
          <button type="button" class="absolute right-2 top-2 text-gray-400 hover:text-white" @click="showCustomKey = !showCustomKey">
            <Eye v-if="!showCustomKey" class="w-4 h-4" /><EyeOff v-else class="w-4 h-4" />
          </button>
        </div>
      </div>
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Modèle texte</label>
        <input v-model="local.custom.model" placeholder="mistral" :class="inputClass" @input="emit('update:modelValue', { ...local })" />
      </div>
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Modèle vision (optionnel)</label>
        <input v-model="local.custom.vision_model" placeholder="" :class="inputClass" @input="emit('update:modelValue', { ...local })" />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { Eye, EyeOff } from 'lucide-vue-next'
import type { LLMConfig } from '~/types/api'

const props = defineProps<{ modelValue: LLMConfig }>()
const emit = defineEmits<{ 'update:modelValue': [LLMConfig] }>()

const inputClass = 'w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500'

const local = reactive(JSON.parse(JSON.stringify(props.modelValue)) as LLMConfig)
watch(() => props.modelValue, (v) => Object.assign(local, JSON.parse(JSON.stringify(v))), { deep: true })

const showOpenAIKey = ref(false)
const showGeminiKey = ref(false)
const showAnthropicKey = ref(false)
const showCustomKey = ref(false)
</script>
```

- [ ] **Step 2 : Vérifier la compilation TypeScript**

```bash
cd frontend && npx nuxi typecheck 2>&1 | head -20
```
Attendu : pas d'erreur TypeScript

- [ ] **Step 3 : Commit**

```bash
git add frontend/components/settings/LLMSettings.vue
git commit -m "feat(settings): add LLMSettings component"
```

---

## Task 15 : Composant `IngestSettings.vue`

**Files:**
- Create: `frontend/components/settings/IngestSettings.vue`

Note : s'importe automatiquement comme `<SettingsIngestSettings>` dans Nuxt 3.

- [ ] **Step 1 : Créer `frontend/components/settings/IngestSettings.vue`**

```vue
<template>
  <div class="space-y-4">
    <div class="space-y-1">
      <label class="block text-xs text-gray-400">Taille max du texte ingéré (caractères)</label>
      <input
        v-model.number="local.max_text_chars"
        type="number"
        min="1000"
        max="100000"
        step="1000"
        class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
        @input="emit('update:modelValue', { ...local })"
      />
      <p class="text-xs text-gray-500">Le texte sera tronqué à cette limite avant envoi au LLM. Défaut : 30 000.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import type { IngestConfig } from '~/types/api'

const props = defineProps<{ modelValue: IngestConfig }>()
const emit = defineEmits<{ 'update:modelValue': [IngestConfig] }>()
const local = reactive({ ...props.modelValue })
watch(() => props.modelValue, (v) => Object.assign(local, v))
</script>
```

- [ ] **Step 2 : Commit**

```bash
git add frontend/components/settings/IngestSettings.vue
git commit -m "feat(settings): add IngestSettings component"
```

---

## Task 16 : Page `settings.vue`

**Files:**
- Create: `frontend/pages/settings.vue`

- [ ] **Step 1 : Créer `frontend/pages/settings.vue`**

```vue
<template>
  <div class="max-w-2xl mx-auto py-10 px-6 space-y-8">
    <div>
      <h1 class="text-xl font-bold text-white">
        {{ isSetupMode ? 'Configuration initiale' : 'Paramètres' }}
      </h1>
      <p v-if="isSetupMode" class="text-sm text-gray-400 mt-1">
        Configurez votre provider LLM pour commencer à utiliser OpenWikiLLM.
      </p>
    </div>

    <div v-if="settings" class="space-y-8">
      <section class="p-4 bg-gray-900 border border-gray-800 rounded-xl space-y-4">
        <h2 class="text-sm font-semibold text-gray-300 uppercase tracking-wider">LLM</h2>
        <SettingsLLMSettings v-model="settings.llm" />
      </section>

      <section class="p-4 bg-gray-900 border border-gray-800 rounded-xl space-y-4">
        <h2 class="text-sm font-semibold text-gray-300 uppercase tracking-wider">Ingestion</h2>
        <SettingsIngestSettings v-model="settings.ingest" />
      </section>

      <div class="flex items-center gap-4">
        <button
          :disabled="saving"
          class="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
          @click="handleSave"
        >
          {{ saving ? 'Enregistrement…' : 'Enregistrer' }}
        </button>
        <p v-if="saved" class="text-green-400 text-sm">Paramètres enregistrés.</p>
        <p v-if="saveError" class="text-red-400 text-sm">{{ saveError }}</p>
      </div>
    </div>

    <div v-else class="text-gray-400 text-sm">Chargement…</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'

const { settings, saving, saveError, fetchSettings, saveSettings, isConfigured } = useSettings()
const router = useRouter()
const saved = ref(false)
const isSetupMode = computed(() => !isConfigured())

onMounted(async () => {
  await fetchSettings()
})

async function handleSave() {
  if (!settings.value) return
  saved.value = false
  const wasSetupMode = isSetupMode.value  // capturer AVANT la sauvegarde
  try {
    await saveSettings(settings.value)
    // Marquer LLM comme configuré dans le state global de session
    const llmReady = useState('llm-ready', () => false)
    llmReady.value = true
    saved.value = true
    if (wasSetupMode) {
      // Après setup initial, rediriger vers le chat
      await router.push('/chat')
    }
    // En mode édition, rester sur la page (saved.value affiche le message de confirmation)
  } catch {
    // saveError est géré dans useSettings
  }
}
</script>
```

- [ ] **Step 2 : Vérifier que le build TypeScript ne remonte pas d'erreurs**

```bash
cd frontend && npx nuxi typecheck 2>&1 | head -30
```

- [ ] **Step 3 : Commit**

```bash
git add frontend/pages/settings.vue
git commit -m "feat(settings): add /settings page (setup + edit mode)"
```

---

## Task 17 : Sidebar — lien Settings

**Files:**
- Modify: `frontend/components/layout/AppSidebar.vue`

- [ ] **Step 1 : Modifier `AppSidebar.vue`**

Dans les imports `<script setup>`, remplacer :
```typescript
import { BookOpen, MessageSquare, Library, Upload, PanelLeft, ScrollText } from 'lucide-vue-next'
```
par :
```typescript
import { BookOpen, MessageSquare, Library, Upload, PanelLeft, ScrollText, Settings } from 'lucide-vue-next'
```

Dans `navItems`, ajouter en dernier :
```typescript
const navItems = [
  { to: '/chat', icon: MessageSquare, label: 'Chat' },
  { to: '/wiki', icon: Library, label: 'Wiki' },
  { to: '/log', icon: ScrollText, label: 'Journal' },
  { to: '/ingest', icon: Upload, label: 'Ingest' },
  { to: '/settings', icon: Settings, label: 'Paramètres' },
]
```

- [ ] **Step 2 : Vérifier que les tests existants passent**

```bash
cd frontend && npx vitest run
```
Attendu : toute la suite `PASSED`

- [ ] **Step 3 : Commit**

```bash
git add frontend/components/layout/AppSidebar.vue
git commit -m "feat(settings): add Settings link in sidebar"
```

---

## Task 18 : Build Docker et vérification finale

- [ ] **Step 1 : Lancer la suite de tests backend complète**

```bash
cd backend && python -m pytest -v
```
Attendu : tous `PASSED`

- [ ] **Step 2 : Lancer la suite de tests frontend complète**

```bash
cd frontend && npx vitest run
```
Attendu : tous `PASSED`

- [ ] **Step 3 : Rebuild les images Docker**

```bash
./docker.sh build api
./docker.sh build front
```

- [ ] **Step 4 : Vérifier le flux complet en navigateur**

1. Aller sur `http://localhost:3000`
2. Se connecter
3. Vérifier la redirection automatique vers `/settings` (si pas de `config.json`)
4. Sélectionner "Ollama", renseigner l'URL, cliquer "Enregistrer"
5. Vérifier la redirection vers `/chat`
6. Naviguer vers `/settings` depuis la sidebar, vérifier que les valeurs sont pré-remplies
7. Changer le `max_text_chars`, sauvegarder, vérifier que l'ingest utilise la nouvelle valeur

- [ ] **Step 5 : Créer la note de dev**

```bash
# docs/dev-notes/2026-05-22-llm-provider-settings.md
```
Format attendu (voir CLAUDE.md) : Objectif, Fichiers modifiés, Décisions prises, Implémentation, Tests effectués, Limites connues, Prochaines étapes.

- [ ] **Step 6 : Mettre à jour CHANGELOG.md**

Ajouter une entrée pour cette feature.
