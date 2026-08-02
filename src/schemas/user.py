from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, model_validator

from src.database.models import User

NonBlankName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
PositiveDecimal = Annotated[Decimal, Field(gt=0)]
NonnegativeDecimal = Annotated[Decimal, Field(ge=0)]


class UserResponse(BaseModel):
    id: UUID
    email: str
    username: str
    name: str
    age: int | None
    height_inches: float | None
    weight_pounds: float | None
    gender: str | None
    calorie_goal: float
    protein_goal: float
    carbs_goal: float
    fat_goal: float
    sodium_max: float | None
    sugar_max: float | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_user(cls, user: User) -> "UserResponse":
        return cls(
            id=user.id,
            email=user.email,
            username=user.username,
            name=user.name,
            age=user.age,
            height_inches=float(user.height_inches) if user.height_inches is not None else None,
            weight_pounds=float(user.weight_pounds) if user.weight_pounds is not None else None,
            gender=user.gender,
            calorie_goal=float(user.calorie_goal),
            protein_goal=float(user.protein_goal),
            carbs_goal=float(user.carbohydrate_goal),
            fat_goal=float(user.fat_goal),
            sodium_max=float(user.sodium_maximum) if user.sodium_maximum is not None else None,
            sugar_max=float(user.sugar_maximum) if user.sugar_maximum is not None else None,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


class UserUpdate(BaseModel):
    name: NonBlankName | None = None
    age: Annotated[int, Field(gt=0)] | None = None
    height_inches: PositiveDecimal | None = None
    weight_pounds: PositiveDecimal | None = None
    gender: Annotated[str, StringConstraints(max_length=50)] | None = None
    calorie_goal: PositiveDecimal | None = None
    protein_goal: PositiveDecimal | None = None
    carbs_goal: PositiveDecimal | None = None
    fat_goal: PositiveDecimal | None = None
    sodium_max: NonnegativeDecimal | None = None
    sugar_max: NonnegativeDecimal | None = None

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> "UserUpdate":
        required = {"name", "calorie_goal", "protein_goal", "carbs_goal", "fat_goal"}
        for field in required & self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self
