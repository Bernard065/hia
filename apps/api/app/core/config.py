"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration values for the API service."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "HIA API"
    ENV: str = "development"

    DATABASE_URL: str = "postgresql+psycopg2://hia:hia@localhost:5432/hia"

    JWT_SECRET: str = "change-me-in-.env"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    REDIS_URL: str = "redis://localhost:6379/0"


settings = Settings()
