from collections.abc import Callable, Generator
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from src.app.main import app
from src.app.settings import Settings
from src.database.models import Food, User
from src.database.session import get_db

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TABLES = "meal_log_items, meal_logs, pantry_items, foods, users"


@pytest.fixture(scope="session")
def api_engine() -> Generator[Engine, None, None]:
    settings = Settings(_env_file=PROJECT_ROOT / ".env.test")
    config = Config(PROJECT_ROOT / "alembic.ini")
    config.attributes["database_url"] = settings.database_url
    command.upgrade(config, "head")
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def api_session_factory(api_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=api_engine, class_=Session, expire_on_commit=False)


@pytest.fixture(autouse=True)
def clean_api_database(api_engine: Engine) -> Generator[None, None, None]:
    with api_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {TABLES} RESTART IDENTITY CASCADE"))
    yield
    with api_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {TABLES} RESTART IDENTITY CASCADE"))


@pytest.fixture
def api_session(api_session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    with api_session_factory() as session:
        yield session


@pytest.fixture
def client(api_session_factory: sessionmaker[Session]) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        with api_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def api_user(api_session: Session) -> User:
    user = User(
        email="api@example.com",
        username="development_user",
        password_hash="test-only",
        name="API User",
    )
    api_session.add(user)
    api_session.commit()
    return user


@pytest.fixture
def food_factory(api_session: Session) -> Callable[..., Food]:
    counter = 0

    def create_food(**overrides: object) -> Food:
        nonlocal counter
        counter += 1
        values = {
            "external_source": "api-test",
            "external_id": f"food-{counter}",
            "name": f"Food {counter}",
            "brand": "Generic",
            "category": "protein",
            "serving_size": Decimal("1"),
            "serving_unit": "serving",
            "calories": Decimal("100"),
            "protein": Decimal("20"),
            "carbs": Decimal("10"),
            "fat": Decimal("5"),
            "sugar": Decimal("1"),
            "fiber": Decimal("2"),
            "sodium": Decimal("50"),
            "cost_per_serving": Decimal("1.25"),
        }
        values.update(overrides)
        food = Food(**values)
        api_session.add(food)
        api_session.commit()
        return food

    return create_food
