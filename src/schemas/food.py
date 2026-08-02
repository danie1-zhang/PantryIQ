from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.database.models import Food


class FoodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    brand: str
    category: str
    serving_size: float
    serving_unit: str
    calories_per_serving: float
    protein_g_per_serving: float
    carbs_g_per_serving: float
    fat_g_per_serving: float
    sugar_g_per_serving: float
    fiber_g_per_serving: float
    sodium_mg_per_serving: float
    cost_per_serving: float | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_food(cls, food: Food) -> "FoodResponse":
        return cls(
            id=food.id,
            name=food.name,
            brand=food.brand,
            category=food.category,
            serving_size=float(food.serving_size),
            serving_unit=food.serving_unit,
            calories_per_serving=float(food.calories),
            protein_g_per_serving=float(food.protein),
            carbs_g_per_serving=float(food.carbs),
            fat_g_per_serving=float(food.fat),
            sugar_g_per_serving=float(food.sugar),
            fiber_g_per_serving=float(food.fiber),
            sodium_mg_per_serving=float(food.sodium),
            cost_per_serving=(
                float(food.cost_per_serving) if food.cost_per_serving is not None else None
            ),
            created_at=food.created_at,
            updated_at=food.updated_at,
        )
