from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["development", "test", "staging", "production"]
POSTGRESQL_SCHEMES = ("postgresql://", "postgresql+psycopg://")


class Settings(BaseSettings):
    """Validated application configuration loaded from the environment."""

    environment: Environment = "development"
    database_url: str
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    jwt_secret_key: SecretStr
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_expire_minutes: int = Field(default=15, ge=1, le=1440)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=90)
    auth_cookie_secure: bool = True
    auth_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    frontend_origin: str = "http://localhost:5173"
    llm_api_key: SecretStr | None = None
    llm_model: str = "gpt-4.1-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_timeout_seconds: float = Field(default=10, ge=1, le=60)
    llm_max_retries: int = Field(default=1, ge=0, le=3)

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

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def protect_test_environment(self) -> "Settings":
        database_name = self.database_url.rstrip("/").rsplit("/", 1)[-1].split("?", 1)[0]
        if self.environment == "test" and not database_name.endswith("_test"):
            raise ValueError("The test environment requires a database name ending in '_test'")
        if len(self.jwt_secret_key.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        if self.environment in {"staging", "production"} and not self.auth_cookie_secure:
            raise ValueError("AUTH_COOKIE_SECURE must be true outside development and test")
        if self.auth_cookie_samesite == "none" and not self.auth_cookie_secure:
            raise ValueError("SameSite=None cookies must be secure")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return one validated settings instance for the running process."""

    return Settings()
