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
