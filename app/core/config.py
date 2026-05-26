"""
Application configuration loaded from environment variables.
Uses pydantic-settings for validation and type coercion.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    GOOGLE_MAPS_API_KEY: str
    APP_SECRET: str = "change-this-secret"
    JWT_EXP: int = 604800  # 1 week in seconds
    GOOGLE_CLIENT_ID: str = ""

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton — loaded once at startup."""
    return Settings()
