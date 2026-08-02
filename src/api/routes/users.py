from fastapi import APIRouter

from src.api.dependencies import CurrentUser, DatabaseSession
from src.schemas.user import UserResponse, UserUpdate
from src.services.user_service import update_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def current_user_profile(user: CurrentUser) -> UserResponse:
    return UserResponse.from_user(user)


@router.patch("/me", response_model=UserResponse)
def update_current_user(
    payload: UserUpdate, session: DatabaseSession, user: CurrentUser
) -> UserResponse:
    return UserResponse.from_user(update_user(session, user, payload))
