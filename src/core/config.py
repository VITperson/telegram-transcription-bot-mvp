from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    # Core
    ENV: str = "dev"
    LOG_LEVEL: str = "INFO"
    TZ: str = "UTC"

    # Web
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Telegram
    TELEGRAM_BOT_TOKEN: str

    # DB (MySQL default)
    DB_DIALECT: str = "mysql"  # or "postgres"
    DB_HOST: str = "mysql"
    DB_PORT: int = 3306
    DB_USER: str = "transcriber"
    DB_PASSWORD: str = "example"
    DB_NAME: str = "transcriber"

    # Postgres alt
    PG_HOST: str = "postgres"
    PG_PORT: int = 5432
    PG_USER: str = "postgres"
    PG_PASSWORD: str = "postgres"
    PG_DB: str = "transcriber"

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    # Whisper
    WHISPER_MODEL_SIZE: str = "base"
    WHISPER_COMPUTE_TYPE: str = "int8"  # int8, float16, etc.

    # OpenAI
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Payments
    PAYMENT_HMAC_SECRET: str = "changeme"

    # Free tier
    FREE_MAX_JOBS_PER_DAY: int = 3
    FREE_MAX_MINUTES_PER_JOB: int = 3

    def sqlalchemy_dsn(self) -> str:
        if self.DB_DIALECT.lower() == "postgres":
            return f"postgresql+asyncpg://{self.PG_USER}:{self.PG_PASSWORD}@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DB}"
        # Default MySQL
        return f"mysql+asyncmy://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

    def sqlalchemy_sync_dsn(self) -> str:
        if self.DB_DIALECT.lower() == "postgres":
            return f"postgresql+psycopg://{self.PG_USER}:{self.PG_PASSWORD}@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DB}"
        return f"mysql+mysqldb://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

    def redis_dsn(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]

