from sqlalchemy.orm import Session

from src.database.models import User
from src.schemas.user import UserUpdate

FIELD_MAP = {
    "carbs_goal": "carbohydrate_goal",
    "sodium_max": "sodium_maximum",
    "sugar_max": "sugar_maximum",
}


def update_user(session: Session, user: User, update: UserUpdate) -> User:
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(user, FIELD_MAP.get(field, field), value)
    session.commit()
    session.refresh(user)
    return user
