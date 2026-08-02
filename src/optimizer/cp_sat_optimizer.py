from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from dataclasses import replace
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP

from ortools.sat.python import cp_model

from src.optimizer.adapter import optimizer_foods_to_frame
from src.optimizer.categories import (
    CARB_CATEGORIES,
    CONDIMENT_CATEGORIES,
    PRODUCE_CATEGORIES,
    PROTEIN_CATEGORIES,
)
from src.optimizer.models import OptimizerFood, OptimizerResult
from src.optimizer.nutrition_constraints import (
    FEASIBILITY_TOLERANCE,
    NutritionConstraints,
    NutritionConstraintEvaluator,
)

logger = logging.getLogger(__name__)

SERVING_SCALE = 2
NUTRITION_SCALE = 100
COST_SCALE = 100
TARGET_TOLERANCE = Decimal(str(FEASIBILITY_TOLERANCE))
DEFAULT_MAX_UNIQUE_FOODS = 6
DEFAULT_MAX_TOTAL_SERVINGS = Decimal("8")
DEFAULT_TIME_LIMIT_SECONDS = 2.0
OBJECTIVE_SCALE = 1_000_000
VIOLATION_PRIORITY = 10_000

OBJECTIVE_WEIGHTS = {
    "calories": 100,
    "carbs": 60,
    "fat": 60,
    "cost": 5,
    "sodium": 3,
    "sugar": 3,
    "food_count": 1,
}

NUTRIENT_FIELDS = {
    "calories": "calories_per_serving",
    "protein_g": "protein_g_per_serving",
    "carbs_g": "carbs_g_per_serving",
    "fat_g": "fat_g_per_serving",
    "sugar_g": "sugar_g_per_serving",
    "fiber_g": "fiber_g_per_serving",
    "sodium_mg": "sodium_mg_per_serving",
    "cost": "cost_per_serving",
}


