from functools import lru_cache
from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    business_config_path: str = "config/business.yaml"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_business_config(path: str | None = None) -> dict:
    settings = get_settings()
    config_path = Path(path or settings.business_config_path)

    if not config_path.is_absolute():
        config_path = (_project_root() / config_path).resolve()

    with config_path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)
