from __future__ import annotations

from decimal import Decimal

import pytest

from src.optimizer.cp_sat_optimizer import (
    COST_SCALE,
    NUTRITION_SCALE,
    CpSatMealOptimizer,
    scale_decimal,
    servings_to_units,
    units_to_servings,
    unscale_total,
)
from src.optimizer.models import OptimizerFood
from src.optimizer.nutrition_constraints import NutritionConstraints
from src.optimizer.service import optimize_meal


def optimizer_food(
    food_id: str,
    category: str,
    *,
    calories: str = "100",
    protein: str = "10",
    carbs: str = "10",
    fat: str = "5",
    sugar: str = "0",
    sodium: str = "0",
    cost: str = "1",
    available: str = "4",
    maximum: str = "3",
) -> OptimizerFood:
    return OptimizerFood(
        food_id=food_id,
        food_name=food_id.title(),
        category=category,
        servings_available=Decimal(available),
        max_servings_per_meal=Decimal(maximum),
        calories_per_serving=Decimal(calories),
        protein_g_per_serving=Decimal(protein),
        carbs_g_per_serving=Decimal(carbs),
        fat_g_per_serving=Decimal(fat),
        sugar_g_per_serving=Decimal(sugar),
        fiber_g_per_serving=Decimal("1"),
        sodium_mg_per_serving=Decimal(sodium),
        cost_per_serving=Decimal(cost),
    )


def exact_foods() -> list[OptimizerFood]:
    return [
        optimizer_food("chicken", "protein", calories="200", protein="40", carbs="0", fat="5"),
        optimizer_food("rice", "carb", calories="200", protein="4", carbs="45", fat="1"),
        optimizer_food("broccoli", "vegetable", calories="50", protein="4", carbs="10", fat="0"),
    ]


def exact_constraints(**overrides: float) -> NutritionConstraints:
    values = {"calorie_goal": 450, "protein_goal": 48, "carbs_goal": 55, "fat_goal": 6}
    values.update(overrides)
    return NutritionConstraints(**values)


def test_scaling_and_half_serving_conversions() -> None:
    assert servings_to_units(Decimal("0.5")) == 1
    assert servings_to_units(Decimal("1.5")) == 3
    assert servings_to_units(Decimal("1.49")) == 2
    assert units_to_servings(3) == 1.5
    assert scale_decimal(Decimal("12.345"), NUTRITION_SCALE) == 1235
    assert scale_decimal(Decimal("4.25"), COST_SCALE) == 425
    assert unscale_total(1235 * 3, NUTRITION_SCALE) == pytest.approx(18.525)


def test_exact_target_is_proven_optimal_and_matches_evaluator() -> None:
    result = CpSatMealOptimizer(exact_foods(), exact_constraints(), time_limit_seconds=1).solve()
    assert result.solver_status == "OPTIMAL"
    assert result.meal == {"chicken": 1, "rice": 1, "broccoli": 1}
    assert result.objective_value == pytest.approx(3)
    assert result.evaluation.is_feasible is True
    assert result.evaluation.totals == {
        "calories": 450.0,
        "protein_g": 48.0,
        "carbs_g": 55.0,
        "fat_g": 6.0,
        "sodium_mg": 0.0,
        "sugar_g": 0.0,
        "fiber_g": 3.0,
        "cost": 3.0,
    }


def test_protein_is_a_minimum_and_excess_is_allowed() -> None:
    foods = exact_foods()
    foods[0] = optimizer_food(
        "chicken", "protein", calories="200", protein="80", carbs="0", fat="5"
    )
    result = CpSatMealOptimizer(foods, exact_constraints(), time_limit_seconds=1).solve()
    assert result.evaluation.is_feasible
    assert result.evaluation.totals["protein_g"] > 48
    assert result.evaluation.constraint_scores["protein"] == 100


