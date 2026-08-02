from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from src.api.dependencies import DatabaseSession
from src.schemas.food import FoodResponse
from src.services.food_service import get_food, search_foods

router = APIRouter(prefix="/foods", tags=["foods"])


@router.get("", response_model=list[FoodResponse])
def list_foods(
    session: DatabaseSession,
    query: str | None = None,
    category: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[FoodResponse]:
    return [
        FoodResponse.from_food(food)
        for food in search_foods(
            session, query=query, category=category, limit=limit, offset=offset
        )
    ]


@router.get("/{food_id}", response_model=FoodResponse)
def food_detail(food_id: UUID, session: DatabaseSession) -> FoodResponse:
    return FoodResponse.from_food(get_food(session, food_id))
