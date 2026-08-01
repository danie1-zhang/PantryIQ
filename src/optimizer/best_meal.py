from __future__ import annotations
import random
from dataclasses import dataclass
from typing import Mapping
import pandas as pd

from optimizer.nutrition_constraints import (
    MealEvaluation,
    NutritionConstraints,
    NutritionConstraintEvaluator,
)


@dataclass(frozen=True)
class OptimizerResult:
    "The best meal found by the V1 optimizer."
    meal: dict[str, float]
    evaluation: MealEvaluation
    candidates_generated: int
    valid_candidates_evaluated: int


class MealOptimizer:
    """
    Generate candidate meals and select the best candidate found.

    This V1 optimizer uses randomized candidate generation rather than
    exhaustively checking every possible combination.

    A candidate meal is represented as:

        {
            "chicken_breast": 1,
            "white_rice": 2,
            "broccoli": 1,
        }

    Each key is a food_item_id and each value is a serving count.
    """

    REQUIRED_COLUMNS = {
        "food_item_id",
        "category",
        "servings",
        "max_servings",
        "is_available",
        "calories_per_serving",
        "protein_g_per_serving",
        "carbs_g_per_serving",
        "fat_g_per_serving"
    }

    # These categories generally form the main structure of a meal.
    PROTEIN_CATEGORIES = {
        "protein",
        "meat",
        "poultry",
        "fish",
        "seafood",
        "egg",
        "eggs",
        "tofu"
    }

    CARB_CATEGORIES = {
        "carb",
        "grain",
        "rice",
        "pasta",
        "bread",
        "potato"
    }

    PRODUCE_CATEGORIES = {
        "vegetable",
        "vegetables",
        "fruit",
        "produce"
    }

    CONDIMENT_CATEGORIES = {
        "condiment",
        "sauce",
        "seasoning",
        "dressing"
    }

    OPTIONAL_CATEGORIES = {
        "dairy",
        "fat",
        "snack",
        "other"
    }


    def __init__(self, pantry_foods: pd.DataFrame, constraints: NutritionConstraints, *, random_seed: int | None = 42, max_items_per_meal: int = 6, max_total_servings: float = 8,) -> None:
        """
        Initialize the optimizer.

        Args:
            pantry_foods:
                Available pantry items joined with their nutrition data.
                This can come from Pantry.available_items_df().
            constraints:
                Nutrition goals used to evaluate every candidate.
            random_seed:
                Seed for reproducible random candidate generation.
                Pass None for different results on every run.
            max_items_per_meal:
                Maximum number of unique foods in one candidate meal.
            max_total_servings:
                Maximum total serving count across the candidate meal.
        """
        if max_items_per_meal <= 0:
            raise ValueError("max_items_per_meal must be greater than zero.")

        if max_total_servings <= 0:
            raise ValueError("max_total_servings must be greater than zero.")

        self.pantry_foods = self._prepare_pantry_foods(pantry_foods)
        self.constraints = constraints
        self.max_items_per_meal = max_items_per_meal
        self.max_total_servings = max_total_servings
        self.random = random.Random(random_seed)
        self.evaluator = NutritionConstraintEvaluator(self.pantry_foods)


    def find_best_meal(self, number_of_candidates: int = 10_000) -> OptimizerResult:
        """
        Generate candidate meals and return the best one found.

        Feasible candidates are always preferred over infeasible candidates.

        Among candidates with the same feasibility status, the candidate with
        the highest feasibility score is selected.
        """
        if number_of_candidates <= 0:
            raise ValueError("number_of_candidates must be greater than zero.")

        best_feasible_meal: dict[str, float] | None = None
        best_feasible_evaluation: MealEvaluation | None = None
        best_infeasible_meal: dict[str, float] | None = None
        best_infeasible_evaluation: MealEvaluation | None = None
        valid_candidates_evaluated = 0

        for _ in range(number_of_candidates):
            candidate = self.generate_candidate_meal()

            if candidate is None:
                continue

            evaluation = self.evaluator.evaluate(meal=candidate, constraints=self.constraints,)
            valid_candidates_evaluated += 1

            if evaluation.is_feasible:
                if self._is_better_evaluation(candidate=evaluation, current_best=best_feasible_evaluation,):
                    best_feasible_meal = candidate
                    best_feasible_evaluation = evaluation
            else:
                if self._is_better_evaluation(candidate=evaluation, current_best=best_infeasible_evaluation,):
                    best_infeasible_meal = candidate
                    best_infeasible_evaluation = evaluation

        if best_feasible_meal is not None:
            return OptimizerResult(
                meal=best_feasible_meal,
                evaluation=best_feasible_evaluation,
                candidates_generated=number_of_candidates,
                valid_candidates_evaluated=valid_candidates_evaluated
            )

        if best_infeasible_meal is not None:
            return OptimizerResult(
                meal=best_infeasible_meal,
                evaluation=best_infeasible_evaluation,
                candidates_generated=number_of_candidates,
                valid_candidates_evaluated=valid_candidates_evaluated
            )

        raise RuntimeError("No valid candidate meals could be generated from the pantry.")


    def generate_candidate_meal(self) -> dict[str, float] | None:
        """
        Generate one random meal that passes basic realism checks.

        The method tries several times because a randomly generated candidate
        may be structurally unrealistic.
        """
        maximum_attempts = 50

        for _ in range(maximum_attempts):
            candidate = self._build_random_candidate()
            if self._is_valid_meal_structure(candidate):
                return candidate
        return None


    def _build_random_candidate(self) -> dict[str, float]:
        "Randomly select pantry foods and serving counts."
        available_foods = self.pantry_foods.copy()

        maximum_items = min(self.max_items_per_meal, len(available_foods))

        if maximum_items == 0:
            return {}

        minimum_items = min(2, maximum_items)
        number_of_items = self.random.randint(minimum_items, maximum_items)
        selected_indices = self.random.sample(population=list(available_foods.index), k=number_of_items)

        candidate: dict[str, float] = {}

        for index in selected_indices:
            food = available_foods.loc[index]
            available_servings = float(food["servings"])
            maximum_meal_servings = float(food["max_servings"])
            serving_limit = min(available_servings, maximum_meal_servings,)

            if serving_limit <= 0:
                continue

            servings = self._random_serving_count(serving_limit)

            if servings > 0:
                food_item_id = str(food["food_item_id"])
                candidate[food_item_id] = servings

        return candidate


    def _random_serving_count(self, maximum_servings: float) -> float:
        """
        Choose a whole or half serving up to the allowed maximum.

        For V1, serving counts are limited to increments of 0.5.
        Change `serving_step` to 1.0 to allow only whole servings.
        """
        serving_step = 0.5
        number_of_steps = int(maximum_servings / serving_step)
        if number_of_steps <= 0:
            return 0.0
        selected_steps = self.random.randint(1, number_of_steps)
        return round(selected_steps * serving_step, 2)


    def _is_valid_meal_structure(self, meal: Mapping[str, float]) -> bool:
        "Apply basic rules for what counts as a realistic meal."
        if not meal:
            return False

        if len(meal) > self.max_items_per_meal:
            return False

        total_servings = sum(meal.values())

        if total_servings > self.max_total_servings:
            return False

        selected_foods = self.pantry_foods[self.pantry_foods["food_item_id"].isin(meal.keys())]

        if selected_foods.empty:
            return False

        categories = (selected_foods["category"].fillna("other").astype(str).str.strip().str.lower())
        protein_count = categories.isin(self.PROTEIN_CATEGORIES).sum()
        condiment_count = categories.isin(self.CONDIMENT_CATEGORIES).sum()
        non_condiment_count = (~categories.isin(self.CONDIMENT_CATEGORIES)).sum()
        has_protein = protein_count >= 1
        has_carb = categories.isin(self.CARB_CATEGORIES).any()
        has_produce = categories.isin(self.PRODUCE_CATEGORIES).any()

        # Prevent combinations such as beef + chicken + eggs + fish.
        if protein_count > 2:
            return False

        # A meal should not consist only of condiments.
        if non_condiment_count == 0:
            return False

        if condiment_count > 2:
            return False

        # Require at least one meaningful protein source.
        if not has_protein:
            return False

        # Require at least one supporting component:
        # a carbohydrate or produce item.
        if not has_carb and not has_produce:
            return False

        return True


    @staticmethod
    def _is_better_evaluation(candidate: MealEvaluation, current_best: MealEvaluation | None,) -> bool:
        "Return whether one evaluation should replace the current best."
        if current_best is None:
            return True

        if candidate.feasibility_score != current_best.feasibility_score:
            return (candidate.feasibility_score > current_best.feasibility_score)

        # Tie breaker 1: lower cost.
        if candidate.totals["cost"] != current_best.totals["cost"]:
            return candidate.totals["cost"] < current_best.totals["cost"]

        # Tie breaker 2: higher protein.
        if (candidate.totals["protein_g"] != current_best.totals["protein_g"]):
            return (candidate.totals["protein_g"] > current_best.totals["protein_g"])

        # Tie breaker 3: lower calories.
        return (candidate.totals["calories"] < current_best.totals["calories"])


    def _prepare_pantry_foods(self, pantry_foods: pd.DataFrame,) -> pd.DataFrame:
        "Validate and filter the pantry data used by the optimizer."
        foods = pantry_foods.copy()

        missing_columns = self.REQUIRED_COLUMNS - set(foods.columns)

        if missing_columns:
            raise ValueError(f"Pantry food data is missing required columns: {sorted(missing_columns)}")

        foods["food_item_id"] = (foods["food_item_id"].astype(str).str.strip())
        foods["category"] = (foods["category"].fillna("other").astype(str).str.strip().str.lower())

        numeric_columns = [
            "servings",
            "max_servings",
            "calories_per_serving",
            "protein_g_per_serving",
            "carbs_g_per_serving",
            "fat_g_per_serving"
        ]

        for column in numeric_columns:
            foods[column] = pd.to_numeric(foods[column],errors="raise")

        foods["is_available"] = (foods["is_available"].astype(str).str.strip().str.lower().map(
            {
                    "true": True,
                    "false": False,
                    "1": True,
                    "0": False,
                    "yes": True,
                    "no": False,
                }
            )
        )

        if foods["is_available"].isna().any():
            raise ValueError("is_available contains invalid boolean values.")

        foods = foods[foods["is_available"] & (foods["servings"] > 0) & (foods["max_servings"] > 0)].copy()

        if foods.empty:
            raise ValueError("The pantry does not contain any available foods.")

        if foods["food_item_id"].duplicated().any():
            raise ValueError("The optimizer expects one row per food_item_id.")

        return foods.reset_index(drop=True)
