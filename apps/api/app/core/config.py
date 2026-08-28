"""Application settings loaded from environment variables."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated configuration for the API service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str
    ENV: Literal["development", "test", "staging", "production"]

    DATABASE_URL: str
    REDIS_URL: str

    JWT_SECRET: str = Field(min_length=32)
    JWT_ALGORITHM: Literal["HS256"]
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(ge=1, le=60)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(ge=1, le=90)


settings = Settings()
