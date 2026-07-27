from __future__ import annotations
import pandas as pd
import pytest
from database.pantry import Pantry


def test_empty_pantry_has_no_items(food_catalog_df: pd.DataFrame) -> None:
    pantry = Pantry(food_catalog=food_catalog_df,)
    assert pantry.pantry_items.empty
    assert pantry.available_items() == []
    assert pantry.number_of_unique_items() == 0


def test_add_food_adds_valid_catalog_food(food_catalog_df: pd.DataFrame) -> None:
    pantry = Pantry(food_catalog=food_catalog_df)
    pantry.add_food(food_query="chicken", servings=3, max_servings=2, notes="Cooked chicken")

    assert pantry.number_of_unique_items() == 1
    assert pantry.available_items() == ["Chicken Breast"]

    row = pantry.pantry_items.iloc[0]

    assert row["food_item_id"] == "chicken"
    assert row["food_nm"] == "Chicken Breast"
    assert row["servings"] == pytest.approx(3)
    assert row["max_servings"] == pytest.approx(2)
    assert bool(row["is_available"]) is True
    assert row["notes"] == "Cooked chicken"


def test_add_food_can_find_food_by_name(food_catalog_df: pd.DataFrame) -> None:
    pantry = Pantry(food_catalog=food_catalog_df)
    pantry.add_food(food_query="white rice", servings=2, max_servings=1,)
    assert pantry.available_items() == ["White Rice"]


def test_add_food_is_case_insensitive(food_catalog_df: pd.DataFrame) -> None:
    pantry = Pantry(food_catalog=food_catalog_df)
    pantry.add_food(food_query="CHICKEN BREAST", servings=1, max_servings=1)
    assert pantry.available_items() == ["Chicken Breast"]


def test_add_unknown_food_raises_error(food_catalog_df: pd.DataFrame) -> None:
    pantry = Pantry(food_catalog=food_catalog_df)
    with pytest.raises(ValueError, match="not found"):
        pantry.add_food(food_query="lobster", servings=1, max_servings=1)


def test_add_food_rejects_nonpositive_servings(food_catalog_df: pd.DataFrame) -> None:
    pantry = Pantry(food_catalog=food_catalog_df)
    with pytest.raises(ValueError, match="servings must be greater than zero"):
        pantry.add_food(food_query="chicken", servings=0, max_servings=0)


def test_max_servings_cannot_exceed_available_servings(food_catalog_df: pd.DataFrame) -> None:
    pantry = Pantry(food_catalog=food_catalog_df)
    with pytest.raises(ValueError, match="max_servings cannot exceed",):
        pantry.add_food(food_query="chicken", servings=1, max_servings=2)


def test_adding_existing_food_increases_quantity(food_catalog_df: pd.DataFrame) -> None:
    pantry = Pantry(food_catalog=food_catalog_df)
    pantry.add_food(food_query="chicken", servings=2, max_servings=1)
    pantry.add_food(food_query="chicken", servings=3, max_servings=2)
    assert pantry.number_of_unique_items() == 1
    row = pantry.pantry_items.iloc[0]
    assert row["servings"] == pytest.approx(5)
    assert row["max_servings"] == pytest.approx(2)


def test_available_items_excludes_unavailable_foods(food_catalog_df: pd.DataFrame, pantry_df: pd.DataFrame) -> None:
    pantry_df.loc[pantry_df["food_item_id"] == "chicken", "is_available"] = False
    pantry = Pantry(food_catalog=food_catalog_df, pantry_items=pantry_df)
    assert "Chicken Breast" not in pantry.available_items()
    assert "White Rice" in pantry.available_items()


def test_available_items_excludes_zero_serving_foods(food_catalog_df: pd.DataFrame, pantry_df: pd.DataFrame) -> None:
    pantry_df.loc[pantry_df["food_item_id"] == "chicken", "servings"] = 0
    pantry_df.loc[pantry_df["food_item_id"] == "chicken", "max_servings"] = 0
    pantry = Pantry(food_catalog=food_catalog_df, pantry_items=pantry_df)
    assert "Chicken Breast" not in pantry.available_items()


def test_available_items_df_contains_nutrition_data(pantry: Pantry) -> None:
    foods = pantry.available_items_df()
    chicken = foods.loc[foods["food_item_id"] == "chicken"].iloc[0]
    assert chicken["servings"] == pytest.approx(3)
    assert chicken["calories_per_serving"] == pytest.approx(200)
    assert chicken["protein_g_per_serving"] == pytest.approx(40)


def test_items_with_dates_returns_expected_fields(pantry: Pantry) -> None:
    records = pantry.items_with_dates()
    assert len(records) == 5
    assert set(records[0]) == {"food_item_id", "food_nm", "date_added"}


def test_number_of_unique_items_counts_food_ids(pantry: Pantry) -> None:
    assert pantry.number_of_unique_items() == 5


def test_pantry_csv_round_trip(tmp_path, food_catalog_df: pd.DataFrame, pantry_df: pd.DataFrame) -> None:
    catalog_path = tmp_path / "food_catalog.csv"
    pantry_path = tmp_path / "test_pantry.csv"
    food_catalog_df.to_csv(catalog_path, index=False)
    original = Pantry(food_catalog=food_catalog_df, pantry_items=pantry_df, pantry_path=pantry_path)
    original.save()
    loaded = Pantry.from_csv(pantry_path=pantry_path, food_catalog_path=catalog_path)
    pd.testing.assert_frame_equal(original.pantry_items.reset_index(drop=True), loaded.pantry_items.reset_index(drop=True), check_dtype=False)