def scale_decimal(value: Decimal | float | int | str, scale: int) -> int:
    """Round a decimal value to one consistent CP-SAT integer scale."""

    return int((Decimal(str(value)) * scale).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def unscale_total(value: int, scale: int) -> float:
    """Convert a sum of per-serving coefficients times half-serving units."""

    return float(Decimal(value) / Decimal(scale * SERVING_SCALE))


def servings_to_units(servings: Decimal | float | int | str) -> int:
    """Floor inventory to the number of complete half-serving units available."""

    return int((Decimal(str(servings)) * SERVING_SCALE).to_integral_value(rounding=ROUND_FLOOR))


def units_to_servings(units: int) -> float:
    return float(Decimal(units) / SERVING_SCALE)


@dataclass
class _BuiltModel:
    model: cp_model.CpModel
    serving_units: list[cp_model.IntVar]
    totals: dict[str, cp_model.IntVar]
    violations: dict[str, cp_model.IntVar]


class OptimizationTimeoutError(RuntimeError):
    """The bounded solver run ended before producing a usable solution."""


class CpSatMealOptimizer:
    """Solve a deterministic half-serving meal model with strict then relaxed constraints."""

    def __init__(
        self,
        foods: list[OptimizerFood],
        constraints: NutritionConstraints,
        *,
        time_limit_seconds: float = DEFAULT_TIME_LIMIT_SECONDS,
        max_unique_foods: int = DEFAULT_MAX_UNIQUE_FOODS,
        max_total_servings: Decimal = DEFAULT_MAX_TOTAL_SERVINGS,
        excluded_meals: list[dict[str, float]] | None = None,
    ) -> None:
        self.foods = [
            food
            for food in foods
            if food.is_available
            and food.is_active
            and servings_to_units(min(food.servings_available, food.max_servings_per_meal)) > 0
        ]
        if not self.foods:
            raise ValueError("The pantry does not contain any eligible foods.")
        if not 0.1 <= time_limit_seconds <= 10:
            raise ValueError("time_limit_seconds must be between 0.1 and 10 seconds.")
        if max_unique_foods <= 0 or max_total_servings <= 0:
            raise ValueError("Meal size limits must be greater than zero.")
        self.constraints = constraints
        self.time_limit_seconds = time_limit_seconds
        self.max_unique_foods = max_unique_foods
        self.max_total_servings = max_total_servings
        self.excluded_meals = excluded_meals or []
        self.evaluator = NutritionConstraintEvaluator(optimizer_foods_to_frame(self.foods))

    def solve(self) -> OptimizerResult:
        started_at = time.monotonic()
        deadline = started_at + self.time_limit_seconds
        strict = self._build_model(relaxed=False)
        strict_time = deadline - time.monotonic()
        if strict_time <= 0:
            raise OptimizationTimeoutError("Building the CP-SAT model exceeded the time limit.")
        strict_result = self._solve_model(strict, relaxed=False, time_limit_seconds=strict_time)
        if strict_result is not None:
            if not strict_result.evaluation.is_feasible:
                raise RuntimeError("CP-SAT strict solution disagrees with the nutrition evaluator.")
            return replace(strict_result, solve_time_seconds=time.monotonic() - started_at)

        relaxed = self._build_model(relaxed=True)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise OptimizationTimeoutError(
                "The strict model was infeasible, but no solve time remained for relaxation."
            )
        relaxed_result = self._solve_model(relaxed, relaxed=True, time_limit_seconds=remaining)
        if relaxed_result is None:
            raise ValueError("No structurally valid meal can be generated from this pantry.")
        return replace(relaxed_result, solve_time_seconds=time.monotonic() - started_at)

    def _build_model(self, *, relaxed: bool) -> _BuiltModel:
        model = cp_model.CpModel()
        serving_units: list[cp_model.IntVar] = []
        selected: list[cp_model.IntVar] = []
        maximum_units: list[int] = []

        for index, food in enumerate(self.foods):
            upper = servings_to_units(min(food.servings_available, food.max_servings_per_meal))
            units = model.new_int_var(0, upper, f"serving_units_{index}")
            included = model.new_bool_var(f"selected_{index}")
            model.add(units >= included)
            model.add(units <= upper * included)
            serving_units.append(units)
            selected.append(included)
            maximum_units.append(upper)

        model.add(sum(selected) >= 1)
        model.add(sum(selected) <= min(self.max_unique_foods, len(self.foods)))
        model.add(sum(serving_units) <= servings_to_units(self.max_total_servings))
        self._exclude_previous_meals(model, serving_units, maximum_units)

        protein_selected = [
            selected[index]
            for index, food in enumerate(self.foods)
            if food.category in PROTEIN_CATEGORIES
        ]
        support_selected = [
            selected[index]
            for index, food in enumerate(self.foods)
            if food.category in CARB_CATEGORIES or food.category in PRODUCE_CATEGORIES
        ]
        condiment_selected = [
            selected[index]
            for index, food in enumerate(self.foods)
            if food.category in CONDIMENT_CATEGORIES
        ]
        non_condiment_selected = [
            selected[index]
            for index, food in enumerate(self.foods)
            if food.category not in CONDIMENT_CATEGORIES
        ]
        if not protein_selected or not support_selected or not non_condiment_selected:
            raise ValueError("Pantry needs a protein and a carbohydrate or produce item.")
        model.add(sum(protein_selected) >= 1)
        model.add(sum(protein_selected) <= 2)
        model.add(sum(support_selected) >= 1)
        model.add(sum(non_condiment_selected) >= 1)
        if condiment_selected:
            model.add(sum(condiment_selected) <= 2)

        totals: dict[str, cp_model.IntVar] = {}
        total_upper_bounds: dict[str, int] = {}
        for nutrient, field_name in NUTRIENT_FIELDS.items():
            scale = COST_SCALE if nutrient == "cost" else NUTRITION_SCALE
            coefficients = [scale_decimal(getattr(food, field_name), scale) for food in self.foods]
            upper = sum(
                coefficient * units for coefficient, units in zip(coefficients, maximum_units)
            )
            total = model.new_int_var(0, max(0, upper), f"total_{nutrient}")
            model.add(total == sum(c * u for c, u in zip(coefficients, serving_units)))
            totals[nutrient] = total
            total_upper_bounds[nutrient] = upper

        targets = {
            "calories": self._scaled_target(self.constraints.calorie_goal, NUTRITION_SCALE),
            "protein_g": self._scaled_target(self.constraints.protein_goal, NUTRITION_SCALE),
            "carbs_g": self._scaled_target(self.constraints.carbs_goal, NUTRITION_SCALE),
            "fat_g": self._scaled_target(self.constraints.fat_goal, NUTRITION_SCALE),
        }
        maximums = {
            "sodium_mg": self._optional_target(self.constraints.sodium_max, NUTRITION_SCALE),
            "sugar_g": self._optional_target(self.constraints.sugar_max, NUTRITION_SCALE),
            "cost": self._optional_target(self.constraints.cost_max, COST_SCALE),
        }

        objective_terms: list[cp_model.LinearExpr] = []
        violations: dict[str, cp_model.IntVar] = {}
        for nutrient in ("calories", "carbs_g", "fat_g"):
            target = targets[nutrient]
            upper_bound = max(target, total_upper_bounds[nutrient])
            under = model.new_int_var(0, upper_bound, f"{nutrient}_under")
            over = model.new_int_var(0, upper_bound, f"{nutrient}_over")
            model.add(under >= target - totals[nutrient])
            model.add(over >= totals[nutrient] - target)
            weight_name = "carbs" if nutrient == "carbs_g" else nutrient.removesuffix("_g")
            coefficient = self._normalized_coefficient(OBJECTIVE_WEIGHTS[weight_name], target)
            objective_terms.extend([under * coefficient, over * coefficient])

            lower = int(
                (Decimal(target) * (Decimal("1") - TARGET_TOLERANCE)).to_integral_value(
                    rounding=ROUND_CEILING
                )
            )
            upper = int(
                (Decimal(target) * (Decimal("1") + TARGET_TOLERANCE)).to_integral_value(
                    rounding=ROUND_FLOOR
                )
            )
            if relaxed:
                violation = model.new_int_var(0, upper_bound, f"{nutrient}_tolerance_violation")
                model.add(violation >= lower - totals[nutrient])
                model.add(violation >= totals[nutrient] - upper)
                violations[weight_name] = violation
                objective_terms.append(
                    violation * self._normalized_coefficient(VIOLATION_PRIORITY, target)
                )
            else:
                model.add(totals[nutrient] >= lower)
                model.add(totals[nutrient] <= upper)

        if relaxed:
            shortfall = model.new_int_var(0, targets["protein_g"], "protein_shortfall")
            model.add(shortfall >= targets["protein_g"] - totals["protein_g"])
            violations["protein"] = shortfall
            objective_terms.append(
                shortfall * self._normalized_coefficient(VIOLATION_PRIORITY, targets["protein_g"])
            )
        else:
            model.add(totals["protein_g"] >= targets["protein_g"])

        for nutrient, maximum in maximums.items():
            if maximum is None:
                continue
            public_name = {"sodium_mg": "sodium", "sugar_g": "sugar"}.get(nutrient, nutrient)
            if relaxed:
                upper_bound = max(maximum, total_upper_bounds[nutrient])
                excess = model.new_int_var(0, upper_bound, f"{public_name}_excess")
                model.add(excess >= totals[nutrient] - maximum)
                violations[public_name] = excess
                objective_terms.append(
                    excess * self._normalized_coefficient(VIOLATION_PRIORITY, maximum)
                )
            else:
                model.add(totals[nutrient] <= maximum)
            objective_terms.append(
                totals[nutrient]
                * self._normalized_coefficient(OBJECTIVE_WEIGHTS[public_name], maximum)
            )

        objective_terms.append(sum(selected) * OBJECTIVE_WEIGHTS["food_count"])
        model.minimize(sum(objective_terms))
        return _BuiltModel(model, serving_units, totals, violations)

    def _exclude_previous_meals(
        self,
        model: cp_model.CpModel,
        serving_units: list[cp_model.IntVar],
        maximum_units: list[int],
    ) -> None:
        """Prevent an exact repeat of each supplied food-and-serving combination."""

        food_indexes = {food.food_id: index for index, food in enumerate(self.foods)}
        for exclusion_index, excluded_meal in enumerate(self.excluded_meals):
            if any(food_id not in food_indexes for food_id in excluded_meal):
                continue
            expected_units = [0] * len(self.foods)
            for food_id, servings in excluded_meal.items():
                expected_units[food_indexes[food_id]] = servings_to_units(servings)
            if any(
                expected > maximum
                for expected, maximum in zip(expected_units, maximum_units, strict=True)
            ):
                continue

            matches: list[cp_model.IntVar] = []
            for food_index, (variable, expected) in enumerate(
                zip(serving_units, expected_units, strict=True)
            ):
                matches_expected = model.new_bool_var(
                    f"exclusion_{exclusion_index}_food_{food_index}_matches"
                )
                model.add(variable == expected).only_enforce_if(matches_expected)
                model.add(variable != expected).only_enforce_if(matches_expected.Not())
                matches.append(matches_expected)
            model.add(sum(matches) <= len(matches) - 1)

    def _solve_model(
        self, built: _BuiltModel, *, relaxed: bool, time_limit_seconds: float
    ) -> OptimizerResult | None:
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit_seconds
        solver.parameters.num_search_workers = 1
        solver.parameters.random_seed = 0
        status = solver.solve(built.model)
        status_name = solver.status_name(status)
        logger.info(
            "meal optimization method=cp_sat status=%s solve_time=%.4f foods=%d relaxed=%s",
            status_name,
            solver.wall_time,
            len(self.foods),
            relaxed,
        )
        if status == cp_model.MODEL_INVALID:
            raise RuntimeError("The CP-SAT meal model is invalid.")
        if status == cp_model.UNKNOWN:
            raise OptimizationTimeoutError(
                "CP-SAT did not find a solution within the requested time limit."
            )
        if status == cp_model.INFEASIBLE:
            return None
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise RuntimeError(f"Unhandled CP-SAT status: {status_name}")

        meal = {
            food.food_id: units_to_servings(solver.value(built.serving_units[index]))
            for index, food in enumerate(self.foods)
            if solver.value(built.serving_units[index]) > 0
        }
        evaluation = self.evaluator.evaluate(meal, self.constraints)
        violation_values = self._violation_values(evaluation)
        return OptimizerResult(
            meal=meal,
            evaluation=evaluation,
            optimization_method="cp_sat",
            solver_status=status_name,
            objective_value=solver.objective_value,
            best_objective_bound=solver.best_objective_bound,
            solve_time_seconds=solver.wall_time,
            constraint_violations=violation_values,
        )

    def _violation_values(self, evaluation) -> dict[str, float]:
        values: dict[str, float] = {}
        totals = evaluation.totals
        for name, target in (
            ("calories", self.constraints.calorie_goal),
            ("carbs", self.constraints.carbs_goal),
            ("fat", self.constraints.fat_goal),
        ):
            actual = totals["carbs_g" if name == "carbs" else "fat_g" if name == "fat" else name]
            allowed = float(target) * float(TARGET_TOLERANCE)
            values[name] = round(max(0.0, abs(actual - float(target)) - allowed), 2)
        values["protein"] = round(
            max(0.0, float(self.constraints.protein_goal) - totals["protein_g"]), 2
        )
        for name, maximum, total_name in (
            ("sodium", self.constraints.sodium_max, "sodium_mg"),
            ("sugar", self.constraints.sugar_max, "sugar_g"),
            ("cost", self.constraints.cost_max, "cost"),
        ):
            if maximum is not None:
                values[name] = round(max(0.0, totals[total_name] - float(maximum)), 2)
        return {name: value for name, value in values.items() if value > 0}

    @staticmethod
    def _scaled_target(value: float, scale: int) -> int:
        return scale_decimal(value, scale) * SERVING_SCALE

    @staticmethod
    def _optional_target(value: float | None, scale: int) -> int | None:
        return None if value is None else scale_decimal(value, scale) * SERVING_SCALE

    @staticmethod
    def _normalized_coefficient(weight: int, denominator: int) -> int:
        return max(1, round(OBJECTIVE_SCALE * weight / max(1, denominator)))
