from __future__ import annotations

from decimal import Decimal

import pandas as pd

from src.database.models import PantryItem
from src.optimizer.categories import normalize_category
from src.optimizer.models import OptimizerFood


def pantry_items_to_optimizer_foods(items: list[PantryItem]) -> list[OptimizerFood]:
    """Convert loaded SQLAlchemy pantry rows into validated optimizer inputs."""

    foods: list[OptimizerFood] = []
    for item in items:
        food = item.food
        values = (
            food.calories,
            food.protein,
            food.carbs,
            food.fat,
            food.sugar,
            food.fiber,
            food.sodium,
        )
        if (
            not item.is_available
            or item.servings_available <= 0
            or item.max_servings_per_meal <= 0
            or any(value is None or value < 0 for value in values)
        ):
            continue
        foods.append(
            OptimizerFood(
                food_id=str(food.id),
                food_name=food.name,
                category=normalize_category(food.category),
                servings_available=item.servings_available,
                max_servings_per_meal=item.max_servings_per_meal,
                calories_per_serving=food.calories,
                protein_g_per_serving=food.protein,
                carbs_g_per_serving=food.carbs,
                fat_g_per_serving=food.fat,
                sugar_g_per_serving=food.sugar,
                fiber_g_per_serving=food.fiber,
                sodium_mg_per_serving=food.sodium,
                cost_per_serving=food.cost_per_serving or Decimal("0"),
                # The current Food model has no active flag. Existing canonical rows are active.
                is_active=True,
            )
        )
    return foods


def optimizer_foods_to_frame(foods: list[OptimizerFood]) -> pd.DataFrame:
    """Build the legacy evaluator/random-optimizer DataFrame once per request."""

    return pd.DataFrame(
        [
            {
                "food_item_id": food.food_id,
                "food_nm": food.food_name,
                "category": food.category,
                "servings": float(food.servings_available),
                "max_servings": float(food.max_servings_per_meal),
                "is_available": food.is_available and food.is_active,
                "calories_per_serving": float(food.calories_per_serving),
                "protein_g_per_serving": float(food.protein_g_per_serving),
                "carbs_g_per_serving": float(food.carbs_g_per_serving),
                "fat_g_per_serving": float(food.fat_g_per_serving),
                "sugar_g_per_serving": float(food.sugar_g_per_serving),
                "fiber_g_per_serving": float(food.fiber_g_per_serving),
                "sodium_mg_per_serving": float(food.sodium_mg_per_serving),
                "cost_per_serving": float(food.cost_per_serving),
            }
            for food in foods
        ]
    )