def test_calorie_carb_and_fat_over_and_under_deviations_are_penalized() -> None:
    foods = [
        optimizer_food(
            "protein",
            "protein",
            calories="100",
            protein="50",
            carbs="0",
            fat="0",
            available="0.5",
            maximum="0.5",
        ),
        optimizer_food(
            "under",
            "carb",
            calories="200",
            carbs="20",
            fat="10",
            available="0.5",
            maximum="0.5",
        ),
        optimizer_food(
            "target",
            "carb",
            calories="300",
            carbs="40",
            fat="20",
            available="0.5",
            maximum="0.5",
        ),
        optimizer_food(
            "over",
            "carb",
            calories="400",
            carbs="60",
            fat="30",
            available="0.5",
            maximum="0.5",
        ),
    ]
    constraints = NutritionConstraints(200, 25, 20, 10)
    result = CpSatMealOptimizer(
        foods, constraints, time_limit_seconds=1, max_unique_foods=2
    ).solve()
    assert result.meal == {"protein": 0.5, "target": 0.5}


@pytest.mark.parametrize(
    ("maximum_name", "maximum"),
    [("sodium_max", 1), ("sugar_max", 0), ("cost_max", 2)],
)
def test_impossible_optional_maximum_triggers_relaxed_solution(
    maximum_name: str, maximum: float
) -> None:
    foods = exact_foods()
    foods[0] = optimizer_food(
        "chicken",
        "protein",
        calories="200",
        protein="40",
        carbs="0",
        fat="5",
        sodium="10",
        sugar="1",
        cost="2",
    )
    constraints = exact_constraints(**{maximum_name: maximum})
    result = CpSatMealOptimizer(foods, constraints, time_limit_seconds=1).solve()
    assert result.solver_status == "OPTIMAL"
    assert result.evaluation.is_feasible is False
    assert result.constraint_violations


def test_inventory_and_per_meal_limits_are_enforced() -> None:
    foods = exact_foods()
    foods[0] = optimizer_food(
        "chicken",
        "protein",
        calories="200",
        protein="40",
        carbs="0",
        fat="5",
        available="0.75",
        maximum="2",
    )
    result = CpSatMealOptimizer(foods, exact_constraints(), time_limit_seconds=1).solve()
    assert result.meal["chicken"] <= 0.5


def test_food_count_and_total_serving_limits_are_enforced() -> None:
    result = CpSatMealOptimizer(
        exact_foods(),
        exact_constraints(),
        time_limit_seconds=1,
        max_unique_foods=2,
        max_total_servings=Decimal("2"),
    ).solve()
    assert len(result.meal) <= 2
    assert sum(result.meal.values()) <= 2


def test_structure_requires_protein_and_carb_or_produce() -> None:
    with pytest.raises(ValueError, match="protein and a carbohydrate or produce"):
        CpSatMealOptimizer(
            [optimizer_food("rice", "carb")], exact_constraints(), time_limit_seconds=1
        ).solve()


def test_protein_and_condiment_category_counts_are_limited() -> None:
    foods = exact_foods() + [
        optimizer_food("eggs", "protein"),
        optimizer_food("fish", "protein"),
        optimizer_food("sauce", "condiment"),
        optimizer_food("salt", "condiment"),
        optimizer_food("spice", "condiment"),
    ]
    result = CpSatMealOptimizer(foods, exact_constraints(), time_limit_seconds=1).solve()
    selected = {food.food_id: food for food in foods if food.food_id in result.meal}
    assert sum(food.category == "protein" for food in selected.values()) <= 2
    assert sum(food.category == "condiment" for food in selected.values()) <= 2


def test_impossible_strict_nutrition_returns_near_feasible_meal() -> None:
    result = CpSatMealOptimizer(
        exact_foods(),
        exact_constraints(calorie_goal=2000, protein_goal=300, carbs_goal=300, fat_goal=80),
        time_limit_seconds=1,
    ).solve()
    assert result.evaluation.is_feasible is False
    assert result.constraint_violations["protein"] > 0


def test_empty_eligible_pantry_is_rejected() -> None:
    unavailable = optimizer_food("chicken", "protein", available="0")
    with pytest.raises(ValueError, match="eligible foods"):
        CpSatMealOptimizer([unavailable], exact_constraints(), time_limit_seconds=1)


def test_unified_service_preserves_random_baseline() -> None:
    result = optimize_meal(
        exact_foods(), exact_constraints(), method="random", number_of_candidates=20
    )
    assert result.optimization_method == "random"
    assert result.solver_status == "COMPLETED"
    assert result.candidates_generated == 20
