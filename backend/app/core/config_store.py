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
