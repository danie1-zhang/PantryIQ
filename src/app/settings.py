from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


Environment = Literal["development", "test", "staging", "production"]
POSTGRESQL_SCHEMES = ("postgresql://", "postgresql+psycopg://")


class Settings(BaseSettings):
    """Validated application configuration loaded from the environment."""

    environment: Environment = "development"
    database_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith(POSTGRESQL_SCHEMES):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection URL")
        return value

    @model_validator(mode="after")
    def protect_test_environment(self) -> "Settings":
        database_name = self.database_url.rstrip("/").rsplit("/", 1)[-1].split("?", 1)[0]
        if self.environment == "test" and not database_name.endswith("_test"):
            raise ValueError("The test environment requires a database name ending in '_test'")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return one validated settings instance for the running process."""

    return Settings()
