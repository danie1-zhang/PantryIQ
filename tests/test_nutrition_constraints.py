from __future__ import annotations
import pandas as pd
import pytest
from optimizer.nutrition_constraints import (NutritionConstraints, NutritionConstraintEvaluator)


@pytest.fixture
def evaluator(food_catalog_df: pd.DataFrame) -> NutritionConstraintEvaluator:
    return NutritionConstraintEvaluator(food_catalog_df)


def test_constraints_reject_nonpositive_required_goal() -> None:
    with pytest.raises(ValueError, match="calorie_goal must be greater than zero"):
        NutritionConstraints(
            calorie_goal=0,
            protein_goal=40,
            carbs_goal=50,
            fat_goal=20,
        )


def test_constraints_reject_negative_optional_maximum() -> None:
    with pytest.raises(ValueError, match="sodium_max cannot be negative"):
        NutritionConstraints(
            calorie_goal=500,
            protein_goal=40,
            carbs_goal=50,
            fat_goal=20,
            sodium_max=-1,
        )


def test_calculate_totals_for_one_meal(evaluator: NutritionConstraintEvaluator) -> None:
    meal = {"chicken": 1, "rice": 1, "broccoli": 1}
    totals = evaluator.calculate_totals(meal)
    assert totals["calories"] == pytest.approx(450)
    assert totals["protein_g"] == pytest.approx(48)
    assert totals["carbs_g"] == pytest.approx(55)
    assert totals["fat_g"] == pytest.approx(6)
    assert totals["sugar_g"] == pytest.approx(2)
    assert totals["sodium_mg"] == pytest.approx(135)
    assert totals["cost"] == pytest.approx(3.75)


def test_calculate_totals_supports_fractional_servings(evaluator: NutritionConstraintEvaluator) -> None:
    meal = {"chicken": 0.5, "rice": 1.5}
    totals = evaluator.calculate_totals(meal)
    assert totals["calories"] == pytest.approx(400)
    assert totals["protein_g"] == pytest.approx(26)
    assert totals["carbs_g"] == pytest.approx(67.5)
    assert totals["fat_g"] == pytest.approx(4)


def test_calculate_totals_rejects_empty_meal(evaluator: NutritionConstraintEvaluator) -> None:
    with pytest.raises(ValueError, match="Meal cannot be empty"):
        evaluator.calculate_totals({})


def test_calculate_totals_rejects_unknown_food(evaluator: NutritionConstraintEvaluator) -> None:
    with pytest.raises(ValueError, match="was not found"):
        evaluator.calculate_totals({"unknown_food": 1})


def test_calculate_totals_rejects_nonpositive_servings(evaluator: NutritionConstraintEvaluator) -> None:
    with pytest.raises(ValueError, match="must be greater than zero",):
        evaluator.calculate_totals({"chicken": 0})


def test_exact_target_meal_gets_full_core_scores(evaluator: NutritionConstraintEvaluator) -> None:
    meal = { "chicken": 1, "rice": 1, "broccoli": 1}

    constraints = NutritionConstraints(
        calorie_goal=450,
        protein_goal=48,
        carbs_goal=55,
        fat_goal=6,
    )

    result = evaluator.evaluate(meal=meal, constraints=constraints)
    assert result.is_feasible is True
    assert result.feasibility_score == pytest.approx(100)
    assert all(result.constraints_met.values())
    assert result.constraint_scores["calories"] == pytest.approx(100)
    assert result.constraint_scores["protein"] == pytest.approx(100)
    assert result.constraint_scores["carbs"] == pytest.approx(100)
    assert result.constraint_scores["fat"] == pytest.approx(100)


def test_protein_above_goal_is_not_penalized(evaluator: NutritionConstraintEvaluator) -> None:
    meal = {"chicken": 2, "rice": 1}

    constraints = NutritionConstraints(
        calorie_goal=600,
        protein_goal=40,
        carbs_goal=45,
        fat_goal=11,
    )

    result = evaluator.evaluate(meal=meal, constraints=constraints)
    assert result.totals["protein_g"] > constraints.protein_goal
    assert result.constraint_scores["protein"] == pytest.approx(100)
    assert result.constraints_met["protein"] is True


def test_calorie_over_and_under_are_penalized_symmetrically(evaluator: NutritionConstraintEvaluator) -> None:
    under_score = evaluator._closeness_score(actual=450, target=500)
    over_score = evaluator._closeness_score(actual=550, target=500)
    assert under_score == pytest.approx(over_score)


def test_calories_outside_tolerance_make_meal_infeasible(evaluator: NutritionConstraintEvaluator) -> None:
    constraints = NutritionConstraints(
        calorie_goal=600,
        protein_goal=40,
        carbs_goal=50,
        fat_goal=10,
    )

    result = evaluator.evaluate(meal={"chicken": 1, "rice": 1,}, constraints=constraints)
    assert result.totals["calories"] == pytest.approx(400)
    assert result.constraints_met["calories"] is False
    assert result.is_feasible is False


def test_optional_limits_are_checked(evaluator: NutritionConstraintEvaluator) -> None:
    constraints = NutritionConstraints(
        calorie_goal=450,
        protein_goal=40,
        carbs_goal=55,
        fat_goal=6,
        sodium_max=100,
        sugar_max=1,
        cost_max=3,
    )

    result = evaluator.evaluate(meal={"chicken": 1, "rice": 1, "broccoli": 1}, constraints=constraints)
    assert result.constraints_met["sodium"] is False
    assert result.constraints_met["sugar"] is False
    assert result.constraints_met["cost"] is False
    assert result.is_feasible is False


def test_optional_constraints_are_omitted_when_none(evaluator: NutritionConstraintEvaluator) -> None:
    constraints = NutritionConstraints(calorie_goal=450, protein_goal=40, carbs_goal=55, fat_goal=6,)
    result = evaluator.evaluate(meal={"chicken": 1, "rice": 1, "broccoli": 1}, constraints=constraints)
    assert "sodium" not in result.constraints_met
    assert "sugar" not in result.constraints_met
    assert "cost" not in result.constraints_met


def test_missing_required_food_column_raises_error(food_catalog_df: pd.DataFrame) -> None:
    invalid_data = food_catalog_df.drop(columns=["protein_g_per_serving"])
    with pytest.raises(ValueError, match="missing required columns"):
        NutritionConstraintEvaluator(invalid_data)


def test_duplicate_food_ids_raise_error(food_catalog_df: pd.DataFrame) -> None:
    duplicate = pd.concat([food_catalog_df, food_catalog_df.iloc[[0]],], ignore_index=True)
    with pytest.raises(ValueError, match="must be unique",):
        NutritionConstraintEvaluator(duplicate)