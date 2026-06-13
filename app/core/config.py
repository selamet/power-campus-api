"""Application configuration loaded from the environment."""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_DEFAULT_SECRET_KEY = "change-me-in-production"

Environment = Literal["local", "staging", "production"]


class Settings(BaseSettings):
    """Typed, validated settings sourced from environment variables / `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "Power Campus API"
    environment: Environment = "local"
    debug: bool = True

    # API
    api_v1_prefix: str = "/api/v1"
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Database
    database_url: str = "sqlite+aiosqlite:///./power_campus.db"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle_seconds: int = 1800

    # Security
    secret_key: str = _DEFAULT_SECRET_KEY
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 43_200  # 30 days

    # Seed
    seed_admin_email: str = "admin@powerakademi.com"
    seed_admin_password: str = "admin1234"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: str | list[str]) -> list[str]:
        """Accept a comma-separated string from the environment."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _guard_production(self) -> "Settings":
        """Refuse to boot a production environment with insecure defaults."""
        if self.environment == "production":
            if self.secret_key == _DEFAULT_SECRET_KEY:
                raise ValueError("SECRET_KEY must be set to a strong value in production.")
            if self.debug:
                raise ValueError("DEBUG must be disabled in production.")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


settings = get_settings()
