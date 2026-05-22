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
