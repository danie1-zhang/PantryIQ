from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

from src.optimizer.nutrition_constraints import MealEvaluation

OptimizationMethod = Literal["cp_sat", "random"]


@dataclass(frozen=True)
class OptimizerFood:
    """Canonical nutrition and inventory data for one eligible pantry food."""

    food_id: str
    food_name: str
    category: str
    servings_available: Decimal
    max_servings_per_meal: Decimal
    calories_per_serving: Decimal
    protein_g_per_serving: Decimal
    carbs_g_per_serving: Decimal
    fat_g_per_serving: Decimal
    sugar_g_per_serving: Decimal
    fiber_g_per_serving: Decimal
    sodium_mg_per_serving: Decimal
    cost_per_serving: Decimal
    is_available: bool = True
    is_active: bool = True
    cuisine_tags: tuple[str, ...] = ()
    dietary_tags: tuple[str, ...] = ()
    allergen_tags: tuple[str, ...] = ()
    ingredient_tags: tuple[str, ...] = ()
    flavor_tags: tuple[str, ...] = ()
    spice_level: str = "none"
    is_cuisine_neutral: bool = False
    preference_score: int = 0
    is_required: bool = False


@dataclass(frozen=True)
class OptimizerResult:
    """Unified result returned by every optimization strategy."""

    meal: dict[str, float]
    evaluation: MealEvaluation
    optimization_method: OptimizationMethod
    solver_status: str
    objective_value: float | None = None
    best_objective_bound: float | None = None
    solve_time_seconds: float = 0.0
    constraint_violations: dict[str, float] = field(default_factory=dict)
    candidates_generated: int = 0
    valid_candidates_evaluated: int = 0
