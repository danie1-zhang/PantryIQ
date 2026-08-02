from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping
import pandas as pd

FEASIBILITY_TOLERANCE = 0.10


@dataclass(frozen=True)
class NutritionConstraints:
    "Nutrition targets and optional maximum limits for one meal."

    calorie_goal: float
    protein_goal: float
    carbs_goal: float
    fat_goal: float

    sodium_max: float | None = None
    sugar_max: float | None = None
    cost_max: float | None = None

    def __post_init__(self) -> None:
        required_values = {
            "calorie_goal": self.calorie_goal,
            "protein_goal": self.protein_goal,
            "carbs_goal": self.carbs_goal,
            "fat_goal": self.fat_goal,
        }

        for name, value in required_values.items():
            if value <= 0:
                raise ValueError(f"{name} must be greater than zero.")

        optional_values = {
            "sodium_max": self.sodium_max,
            "sugar_max": self.sugar_max,
            "cost_max": self.cost_max,
        }

        for name, value in optional_values.items():
            if value is not None and value < 0:
                raise ValueError(f"{name} cannot be negative.")


@dataclass(frozen=True)
class MealEvaluation:
    "Result returned after evaluating one candidate meal."

    totals: dict[str, float]
    constraint_scores: dict[str, float]
    constraints_met: dict[str, bool]
    feasibility_score: float
    is_feasible: bool


