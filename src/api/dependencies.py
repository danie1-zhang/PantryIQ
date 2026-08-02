from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.app.settings import Settings, get_settings
from src.database.models import User
from src.database.session import get_db
from src.security.tokens import InvalidAccessTokenError, decode_access_token
from src.services.exceptions import AuthenticationError

DatabaseSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    session: DatabaseSession,
    settings: AppSettings,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    """Resolve the request user exclusively from a verified bearer access token."""

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Authentication required")
    try:
        payload = decode_access_token(credentials.credentials, settings)
    except InvalidAccessTokenError as exc:
        raise AuthenticationError("Invalid or expired access token") from exc
    user = session.get(User, payload.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("Invalid or expired access token")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
