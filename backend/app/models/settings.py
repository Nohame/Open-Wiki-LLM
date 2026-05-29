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


class GoogleDriveConfig(BaseModel):
    client_id: str = ""
    client_secret: str = ""
    access_token: str = ""
    refresh_token: str = ""
    token_expiry: str = ""


class ConnectorsConfig(BaseModel):
    google_drive: GoogleDriveConfig = GoogleDriveConfig()


class AppSettings(BaseModel):
    llm: LLMConfig = LLMConfig()
    ingest: IngestConfig = IngestConfig()
    connectors: ConnectorsConfig = ConnectorsConfig()