class NutritionConstraintEvaluator:
    "Calculate and score nutrition totals for candidate meals."

    REQUIRED_FOOD_COLUMNS = {
        "food_item_id",
        "calories_per_serving",
        "protein_g_per_serving",
        "carbs_g_per_serving",
        "fat_g_per_serving",
    }

    OPTIONAL_FOOD_COLUMNS = {
        "sodium_mg_per_serving": 0.0,
        "sugar_g_per_serving": 0.0,
        "fiber_g_per_serving": 0.0,
        "cost_per_serving": 0.0,
    }

    # These weights determine each goal's contribution to the final score.
    DEFAULT_WEIGHTS = {
        "calories": 0.35,
        "protein": 0.30,
        "carbs": 0.175,
        "fat": 0.175,
    }

    def __init__(
        self,
        food_data: pd.DataFrame,
        weights: Mapping[str, float] | None = None,
    ) -> None:
        self.food_data = self._prepare_food_data(food_data)
        self.weights = self._prepare_weights(weights)

    def evaluate(
        self,
        meal: Mapping[str, float],
        constraints: NutritionConstraints,
    ) -> MealEvaluation:
        """
        Evaluate one meal against the supplied nutrition constraints.

        Args:
            meal:
                Mapping from food_item_id to number of servings.
                Example: {"chicken_breast": 1.5, "rice": 2}
            constraints:
                Required nutrition goals and optional maximum limits.

        Returns:
            A MealEvaluation containing totals, individual scores,
            feasibility status, and an overall score from 0 to 100.
        """
        totals = self.calculate_totals(meal)

        constraint_scores = {
            "calories": self._closeness_score(
                actual=totals["calories"], target=constraints.calorie_goal
            ),
            "protein": self._minimum_goal_score(
                actual=totals["protein_g"], goal=constraints.protein_goal
            ),
            "carbs": self._closeness_score(actual=totals["carbs_g"], target=constraints.carbs_goal),
            "fat": self._closeness_score(actual=totals["fat_g"], target=constraints.fat_goal),
        }

        constraints_met = {
            # For calories, carbs, and fat, "met" means within 10% of target.
            "calories": self._within_tolerance(
                actual=totals["calories"], target=constraints.calorie_goal
            ),
            "protein": totals["protein_g"] >= constraints.protein_goal,
            "carbs": self._within_tolerance(
                actual=totals["carbs_g"], target=constraints.carbs_goal
            ),
            "fat": self._within_tolerance(actual=totals["fat_g"], target=constraints.fat_goal),
        }

        active_weights = dict(self.weights)

        self._add_optional_constraint(
            name="sodium",
            actual=totals["sodium_mg"],
            maximum=constraints.sodium_max,
            constraint_scores=constraint_scores,
            constraints_met=constraints_met,
            active_weights=active_weights,
        )

        self._add_optional_constraint(
            name="sugar",
            actual=totals["sugar_g"],
            maximum=constraints.sugar_max,
            constraint_scores=constraint_scores,
            constraints_met=constraints_met,
            active_weights=active_weights,
        )

        self._add_optional_constraint(
            name="cost",
            actual=totals["cost"],
            maximum=constraints.cost_max,
            constraint_scores=constraint_scores,
            constraints_met=constraints_met,
            active_weights=active_weights,
        )

        feasibility_score = self._weighted_average(scores=constraint_scores, weights=active_weights)
        is_feasible = all(constraints_met.values())

        return MealEvaluation(
            totals=totals,
            constraint_scores=constraint_scores,
            constraints_met=constraints_met,
            feasibility_score=feasibility_score,
            is_feasible=is_feasible,
        )

    def calculate_totals(
        self,
        meal: Mapping[str, float],
    ) -> dict[str, float]:
        "Calculate total nutrition and cost for a candidate meal."
        if not meal:
            raise ValueError("Meal cannot be empty.")

        totals = {
            "calories": 0.0,
            "protein_g": 0.0,
            "carbs_g": 0.0,
            "fat_g": 0.0,
            "sodium_mg": 0.0,
            "sugar_g": 0.0,
            "fiber_g": 0.0,
            "cost": 0.0,
        }

        foods_by_id = self.food_data.set_index("food_item_id")

        for food_item_id, servings in meal.items():
            if servings <= 0:
                raise ValueError(f"Servings for '{food_item_id}' must be greater than zero.")

            if food_item_id not in foods_by_id.index:
                raise ValueError(f"Food ID '{food_item_id}' was not found in the food data.")

            food = foods_by_id.loc[food_item_id]

            totals["calories"] += float(food["calories_per_serving"]) * servings
            totals["protein_g"] += float(food["protein_g_per_serving"]) * servings
            totals["carbs_g"] += float(food["carbs_g_per_serving"]) * servings
            totals["fat_g"] += float(food["fat_g_per_serving"]) * servings
            totals["sodium_mg"] += float(food["sodium_mg_per_serving"]) * servings
            totals["sugar_g"] += float(food["sugar_g_per_serving"]) * servings
            totals["fiber_g"] += float(food["fiber_g_per_serving"]) * servings
            totals["cost"] += float(food["cost_per_serving"]) * servings

        return {name: round(value, 2) for name, value in totals.items()}

    def _prepare_food_data(
        self,
        food_data: pd.DataFrame,
    ) -> pd.DataFrame:
        "Validate and normalize the nutrition DataFrame."
        foods = food_data.copy()

        missing = self.REQUIRED_FOOD_COLUMNS - set(foods.columns)

        if missing:
            raise ValueError(f"Food data is missing required columns: {sorted(missing)}")

        for column, default in self.OPTIONAL_FOOD_COLUMNS.items():
            if column not in foods.columns:
                foods[column] = default

        if foods["food_item_id"].duplicated().any():
            raise ValueError("food_item_id values must be unique.")

        nutrition_columns = [
            "calories_per_serving",
            "protein_g_per_serving",
            "carbs_g_per_serving",
            "fat_g_per_serving",
            "sodium_mg_per_serving",
            "sugar_g_per_serving",
            "fiber_g_per_serving",
            "cost_per_serving",
        ]

        for column in nutrition_columns:
            foods[column] = pd.to_numeric(
                foods[column],
                errors="raise",
            )
            if (foods[column] < 0).any():
                raise ValueError(f"Column '{column}' cannot contain negative values.")
        foods["food_item_id"] = foods["food_item_id"].astype(str).str.strip()
        return foods.reset_index(drop=True)

    def _prepare_weights(
        self,
        weights: Mapping[str, float] | None,
    ) -> dict[str, float]:
        selected_weights = dict(weights if weights is not None else self.DEFAULT_WEIGHTS)
        required = {"calories", "protein", "carbs", "fat"}
        missing = required - set(selected_weights)

        if missing:
            raise ValueError(f"Scoring weights are missing: {sorted(missing)}")

        if any(weight < 0 for weight in selected_weights.values()):
            raise ValueError("Scoring weights cannot be negative.")

        if sum(selected_weights.values()) <= 0:
            raise ValueError("At least one scoring weight must be greater than zero.")

        return selected_weights

    @staticmethod
    def _closeness_score(
        actual: float,
        target: float,
    ) -> float:
        """
        Score closeness to an exact target from 0 to 100.

        Exact target:
            100 points

        10% away:
            90 points

        50% away:
            50 points

        100% or more away:
            0 points
        """
        relative_error = abs(actual - target) / target
        return round(max(0.0, 100.0 * (1.0 - relative_error)), 2)

    @staticmethod
    def _minimum_goal_score(actual: float, goal: float) -> float:
        "Score a minimum goal where exceeding the goal is not penalized."
        if actual >= goal:
            return 100.0

        return round(max(0.0, 100.0 * actual / goal), 2)

    @staticmethod
    def _maximum_limit_score(
        actual: float,
        maximum: float,
    ) -> float:
        """
        Score a maximum constraint where lower values are preferred.

        A value of zero receives 100 points. A value equal to the maximum
        receives 50 points. Values above the maximum continue losing points.
        """
        if maximum == 0:
            return 100.0 if actual == 0 else 0.0

        score = 100.0 - 50.0 * (actual / maximum)
        return round(max(0.0, score), 2)

    @staticmethod
    def _within_tolerance(
        actual: float,
        target: float,
        tolerance: float = FEASIBILITY_TOLERANCE,
    ) -> bool:
        "Return True when actual is within a percentage of target."
        return abs(actual - target) <= target * tolerance

    def _add_optional_constraint(
        self,
        name: str,
        actual: float,
        maximum: float | None,
        constraint_scores: dict[str, float],
        constraints_met: dict[str, bool],
        active_weights: dict[str, float],
    ) -> None:
        "Add an optional maximum constraint when the user supplied one."
        if maximum is None:
            return

        constraint_scores[name] = self._maximum_limit_score(actual=actual, maximum=maximum)
        constraints_met[name] = actual <= maximum
        # Give each optional constraint a moderate weight.
        active_weights[name] = 0.10

    @staticmethod
    def _weighted_average(
        scores: Mapping[str, float],
        weights: Mapping[str, float],
    ) -> float:
        total_weight = sum(weights[name] for name in scores)
        if total_weight == 0:
            raise ValueError("Total scoring weight cannot be zero.")
        weighted_total = sum(scores[name] * weights[name] for name in scores)
        return round(weighted_total / total_weight, 2)
