from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import Engine, func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from scripts.seed_food_catalog import DEFAULT_CATALOG, seed_food_catalog
from src.database.models import Food, MealLog, MealLogItem, PantryItem, User


def make_user(**overrides: object) -> User:
    values = {
        "email": "person@example.com",
        "username": "person",
        "password_hash": "not-a-real-password-hash",
        "name": "Test Person",
    }
    values.update(overrides)
    return User(**values)


def make_food(**overrides: object) -> Food:
    values = {
        "external_source": "test",
        "external_id": "oats",
        "name": "Oats",
        "brand": "Generic",
        "category": "carbohydrate",
        "serving_size": Decimal("1"),
        "serving_unit": "cup",
        "calories": Decimal("150"),
        "protein": Decimal("5"),
        "carbs": Decimal("27"),
        "fat": Decimal("3"),
        "sugar": Decimal("1"),
        "fiber": Decimal("4"),
        "sodium": Decimal("2"),
        "cost_per_serving": Decimal("0.50"),
    }
    values.update(overrides)
    return Food(**values)


def make_meal_log(user: User, **overrides: object) -> MealLog:
    values = {
        "user": user,
        "eaten_at": datetime.now(UTC),
        "total_calories": Decimal("150"),
        "total_protein": Decimal("5"),
        "total_carbs": Decimal("27"),
        "total_fat": Decimal("3"),
        "total_sugar": Decimal("1"),
        "total_fiber": Decimal("4"),
        "total_sodium": Decimal("2"),
    }
    values.update(overrides)
    return MealLog(**values)


def test_initial_migration_creates_only_expected_tables(test_engine: Engine) -> None:
    tables = set(inspect(test_engine).get_table_names())

    assert tables == {
        "alembic_version",
        "foods",
        "meal_log_items",
        "meal_logs",
        "pantry_items",
        "users",
    }


def test_model_relationships_and_defaults(db_session: Session) -> None:
    user = make_user()
    food = make_food()
    pantry_item = PantryItem(
        user=user,
        food=food,
        servings_available=Decimal("4"),
        max_servings_per_meal=Decimal("2"),
    )
    meal_log = make_meal_log(user, rating=4)
    meal_item = MealLogItem(
        meal_log=meal_log,
        food=food,
        servings=Decimal("1"),
        food_name=food.name,
        calories_per_serving=food.calories,
        protein_per_serving=food.protein,
        carbs_per_serving=food.carbs,
        fat_per_serving=food.fat,
        sugar_per_serving=food.sugar,
        fiber_per_serving=food.fiber,
        sodium_per_serving=food.sodium,
    )
    db_session.add_all([pantry_item, meal_item])
    db_session.commit()

    assert pantry_item in user.pantry_items
    assert meal_log in user.meal_logs
    assert meal_item in meal_log.items
    assert pantry_item.is_available is True
    assert user.calorie_goal == Decimal("2000")
    assert user.created_at.tzinfo is not None


def test_unique_user_email_is_enforced(db_session: Session) -> None:
    db_session.add_all(
        [
            make_user(username="first"),
            make_user(username="second"),
        ]
    )

    with pytest.raises(IntegrityError):
        db_session.commit()


@pytest.mark.parametrize(
    ("record_factory", "overrides"),
    [
        (make_food, {"calories": Decimal("-1")}),
        (make_meal_log, {"rating": 6}),
    ],
)
def test_nutrition_and_rating_checks_are_enforced(
    db_session: Session,
    record_factory: object,
    overrides: dict[str, object],
) -> None:
    record = record_factory(**overrides) if record_factory is make_food else record_factory(make_user(), **overrides)
    db_session.add(record)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_pantry_serving_constraints_are_enforced(db_session: Session) -> None:
    item = PantryItem(
        user=make_user(),
        food=make_food(),
        servings_available=Decimal("1"),
        max_servings_per_meal=Decimal("2"),
    )
    db_session.add(item)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_deleting_user_cascades_but_keeps_food(db_session: Session) -> None:
    user = make_user()
    food = make_food()
    pantry_item = PantryItem(
        user=user,
        food=food,
        servings_available=Decimal("2"),
        max_servings_per_meal=Decimal("1"),
    )
    meal_log = make_meal_log(user)
    db_session.add_all([pantry_item, meal_log])
    db_session.commit()
    food_id = food.id

    db_session.delete(user)
    db_session.commit()

    assert db_session.scalar(select(func.count()).select_from(PantryItem)) == 0
    assert db_session.scalar(select(func.count()).select_from(MealLog)) == 0
    assert db_session.get(Food, food_id) is not None


def test_referenced_food_cannot_be_deleted(db_session: Session) -> None:
    food = make_food()
    db_session.add(
        PantryItem(
            user=make_user(),
            food=food,
            servings_available=Decimal("2"),
            max_servings_per_meal=Decimal("1"),
        )
    )
    db_session.commit()

    db_session.delete(food)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_food_seed_is_idempotent(test_session_factory: sessionmaker[Session]) -> None:
    first_result = seed_food_catalog(DEFAULT_CATALOG, test_session_factory)
    second_result = seed_food_catalog(DEFAULT_CATALOG, test_session_factory)

    with test_session_factory() as session:
        food_count = session.scalar(select(func.count()).select_from(Food))

    assert first_result == (51, 0)
    assert second_result == (0, 51)
    assert food_count == 51
