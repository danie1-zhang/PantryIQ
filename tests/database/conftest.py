from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from src.app.settings import Settings


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_ENV_FILE = PROJECT_ROOT / ".env.test"
TABLES = "meal_log_items, meal_logs, pantry_items, foods, users"


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    if not TEST_ENV_FILE.exists():
        pytest.fail(
            "Database tests require .env.test; copy .env.example and use a database ending in '_test'"
        )
    return Settings(_env_file=TEST_ENV_FILE)


@pytest.fixture(scope="session")
def test_engine(test_settings: Settings) -> Generator[Engine, None, None]:
    alembic_config = Config(PROJECT_ROOT / "alembic.ini")
    alembic_config.attributes["database_url"] = test_settings.database_url
    command.upgrade(alembic_config, "head")

    engine = create_engine(test_settings.database_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def test_session_factory(test_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=test_engine, class_=Session, expire_on_commit=False)


@pytest.fixture(autouse=True)
def clean_test_database(test_engine: Engine) -> Generator[None, None, None]:
    with test_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {TABLES} RESTART IDENTITY CASCADE"))
    yield
    with test_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {TABLES} RESTART IDENTITY CASCADE"))


@pytest.fixture
def db_session(test_session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    with test_session_factory() as session:
        yield session
