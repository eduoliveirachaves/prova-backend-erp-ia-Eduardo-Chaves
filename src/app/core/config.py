from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ERP Backend Challenge"
    database_url: str = "postgresql+asyncpg://erp:erp@localhost:5432/erp"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me-in-env-please-32-characters"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    demo_username: str = "admin"
    demo_password: str = "admin123"
    low_stock_threshold: int = 10
    cache_ttl_seconds: int = 300

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
