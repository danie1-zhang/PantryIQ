from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import secrets
from uuid import UUID, uuid4

import jwt

from src.app.settings import Settings


@dataclass(frozen=True)
class AccessTokenPayload:
    user_id: UUID
    token_id: UUID
    issued_at: datetime
    expires_at: datetime


class InvalidAccessTokenError(ValueError):
    pass


def create_access_token(user_id: UUID, settings: Settings) -> str:
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {
            "sub": str(user_id),
            "type": "access",
            "iat": now,
            "exp": expires_at,
            "jti": str(uuid4()),
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str, settings: Settings) -> AccessTokenPayload:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "type", "iat", "exp", "jti"]},
        )
        if payload["type"] != "access":
            raise InvalidAccessTokenError("Invalid token type")
        return AccessTokenPayload(
            user_id=UUID(payload["sub"]),
            token_id=UUID(payload["jti"]),
            issued_at=datetime.fromtimestamp(payload["iat"], UTC),
            expires_at=datetime.fromtimestamp(payload["exp"], UTC),
        )
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise InvalidAccessTokenError("Invalid access token") from exc


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
