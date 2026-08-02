from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import User
from src.database.session import get_db

DatabaseSession = Annotated[Session, Depends(get_db)]


def get_current_user(session: DatabaseSession) -> User:
    """Return the temporary development user until JWT authentication replaces this dependency."""

    user = session.scalar(select(User).where(User.username == "development_user"))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No development user is seeded",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
