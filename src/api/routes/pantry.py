from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from src.api.dependencies import CurrentUser, DatabaseSession
from src.schemas.pantry import PantryItemCreate, PantryItemResponse, PantryItemUpdate
from src.services.pantry_service import (
    add_to_pantry,
    delete_pantry_item,
    list_pantry,
    update_pantry_item,
)

router = APIRouter(prefix="/pantry", tags=["pantry"])


@router.get("", response_model=list[PantryItemResponse])
def get_pantry(
    session: DatabaseSession,
    user: CurrentUser,
    available_only: bool = True,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PantryItemResponse]:
    return [
        PantryItemResponse.from_item(item)
        for item in list_pantry(
            session, user, available_only=available_only, limit=limit, offset=offset
        )
    ]


@router.post("/items", response_model=PantryItemResponse, status_code=status.HTTP_201_CREATED)
def add_pantry_item(
    payload: PantryItemCreate, response: Response, session: DatabaseSession, user: CurrentUser
) -> PantryItemResponse:
    item, created = add_to_pantry(session, user, payload)
    if not created:
        response.status_code = status.HTTP_200_OK
    return PantryItemResponse.from_item(item)


@router.patch("/items/{pantry_item_id}", response_model=PantryItemResponse)
def patch_pantry_item(
    pantry_item_id: UUID,
    payload: PantryItemUpdate,
    session: DatabaseSession,
    user: CurrentUser,
) -> PantryItemResponse:
    return PantryItemResponse.from_item(update_pantry_item(session, user, pantry_item_id, payload))


@router.delete("/items/{pantry_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_pantry_item(
    pantry_item_id: UUID, session: DatabaseSession, user: CurrentUser
) -> Response:
    delete_pantry_item(session, user, pantry_item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
