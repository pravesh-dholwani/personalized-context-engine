"""Tier 1 config: infrastructure settings loaded from the environment."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    port: int = 8000
    log_level: str = "info"

    user_service_url: str = "http://localhost:9101/users"
    kundli_service_url: str = "http://localhost:9102/kundli"
    horoscope_service_url: str = "http://localhost:9103/horoscope"
    panchang_service_url: str = "http://localhost:9104/panchang"

    http_timeout_seconds: float = 2.0
    http_max_retries: int = 2
    cache_ttl_seconds: int = 300

    openai_api_key: str | None = None

    config_dir: str = "config"


@lru_cache
def get_settings() -> Settings:
    return Settings()
