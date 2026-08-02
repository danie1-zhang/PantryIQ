from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from src.database.models import PantryItem

PositiveServings = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=3)]
NonnegativeServings = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=3)]
Notes = Annotated[str, StringConstraints(max_length=2000)]


class PantryItemCreate(BaseModel):
    food_id: UUID
    servings_available: PositiveServings
    max_servings_per_meal: PositiveServings | None = None
    expiration_date: date | None = None
    notes: Notes | None = None


class PantryItemUpdate(BaseModel):
    servings_available: NonnegativeServings | None = None
    max_servings_per_meal: NonnegativeServings | None = None
    expiration_date: date | None = None
    notes: Notes | None = None
    is_available: bool | None = None


class PantryItemResponse(BaseModel):
    id: UUID
    food_id: UUID
    food_name: str
    brand: str
    category: str
    servings_available: float
    max_servings_per_meal: float
    expiration_date: date | None
    notes: str | None
    is_available: bool
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
    def from_item(cls, item: PantryItem) -> "PantryItemResponse":
        food = item.food
        return cls(
            id=item.id,
            food_id=food.id,
            food_name=food.name,
            brand=food.brand,
            category=food.category,
            servings_available=float(item.servings_available),
            max_servings_per_meal=float(item.max_servings_per_meal),
            expiration_date=item.expiration_date,
            notes=item.notes,
            is_available=item.is_available,
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
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
