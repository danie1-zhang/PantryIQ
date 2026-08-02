from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from src.database.models import Food, PantryItem, User
from src.schemas.pantry import PantryItemCreate, PantryItemUpdate
from src.services.exceptions import BusinessRuleError, ConflictError, ResourceNotFoundError


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
        raise ResourceNotFoundError("Pantry item not found")
    return item


def add_to_pantry(
    session: Session, user: User, payload: PantryItemCreate
) -> tuple[PantryItem, bool]:
    food = session.get(Food, payload.food_id)
    if food is None:
        raise ResourceNotFoundError("Food not found")

    existing = session.scalar(
        select(PantryItem).where(PantryItem.user_id == user.id, PantryItem.food_id == food.id)
    )
    created = existing is None
    maximum = payload.max_servings_per_meal or payload.servings_available
    resulting_total = payload.servings_available + (
        existing.servings_available if existing is not None else Decimal("0")
    )
    if maximum > resulting_total:
        raise BusinessRuleError(
            "Maximum servings per meal cannot exceed resulting available servings"
        )

    statement = insert(PantryItem).values(
        user_id=user.id,
        food_id=food.id,
        servings_available=payload.servings_available,
        # PostgreSQL validates the proposed insert before resolving a conflict.
        # Keep that row valid even when an existing-row update requests a larger maximum.
        max_servings_per_meal=min(maximum, payload.servings_available),
        expiration_date=payload.expiration_date,
        notes=payload.notes,
        is_available=True,
    )
    update_values = {
        "servings_available": PantryItem.servings_available + statement.excluded.servings_available,
        "max_servings_per_meal": (
            maximum
            if payload.max_servings_per_meal is not None
            else PantryItem.max_servings_per_meal
        ),
        "is_available": True,
        "updated_at": func.now(),
    }
    if "expiration_date" in payload.model_fields_set:
        update_values["expiration_date"] = statement.excluded.expiration_date
    if "notes" in payload.model_fields_set:
        update_values["notes"] = statement.excluded.notes

    statement = statement.on_conflict_do_update(
        constraint="uq_pantry_items_user_food", set_=update_values
    ).returning(PantryItem.id)
    try:
        item_id = session.scalar(statement)
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError("Pantry item changed concurrently; retry the request") from exc

    session.expire_all()
    return get_owned_item(session, user, item_id), created


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
            raise BusinessRuleError("Maximum servings per meal cannot exceed available servings")

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
