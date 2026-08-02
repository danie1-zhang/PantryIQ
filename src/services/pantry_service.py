from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from src.database.models import Food, PantryItem, User
from src.schemas.pantry import PantryItemCreate, PantryItemUpdate


def list_pantry(
    session: Session, user: User, *, available_only: bool, limit: int, offset: int
) -> list[PantryItem]:
    statement = (
        select(PantryItem)
        .options(joinedload(PantryItem.food))
        .join(PantryItem.food)
        .where(PantryItem.user_id == user.id)
    )
    if available_only:
        statement = statement.where(
            PantryItem.is_available.is_(True), PantryItem.servings_available > 0
        )
    statement = statement.order_by(Food.name, PantryItem.id).limit(limit).offset(offset)
    return list(session.scalars(statement))


def get_owned_item(session: Session, user: User, item_id: UUID) -> PantryItem:
    item = session.scalar(
        select(PantryItem)
        .options(joinedload(PantryItem.food))
        .where(PantryItem.id == item_id, PantryItem.user_id == user.id)
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pantry item not found")
    return item


def add_to_pantry(
    session: Session, user: User, payload: PantryItemCreate
) -> tuple[PantryItem, bool]:
    food = session.get(Food, payload.food_id)
    if food is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Food not found")

    item = session.scalar(
        select(PantryItem)
        .options(joinedload(PantryItem.food))
        .where(PantryItem.user_id == user.id, PantryItem.food_id == food.id)
    )
    created = item is None
    if item is None:
        maximum = payload.max_servings_per_meal or payload.servings_available
        if maximum > payload.servings_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum servings per meal cannot exceed available servings",
            )
        item = PantryItem(
            user_id=user.id,
            food=food,
            servings_available=payload.servings_available,
            max_servings_per_meal=maximum,
            expiration_date=payload.expiration_date,
            notes=payload.notes,
            is_available=True,
        )
        session.add(item)
    else:
        new_total = item.servings_available + payload.servings_available
        maximum = payload.max_servings_per_meal
        if maximum is not None and maximum > new_total:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum servings per meal cannot exceed resulting available servings",
            )
        item.servings_available = new_total
        if maximum is not None:
            item.max_servings_per_meal = maximum
        if "expiration_date" in payload.model_fields_set:
            item.expiration_date = payload.expiration_date
        if "notes" in payload.model_fields_set:
            item.notes = payload.notes
        item.is_available = True

    session.commit()
    session.refresh(item)
    return item, created


def update_pantry_item(
    session: Session, user: User, item_id: UUID, payload: PantryItemUpdate
) -> PantryItem:
    item = get_owned_item(session, user, item_id)
    values = payload.model_dump(exclude_unset=True)
    resulting_servings = values.get("servings_available", item.servings_available)
    resulting_maximum = values.get("max_servings_per_meal", item.max_servings_per_meal)

    if resulting_maximum > resulting_servings:
        if resulting_servings == 0 and "max_servings_per_meal" not in values:
            resulting_maximum = Decimal("0")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum servings per meal cannot exceed available servings",
            )

    for field, value in values.items():
        setattr(item, field, value)
    item.max_servings_per_meal = resulting_maximum
    if resulting_servings == 0:
        item.is_available = False
    elif "is_available" not in values:
        item.is_available = True

    session.commit()
    session.refresh(item)
    return item


def delete_pantry_item(session: Session, user: User, item_id: UUID) -> None:
    item = get_owned_item(session, user, item_id)
    session.delete(item)
    session.commit()
