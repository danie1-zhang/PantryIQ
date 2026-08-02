from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from src.api.dependencies import CurrentUser, DatabaseSession
from src.schemas.meal import (
    LoggedMealResponse,
    MealAcceptRequest,
    MealGenerateRequest,
    MealGenerateResponse,
    MealHistoryResponse,
)
from src.services.meal_service import accept_meal, generate_meal, get_meal, list_meals

router = APIRouter(prefix="/meals", tags=["meals"])


@router.post("/generate", response_model=MealGenerateResponse)
def generate(
    payload: MealGenerateRequest, session: DatabaseSession, user: CurrentUser
) -> MealGenerateResponse:
    return generate_meal(session, user, payload)


@router.post("/accept", response_model=LoggedMealResponse, status_code=status.HTTP_201_CREATED)
def accept(
    payload: MealAcceptRequest, session: DatabaseSession, user: CurrentUser
) -> LoggedMealResponse:
    return LoggedMealResponse.from_log(accept_meal(session, user, payload))


@router.get("", response_model=list[MealHistoryResponse])
def history(
    session: DatabaseSession,
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[MealHistoryResponse]:
    return [
        MealHistoryResponse.from_log(meal)
        for meal in list_meals(session, user, limit=limit, offset=offset)
    ]


@router.get("/{meal_log_id}", response_model=LoggedMealResponse)
def meal_detail(
    meal_log_id: UUID, session: DatabaseSession, user: CurrentUser
) -> LoggedMealResponse:
    return LoggedMealResponse.from_log(get_meal(session, user, meal_log_id))
