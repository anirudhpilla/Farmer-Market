from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Farmer Market API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://farmer_app:farmer_app@localhost:5432/farmer_market"
    frontend_origin: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()
