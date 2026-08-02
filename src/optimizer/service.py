from __future__ import annotations

from src.optimizer.adapter import optimizer_foods_to_frame
from src.optimizer.best_meal import MealOptimizer
from src.optimizer.cp_sat_optimizer import DEFAULT_TIME_LIMIT_SECONDS, CpSatMealOptimizer
from src.optimizer.models import OptimizationMethod, OptimizerFood, OptimizerResult
from src.optimizer.nutrition_constraints import NutritionConstraints


def optimize_meal(
    foods: list[OptimizerFood],
    constraints: NutritionConstraints,
    *,
    method: OptimizationMethod = "cp_sat",
    time_limit_seconds: float = DEFAULT_TIME_LIMIT_SECONDS,
    number_of_candidates: int = 10_000,
    excluded_meals: list[dict[str, float]] | None = None,
    required_categories: list[str] | None = None,
) -> OptimizerResult:
    """Run the selected optimizer and return a strategy-independent result."""

    if method == "cp_sat":
        return CpSatMealOptimizer(
            foods,
            constraints,
            time_limit_seconds=time_limit_seconds,
            excluded_meals=excluded_meals,
            required_categories=required_categories,
        ).solve()
    if method == "random":
        random_result = MealOptimizer(
            optimizer_foods_to_frame(foods), constraints, excluded_meals=excluded_meals
        ).find_best_meal(number_of_candidates)
        return OptimizerResult(
            meal=random_result.meal,
            evaluation=random_result.evaluation,
            optimization_method="random",
            solver_status="COMPLETED",
            candidates_generated=random_result.candidates_generated,
            valid_candidates_evaluated=random_result.valid_candidates_evaluated,
        )
    raise ValueError(f"Unknown optimization method: {method}")
