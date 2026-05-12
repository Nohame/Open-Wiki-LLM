from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="OPENWIKILLM_",
        extra="ignore",
    )

    app_env: str = "local"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8088

    raw_path: str = "/app/raw"
    wiki_path: str = "/app/wiki"
    data_path: str = "/app/data"

    ollama_base_url: str = Field(
        default="http://host.docker.internal:11434",
        validation_alias="OLLAMA_BASE_URL",
    )
    ollama_model: str = Field(
        default="mistral",
        validation_alias="OLLAMA_MODEL",
    )

    api_key: str = Field(
        default="",
        validation_alias="API_KEY",
    )


settings = Settings()
