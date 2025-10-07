from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API
    API_TITLE: str = "Healthcare API"
    API_CORS_ORIGINS: str = "http://localhost:3000"

    # Mongo
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "myapp"

    # Auth
    JWT_SECRET: str = "change-me"
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_SALT_ROUNDS: int = 12

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "allow",
    }

    @field_validator("API_CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, v: str) -> str:
        # Comma-separated list of origins
        return v or ""


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


# PUBLIC_INTERFACE
def get_cors_origins() -> List[str]:
    """Return list of allowed CORS origins from comma-separated config value."""
    raw = settings.API_CORS_ORIGINS or ""
    return [x.strip() for x in raw.split(",") if x.strip()]
