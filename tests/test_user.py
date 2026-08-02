from __future__ import annotations
import pandas as pd
import pytest
from src.legacy.user import User


@pytest.fixture
def user(pantry) -> User:
    return User(name="Test User", age=20, height_inches=71, weight_pounds=160, pantry=pantry)


def test_user_rejects_empty_name(pantry) -> None:
    with pytest.raises(ValueError, match="name cannot be empty"):
        User(name="", age=20, height_inches=71, weight_pounds=160, pantry=pantry)


def test_user_rejects_nonpositive_age(pantry) -> None:
    with pytest.raises(ValueError, match="Age must be greater than zero"):
        User(name="Test", age=0, height_inches=71, weight_pounds=160, pantry=pantry)


def test_accept_meal_deducts_servings(user: User, monkeypatch) -> None:
    monkeypatch.setattr(user, "save_pantry", lambda: None)
    user.accept_meal({"chicken": 1, "rice": 2})
    pantry_items = user.pantry.pantry_items.set_index("food_item_id")
    assert pantry_items.loc["chicken", "servings"] == pytest.approx(2)
    assert pantry_items.loc["rice", "servings"] == pytest.approx(3)


def test_accept_meal_updates_max_servings(user: User, monkeypatch) -> None:
    monkeypatch.setattr(user, "save_pantry", lambda: None)
    user.accept_meal({"chicken": 2})
    row = user.pantry.pantry_items.loc[user.pantry.pantry_items["food_item_id"] == "chicken"].iloc[
        0
    ]
    assert row["servings"] == pytest.approx(1)
    assert row["max_servings"] == pytest.approx(1)


def test_accept_meal_marks_depleted_food_unavailable(user: User, monkeypatch) -> None:
    monkeypatch.setattr(user, "save_pantry", lambda: None)
    user.accept_meal({"broccoli": 2})
    row = user.pantry.pantry_items.loc[user.pantry.pantry_items["food_item_id"] == "broccoli"].iloc[
        0
    ]
    assert row["servings"] == pytest.approx(0)
    assert bool(row["is_available"]) is False
    assert "Broccoli" not in user.pantry.available_items()


def test_accept_meal_rejects_empty_meal(user: User) -> None:
    with pytest.raises(ValueError, match="empty meal"):
        user.accept_meal({})


def test_accept_meal_rejects_unknown_food_without_mutation(user: User, monkeypatch) -> None:
    monkeypatch.setattr(user, "save_pantry", lambda: None)
    before = user.pantry.pantry_items.copy(deep=True)
    with pytest.raises(ValueError, match="no longer in the pantry"):
        user.accept_meal({"unknown_food": 1})
    pd.testing.assert_frame_equal(before, user.pantry.pantry_items)


def test_accept_meal_rejects_insufficient_servings_without_mutation(
    user: User, monkeypatch
) -> None:
    monkeypatch.setattr(user, "save_pantry", lambda: None)
    before = user.pantry.pantry_items.copy(deep=True)
    with pytest.raises(ValueError, match="only 3"):
        user.accept_meal({"chicken": 10})
    pd.testing.assert_frame_equal(before, user.pantry.pantry_items)


def test_accept_meal_validates_all_items_before_mutating(user: User, monkeypatch) -> None:
    """No servings should be removed if any item is invalid."""
    monkeypatch.setattr(user, "save_pantry", lambda: None)
    before = user.pantry.pantry_items.copy(deep=True)
    with pytest.raises(ValueError):
        user.accept_meal({"chicken": 1, "unknown_food": 1})
    pd.testing.assert_frame_equal(before, user.pantry.pantry_items)


def test_prompt_meal_constraints(user: User, monkeypatch) -> None:
    responses = iter(
        [
            "700",  # calories
            "50",  # protein
            "80",  # carbs
            "20",  # fat
            "y",  # sodium constraint?
            "900",  # sodium maximum
            "n",  # sugar constraint?
            "y",  # cost constraint?
            "8",  # cost maximum
        ]
    )

    monkeypatch.setattr("builtins.input", lambda _: next(responses))
    constraints = user._prompt_meal_constraints()
    assert constraints.calorie_goal == pytest.approx(700)
    assert constraints.protein_goal == pytest.approx(50)
    assert constraints.carbs_goal == pytest.approx(80)
    assert constraints.fat_goal == pytest.approx(20)
    assert constraints.sodium_max == pytest.approx(900)
    assert constraints.sugar_max is None
    assert constraints.cost_max == pytest.approx(8)


def test_view_available_items_handles_empty_pantry(food_catalog_df: pd.DataFrame, capsys) -> None:
    from src.legacy.pantry import Pantry

    empty_pantry = Pantry(food_catalog=food_catalog_df)
    user = User(name="Test User", age=20, height_inches=71, weight_pounds=160, pantry=empty_pantry)
    user.view_available_items()
    output = capsys.readouterr().out
    assert "pantry is currently empty" in output.lower()
