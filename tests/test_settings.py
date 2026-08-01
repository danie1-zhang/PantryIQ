import pytest
from pydantic import ValidationError

from src.app.settings import Settings


def test_settings_accept_postgresql_database_url() -> None:
    settings = Settings(
        _env_file=None,
        environment="development",
        database_url="postgresql+psycopg://user:password@localhost/nutrition_optimizer",
    )

    assert settings.environment == "development"
    assert settings.database_url.endswith("/nutrition_optimizer")


def test_settings_require_database_url() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_reject_non_postgresql_url() -> None:
    with pytest.raises(ValidationError, match="PostgreSQL connection URL"):
        Settings(_env_file=None, database_url="sqlite:///nutrition_optimizer.db")


def test_environment_must_be_recognized() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="qa",
            database_url="postgresql+psycopg://user@localhost/nutrition_optimizer",
        )


def test_test_environment_requires_test_database() -> None:
    with pytest.raises(ValidationError, match="ending in '_test'"):
        Settings(
            _env_file=None,
            environment="test",
            database_url="postgresql+psycopg://user@localhost/nutrition_optimizer",
        )


def test_test_environment_accepts_test_database() -> None:
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url="postgresql+psycopg://user@localhost/nutrition_optimizer_test",
    )

    assert settings.environment == "test"
