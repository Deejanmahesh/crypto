"""Application settings, loaded from environment / .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database. Default targets the docker-compose Postgres service.
    database_url: str = "postgresql+asyncpg://crypto:crypto@localhost:5432/crypto"

    # CoinGecko
    coingecko_base_url: str = "https://api.coingecko.com/api/v3"
    coingecko_api_key: str = ""

    # Ingestion behaviour
    top_n_assets: int = 10
    history_days: int = 30
    ingest_interval_minutes: int = 10
    ingest_on_startup: bool = True

    # CORS (comma-separated origins)
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
