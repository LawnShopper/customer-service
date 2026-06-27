from functools import lru_cache
from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    sample_messages_path: str = "data/sample_messages.json"
    output_dir: str = "data/output"
    business_config_path: str = "config/lawn_shopper.yaml"
    gmail_credentials_path: str = "credentials/google_credentials.json"
    gmail_token_path: str = "data/gmail_token.json"
    tone_examples_path: str = "data/tone_examples.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def resolve_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return (PROJECT_ROOT / candidate).resolve()


def load_business_config() -> dict:
    settings = get_settings()
    config_path = resolve_path(settings.business_config_path)
    with config_path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)
