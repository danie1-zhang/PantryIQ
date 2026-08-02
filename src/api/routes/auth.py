from fastapi import APIRouter, Cookie, Response, status

from src.api.dependencies import AppSettings, CurrentUser, DatabaseSession
from src.schemas.auth import (
    AuthUserResponse,
    LoginRequest,
    LoginResponse,
    RefreshResponse,
    RegisterRequest,
)
from src.security.cookies import REFRESH_COOKIE_NAME, clear_refresh_cookie, set_refresh_cookie
from src.security.tokens import create_access_token
from src.services.auth_service import (
    authenticate_user,
    create_refresh_session,
    register_user,
    revoke_all_user_sessions,
    revoke_refresh_token,
    rotate_refresh_session,
)
from src.services.exceptions import AuthenticationError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthUserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, session: DatabaseSession) -> AuthUserResponse:
    return AuthUserResponse.from_user(register_user(session, payload))


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    response: Response,
    session: DatabaseSession,
    settings: AppSettings,
) -> LoginResponse:
    user = authenticate_user(session, payload)
    refresh_token, _ = create_refresh_session(session, user, settings)
    session.commit()
    set_refresh_cookie(response, refresh_token, settings)
    return LoginResponse(
        access_token=create_access_token(user.id, settings),
        expires_in=settings.access_token_expire_minutes * 60,
        user=AuthUserResponse.from_user(user),
    )


@router.post("/refresh", response_model=RefreshResponse)
def refresh(
    response: Response,
    session: DatabaseSession,
    settings: AppSettings,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> RefreshResponse:
    if not refresh_token:
        raise AuthenticationError("Session is invalid or expired")
    user, new_refresh_token = rotate_refresh_session(session, refresh_token, settings)
    set_refresh_cookie(response, new_refresh_token, settings)
    return RefreshResponse(
        access_token=create_access_token(user.id, settings),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    session: DatabaseSession,
    settings: AppSettings,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> None:
    revoke_refresh_token(session, refresh_token)
    clear_refresh_cookie(response, settings)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all(
    response: Response,
    session: DatabaseSession,
    settings: AppSettings,
    user: CurrentUser,
) -> None:
    revoke_all_user_sessions(session, user)
    clear_refresh_cookie(response, settings)
