from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.database.models import Food


def search_foods(
    session: Session, *, query: str | None, category: str | None, limit: int, offset: int
) -> list[Food]:
    statement = select(Food)
    if query:
        pattern = f"%{query.strip()}%"
        statement = statement.where(or_(Food.name.ilike(pattern), Food.brand.ilike(pattern)))
    if category:
        statement = statement.where(Food.category.ilike(category.strip()))
    statement = statement.order_by(Food.name, Food.id).limit(limit).offset(offset)
    return list(session.scalars(statement))


def get_food(session: Session, food_id: UUID) -> Food:
    food = session.get(Food, food_id)
    if food is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Food not found")
    return food
