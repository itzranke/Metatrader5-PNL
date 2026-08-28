"""Konfigurasi aplikasi via env vars (pydantic-settings).

Semua nilai penting diambil dari environment; tidak ada secret di kode.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "MT5 Journal API"
    environment: str = "development"  # development | staging | production
    api_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg://mt5:mt5@localhost:5432/mt5journal"
    redis_url: str = "redis://localhost:6379/0"

    allowed_origins: str = "http://localhost:5173"  # comma separated
    session_secret: str = "change-me-in-production"

    # Quota free tier (KEPUTUSAN-FINAL DR-17)
    max_accounts_per_user: int = 2
    max_trades_per_user: int = 10000

    # External services — kosong = nonaktif
    resend_api_key: str = ""
    telegram_bot_token: str = ""
    sentry_dsn: str = ""

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
