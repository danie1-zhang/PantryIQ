from collections.abc import Callable, Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from src.app.main import app
from src.database.models import Food, User
from src.database.session import get_db


@pytest.fixture(autouse=True)
def isolated_api_database(clean_test_database: None) -> Generator[None, None, None]:
    yield


@pytest.fixture
def api_session(test_session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    with test_session_factory() as session:
        yield session


@pytest.fixture
def client(test_session_factory: sessionmaker[Session]) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        with test_session_factory() as session:
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
