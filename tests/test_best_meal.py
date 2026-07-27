from __future__ import annotations
from collections.abc import Iterator
import pandas as pd
import pytest
from optimizer.best_meal import MealOptimizer
from optimizer.nutrition_constraints import NutritionConstraints


@pytest.fixture
def standard_constraints() -> NutritionConstraints:
    return NutritionConstraints(
        calorie_goal=450,
        protein_goal=40,
        carbs_goal=55,
        fat_goal=6,
        sodium_max=1000,
        sugar_max=20,
        cost_max=10,
    )


def test_optimizer_rejects_empty_available_pantry(optimizer_foods: pd.DataFrame, standard_constraints: NutritionConstraints) -> None:
    empty = optimizer_foods.iloc[0:0].copy()
    with pytest.raises(ValueError, match="does not contain any available foods"):
        MealOptimizer(pantry_foods=empty, constraints=standard_constraints)


def test_generate_candidate_respects_item_limit(optimizer_foods: pd.DataFrame, standard_constraints: NutritionConstraints) -> None:
    optimizer = MealOptimizer(pantry_foods=optimizer_foods, constraints=standard_constraints, random_seed=42, max_items_per_meal=4)
    candidate = optimizer.generate_candidate_meal()
    assert candidate is not None
    assert 1 <= len(candidate) <= 4


def test_generated_candidate_respects_serving_limits(optimizer_foods: pd.DataFrame, standard_constraints: NutritionConstraints) -> None:
    optimizer = MealOptimizer(pantry_foods=optimizer_foods, constraints=standard_constraints, random_seed=42)
    candidate = optimizer.generate_candidate_meal()
    assert candidate is not None
    foods_by_id = optimizer_foods.set_index("food_item_id")
    for food_item_id, servings in candidate.items():
        row = foods_by_id.loc[food_item_id]
        assert servings <= row["servings"]
        assert servings <= row["max_servings"]
        assert servings > 0


def test_generated_candidate_respects_total_serving_limit(optimizer_foods: pd.DataFrame, standard_constraints: NutritionConstraints) -> None:
    optimizer = MealOptimizer(pantry_foods=optimizer_foods, constraints=standard_constraints, random_seed=42, max_total_servings=4)
    candidate = optimizer.generate_candidate_meal()
    assert candidate is not None
    assert sum(candidate.values()) <= 4


def test_meal_with_only_proteins_is_invalid(optimizer_foods: pd.DataFrame, standard_constraints: NutritionConstraints) -> None:
    optimizer = MealOptimizer(pantry_foods=optimizer_foods, constraints=standard_constraints)
    meal = {"chicken": 1, "eggs": 2}
    assert optimizer._is_valid_meal_structure(meal) is False


def test_meal_with_protein_and_carb_is_valid(optimizer_foods: pd.DataFrame, standard_constraints: NutritionConstraints) -> None:
    optimizer = MealOptimizer(pantry_foods=optimizer_foods, constraints=standard_constraints)
    meal = {"chicken": 1, "rice": 1}
    assert optimizer._is_valid_meal_structure(meal) is True


def test_condiment_only_meal_is_invalid(optimizer_foods: pd.DataFrame, standard_constraints: NutritionConstraints) -> None:
    optimizer = MealOptimizer(pantry_foods=optimizer_foods, constraints=standard_constraints)
    assert (optimizer._is_valid_meal_structure({"sriracha": 1}) is False)


def test_find_best_meal_prefers_feasible_candidate(optimizer_foods: pd.DataFrame, standard_constraints: NutritionConstraints, monkeypatch) -> None:
    optimizer = MealOptimizer(pantry_foods=optimizer_foods, constraints=standard_constraints,)

    candidates: Iterator[dict[str, float]] = iter(
        [
            {
                "chicken": 1,
                "rice": 0.5,
            },
            {
                "chicken": 1,
                "rice": 1,
                "broccoli": 1,
            },
        ]
    )

    monkeypatch.setattr(optimizer, "generate_candidate_meal", lambda: next(candidates))
    result = optimizer.find_best_meal(number_of_candidates=2)
    assert result.evaluation.is_feasible is True
    assert result.meal == {"chicken": 1, "rice": 1,"broccoli": 1}


def test_find_best_meal_returns_near_feasible_when_needed(optimizer_foods: pd.DataFrame, monkeypatch) -> None:
    impossible_constraints = NutritionConstraints(
        calorie_goal=2000,
        protein_goal=200,
        carbs_goal=200,
        fat_goal=80,
    )

    optimizer = MealOptimizer(pantry_foods=optimizer_foods, constraints=impossible_constraints)

    candidates: Iterator[dict[str, float]] = iter(
        [
            {
                "chicken": 1,
                "rice": 1,
            },
            {
                "chicken": 2,
                "rice": 2,
                "broccoli": 1,
            },
        ]
    )

    monkeypatch.setattr(optimizer, "generate_candidate_meal", lambda: next(candidates))
    result = optimizer.find_best_meal(number_of_candidates=2)
    assert result.evaluation.is_feasible is False
    assert result.meal == {"chicken": 2, "rice": 2, "broccoli": 1}


def test_optimizer_is_reproducible_with_same_seed(optimizer_foods: pd.DataFrame, standard_constraints: NutritionConstraints) -> None:
    first = MealOptimizer(pantry_foods=optimizer_foods, constraints=standard_constraints, random_seed=123)
    second = MealOptimizer(pantry_foods=optimizer_foods, constraints=standard_constraints, random_seed=123)
    assert first.generate_candidate_meal() == second.generate_candidate_meal()


def test_find_best_meal_rejects_nonpositive_candidate_count(optimizer_foods: pd.DataFrame, standard_constraints: NutritionConstraints) -> None:
    optimizer = MealOptimizer(pantry_foods=optimizer_foods, constraints=standard_constraints,)
    with pytest.raises(ValueError, match="must be greater than zero"):
        optimizer.find_best_meal(number_of_candidates=0)