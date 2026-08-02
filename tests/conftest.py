from __future__ import annotations
from collections.abc import Generator
from pathlib import Path

import pandas as pd
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from src.app.settings import Settings
from src.legacy.pantry import Pantry

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_ENV_FILE = PROJECT_ROOT / ".env.test"
DATABASE_TABLES = "meal_log_items, meal_logs, pantry_items, foods, users"


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    env_file = TEST_ENV_FILE if TEST_ENV_FILE.exists() else None
    return Settings(_env_file=env_file)


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


@pytest.fixture
def clean_test_database(test_engine: Engine) -> Generator[None, None, None]:
    with test_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {DATABASE_TABLES} RESTART IDENTITY CASCADE"))
    yield
    with test_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {DATABASE_TABLES} RESTART IDENTITY CASCADE"))


@pytest.fixture
def food_catalog_df() -> pd.DataFrame:
    "Return a small, predictable food catalog for tests."
    return pd.DataFrame(
        [
            {
                "food_item_id": "chicken",
                "food_nm": "Chicken Breast",
                "category": "protein",
                "serving_size": 1,
                "serving_unit": "serving",
                "calories_per_serving": 200,
                "protein_g_per_serving": 40,
                "carbs_g_per_serving": 0,
                "fat_g_per_serving": 5,
                "sugar_g_per_serving": 0,
                "sodium_mg_per_serving": 100,
                "cost_per_serving": 2.50,
                "source": "test",
            },
            {
                "food_item_id": "rice",
                "food_nm": "White Rice",
                "category": "carb",
                "serving_size": 1,
                "serving_unit": "cup",
                "calories_per_serving": 200,
                "protein_g_per_serving": 4,
                "carbs_g_per_serving": 45,
                "fat_g_per_serving": 1,
                "sugar_g_per_serving": 0,
                "sodium_mg_per_serving": 5,
                "cost_per_serving": 0.50,
                "source": "test",
            },
            {
                "food_item_id": "broccoli",
                "food_nm": "Broccoli",
                "category": "vegetable",
                "serving_size": 1,
                "serving_unit": "cup",
                "calories_per_serving": 50,
                "protein_g_per_serving": 4,
                "carbs_g_per_serving": 10,
                "fat_g_per_serving": 0,
                "sugar_g_per_serving": 2,
                "sodium_mg_per_serving": 30,
                "cost_per_serving": 0.75,
                "source": "test",
            },
            {
                "food_item_id": "eggs",
                "food_nm": "Eggs",
                "category": "eggs",
                "serving_size": 1,
                "serving_unit": "egg",
                "calories_per_serving": 70,
                "protein_g_per_serving": 6,
                "carbs_g_per_serving": 0,
                "fat_g_per_serving": 5,
                "sugar_g_per_serving": 0,
                "sodium_mg_per_serving": 70,
                "cost_per_serving": 0.30,
                "source": "test",
            },
            {
                "food_item_id": "sriracha",
                "food_nm": "Sriracha",
                "category": "condiment",
                "serving_size": 1,
                "serving_unit": "tbsp",
                "calories_per_serving": 15,
                "protein_g_per_serving": 0,
                "carbs_g_per_serving": 3,
                "fat_g_per_serving": 0,
                "sugar_g_per_serving": 2,
                "sodium_mg_per_serving": 400,
                "cost_per_serving": 0.10,
                "source": "test",
            },
        ]
    )


@pytest.fixture
def pantry_df() -> pd.DataFrame:
    "Return pantry inventory state without duplicated nutrition facts."
    return pd.DataFrame(
        [
            {
                "food_item_id": "chicken",
                "food_nm": "Chicken Breast",
                "servings": 3.0,
                "max_servings": 2.0,
                "is_available": True,
                "date_added": "2026-07-26",
                "notes": "",
            },
            {
                "food_item_id": "rice",
                "food_nm": "White Rice",
                "servings": 5.0,
                "max_servings": 3.0,
                "is_available": True,
                "date_added": "2026-07-26",
                "notes": "",
            },
            {
                "food_item_id": "broccoli",
                "food_nm": "Broccoli",
                "servings": 2.0,
                "max_servings": 2.0,
                "is_available": True,
                "date_added": "2026-07-26",
                "notes": "",
            },
            {
                "food_item_id": "eggs",
                "food_nm": "Eggs",
                "servings": 4.0,
                "max_servings": 3.0,
                "is_available": True,
                "date_added": "2026-07-26",
                "notes": "",
            },
            {
                "food_item_id": "sriracha",
                "food_nm": "Sriracha",
                "servings": 5.0,
                "max_servings": 1.0,
                "is_available": True,
                "date_added": "2026-07-26",
                "notes": "",
            },
        ]
    )


@pytest.fixture
def pantry(food_catalog_df: pd.DataFrame, pantry_df: pd.DataFrame) -> Pantry:
    return Pantry(food_catalog=food_catalog_df, pantry_items=pantry_df)


@pytest.fixture
def optimizer_foods(pantry: Pantry) -> pd.DataFrame:
    "Return pantry items joined to catalog nutrition data."
    return pantry.available_items_df()
