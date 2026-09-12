from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

import logging


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Farmer Market API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = (
        "postgresql+asyncpg://farmer_app:farmer_app@localhost:5432/farmer_market"
    )
    frontend_origin: str = "http://localhost:5173"
    jwt_secret: str = "development-only-secret-change-me"
    jwt_issuer: str = "farmer-market-api"
    jwt_audience: str = "farmer-market-admin"
    access_token_minutes: int = 15
    refresh_session_days: int = 7
    guest_session_days: int = 30
    cookie_secure: bool = False
    admin_email: str | None = None
    admin_password: str | None = None


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:     %(message)s",
)
logging.getLogger("farmer_market.requests").setLevel(logging.INFO)


@lru_cache
def get_settings() -> Settings:
    return Settings()
