from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

from src.database.models import MealLog, MealLogItem

PositiveGoal = Annotated[Decimal, Field(gt=0)]
NonnegativeMaximum = Annotated[Decimal, Field(ge=0)]


class ExcludedMealItem(BaseModel):
    food_id: UUID
    servings: Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=1)]

    @field_validator("servings")
    @classmethod
    def require_half_servings(cls, value: Decimal) -> Decimal:
        if value * 2 != (value * 2).to_integral_value():
            raise ValueError("excluded meal servings must use half-serving increments")
        return value


class ExcludedMeal(BaseModel):
    items: Annotated[list[ExcludedMealItem], Field(min_length=1)]

    @model_validator(mode="after")
    def require_unique_foods(self) -> "ExcludedMeal":
        food_ids = [item.food_id for item in self.items]
        if len(food_ids) != len(set(food_ids)):
            raise ValueError("food IDs must be unique within an excluded meal")
        return self


class MealGenerateRequest(BaseModel):
    calorie_goal: PositiveGoal
    protein_goal: PositiveGoal
    carbs_goal: PositiveGoal
    fat_goal: PositiveGoal
    sodium_max: NonnegativeMaximum | None = None
    sugar_max: NonnegativeMaximum | None = None
    cost_max: NonnegativeMaximum | None = None
    number_of_candidates: Annotated[int, Field(ge=1, le=100_000)] = 10_000
    optimization_method: Literal["cp_sat", "random"] = "cp_sat"
    time_limit_seconds: Annotated[float, Field(ge=0.1, le=10)] = 2.0
    excluded_meals: Annotated[list[ExcludedMeal], Field(max_length=20)] = Field(
        default_factory=list
    )


class GeneratedMealItem(BaseModel):
    food_id: UUID
    food_name: str
    servings: float


class NutritionTotals(BaseModel):
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    sugar_g: float
    fiber_g: float = 0
    sodium_mg: float
    cost: float | None = None


class MealGenerateResponse(BaseModel):
    optimization_method: Literal["cp_sat", "random"]
    solver_status: str
    is_feasible: bool
    feasibility_score: float
    items: list[GeneratedMealItem]
    totals: NutritionTotals
    constraint_scores: dict[str, float]
    constraints_met: dict[str, bool]
    constraint_violations: dict[str, float] = Field(default_factory=dict)
    objective_value: float | None = None
    best_objective_bound: float | None = None
    solve_time_seconds: float
    candidates_generated: int
    valid_candidates_evaluated: int
    disclaimer: str


class MealAcceptItem(BaseModel):
    food_id: UUID
    servings: Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=3)]


class MealAcceptRequest(BaseModel):
    items: Annotated[list[MealAcceptItem], Field(min_length=1)]
    eaten_at: datetime | None = None
    rating: Annotated[int, Field(ge=1, le=5)] | None = None
    notes: Annotated[str, StringConstraints(max_length=2000)] | None = None

    @field_validator("eaten_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("eaten_at must include a timezone")
        return value

    @model_validator(mode="after")
    def require_unique_foods(self) -> "MealAcceptRequest":
        food_ids = [item.food_id for item in self.items]
        if len(food_ids) != len(set(food_ids)):
            raise ValueError("food IDs must be unique within a meal")
        return self


class LoggedMealItemResponse(BaseModel):
    food_id: UUID
    food_name: str
    servings: float
    calories_per_serving: float
    protein_g_per_serving: float
    carbs_g_per_serving: float
    fat_g_per_serving: float
    sugar_g_per_serving: float
    fiber_g_per_serving: float
    sodium_mg_per_serving: float

    @classmethod
    def from_item(cls, item: MealLogItem) -> "LoggedMealItemResponse":
        return cls(
            food_id=item.food_id,
            food_name=item.food_name,
            servings=float(item.servings),
            calories_per_serving=float(item.calories_per_serving),
            protein_g_per_serving=float(item.protein_per_serving),
            carbs_g_per_serving=float(item.carbs_per_serving),
            fat_g_per_serving=float(item.fat_per_serving),
            sugar_g_per_serving=float(item.sugar_per_serving),
            fiber_g_per_serving=float(item.fiber_per_serving),
            sodium_mg_per_serving=float(item.sodium_per_serving),
        )


class LoggedMealResponse(BaseModel):
    id: UUID
    eaten_at: datetime
    totals: NutritionTotals
    rating: int | None
    notes: str | None
    items: list[LoggedMealItemResponse]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_log(cls, log: MealLog) -> "LoggedMealResponse":
        return cls(
            id=log.id,
            eaten_at=log.eaten_at,
            totals=NutritionTotals(
                calories=float(log.total_calories),
                protein_g=float(log.total_protein),
                carbs_g=float(log.total_carbs),
                fat_g=float(log.total_fat),
                sugar_g=float(log.total_sugar),
                fiber_g=float(log.total_fiber),
                sodium_mg=float(log.total_sodium),
                cost=None,
            ),
            rating=log.rating,
            notes=log.notes,
            items=[LoggedMealItemResponse.from_item(item) for item in log.items],
            created_at=log.created_at,
            updated_at=log.updated_at,
        )


class MealHistoryResponse(BaseModel):
    id: UUID
    eaten_at: datetime
    total_calories: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    total_sugar_g: float
    total_fiber_g: float
    total_sodium_mg: float
    rating: int | None
    notes: str | None
    items: list[LoggedMealItemResponse]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_log(cls, log: MealLog) -> "MealHistoryResponse":
        return cls(
            id=log.id,
            eaten_at=log.eaten_at,
            total_calories=float(log.total_calories),
            total_protein_g=float(log.total_protein),
            total_carbs_g=float(log.total_carbs),
            total_fat_g=float(log.total_fat),
            total_sugar_g=float(log.total_sugar),
            total_fiber_g=float(log.total_fiber),
            total_sodium_mg=float(log.total_sodium),
            rating=log.rating,
            notes=log.notes,
            items=[LoggedMealItemResponse.from_item(item) for item in log.items],
            created_at=log.created_at,
            updated_at=log.updated_at,
        )
