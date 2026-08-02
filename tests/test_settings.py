import pytest
from pydantic import ValidationError

from src.app.settings import Settings

SECRET = "test-secret-key-that-is-at-least-32-characters"


def test_settings_accept_postgresql_database_url() -> None:
    settings = Settings(
        _env_file=None,
        environment="development",
        database_url="postgresql+psycopg://user:password@localhost/nutrition_optimizer",
        jwt_secret_key=SECRET,
    )

    assert settings.environment == "development"
    assert settings.database_url.endswith("/nutrition_optimizer")


def test_settings_parse_comma_separated_cors_origins() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://user@localhost/nutrition_optimizer",
        cors_origins="http://localhost:5173, https://staging.example.com",
        jwt_secret_key=SECRET,
    )

    assert settings.cors_origins == ["http://localhost:5173", "https://staging.example.com"]


def test_settings_require_database_url() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_reject_non_postgresql_url() -> None:
    with pytest.raises(ValidationError, match="PostgreSQL connection URL"):
        Settings(
            _env_file=None,
            database_url="sqlite:///nutrition_optimizer.db",
            jwt_secret_key=SECRET,
        )


def test_environment_must_be_recognized() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="qa",
            database_url="postgresql+psycopg://user@localhost/nutrition_optimizer",
            jwt_secret_key=SECRET,
        )


def test_test_environment_requires_test_database() -> None:
    with pytest.raises(ValidationError, match="ending in '_test'"):
        Settings(
            _env_file=None,
            environment="test",
            database_url="postgresql+psycopg://user@localhost/nutrition_optimizer",
            jwt_secret_key=SECRET,
        )


def test_test_environment_accepts_test_database() -> None:
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url="postgresql+psycopg://user@localhost/nutrition_optimizer_test",
        jwt_secret_key=SECRET,
    )

    assert settings.environment == "test"


def test_settings_require_strong_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="at least 32"):
        Settings(
            _env_file=None,
            database_url="postgresql+psycopg://user@localhost/nutrition_optimizer",
            jwt_secret_key="too-short",
        )
