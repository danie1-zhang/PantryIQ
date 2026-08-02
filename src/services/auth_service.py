from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.app.settings import Settings
from src.database.models import RefreshToken, User
from src.schemas.auth import LoginRequest, RegisterRequest
from src.security.passwords import hash_password, verify_password
from src.security.tokens import generate_refresh_token, hash_refresh_token
from src.services.exceptions import AuthenticationError, ConflictError

INVALID_CREDENTIALS = "Invalid email/username or password"
INVALID_SESSION = "Session is invalid or expired"
_DUMMY_PASSWORD_HASH = hash_password("not-a-real-user-password")


def register_user(session: Session, request: RegisterRequest) -> User:
    """Create an active account without starting a browser session."""

    existing = session.scalar(
        select(User).where(
            or_(func.lower(User.email) == request.email, User.username == request.username)
        )
    )
    if existing is not None:
        raise ConflictError("Email or username is already registered")
    user = User(
        email=str(request.email),
        username=request.username,
        password_hash=hash_password(request.password),
        name=request.name,
        is_active=True,
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError("Email or username is already registered") from exc
    session.refresh(user)
    return user


def authenticate_user(session: Session, request: LoginRequest) -> User:
    """Verify either a normalized email or username without revealing account existence."""

    identifier = request.email_or_username.strip().lower()
    user = session.scalar(
        select(User).where(
            or_(func.lower(User.email) == identifier, func.lower(User.username) == identifier)
        )
    )
    encoded_hash = user.password_hash if user is not None else _DUMMY_PASSWORD_HASH
    password_valid = verify_password(request.password, encoded_hash)
    if user is None or not password_valid or not user.is_active:
        raise AuthenticationError(INVALID_CREDENTIALS)
    return user


def create_refresh_session(
    session: Session, user: User, settings: Settings, *, family_id: UUID | None = None
) -> tuple[str, RefreshToken]:
    raw_token = generate_refresh_token()
    record = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_token),
        family_id=family_id or uuid4(),
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
    )
    session.add(record)
    return raw_token, record


def rotate_refresh_session(
    session: Session, raw_token: str, settings: Settings
) -> tuple[User, str]:
    """Consume one refresh token and replace it atomically in the same family."""

    now = datetime.now(UTC)
    record = session.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_refresh_token(raw_token))
        .with_for_update()
    )
    if record is None:
        raise AuthenticationError(INVALID_SESSION)
    if record.revoked_at is not None:
        revoke_token_family(session, record.family_id, now=now)
        session.commit()
        raise AuthenticationError(INVALID_SESSION)
    if record.expires_at <= now:
        record.revoked_at = now
        session.commit()
        raise AuthenticationError(INVALID_SESSION)

    user = session.get(User, record.user_id)
    if user is None or not user.is_active:
        revoke_token_family(session, record.family_id, now=now)
        session.commit()
        raise AuthenticationError(INVALID_SESSION)

    new_raw_token, replacement = create_refresh_session(
        session, user, settings, family_id=record.family_id
    )
    session.flush()
    record.revoked_at = now
    record.last_used_at = now
    record.replaced_by_token_id = replacement.id
    session.commit()
    return user, new_raw_token


def revoke_refresh_token(session: Session, raw_token: str | None) -> None:
    if not raw_token:
        return
    record = session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_token))
    )
    if record is not None and record.revoked_at is None:
        record.revoked_at = datetime.now(UTC)
        session.commit()


def revoke_token_family(session: Session, family_id: UUID, *, now: datetime | None = None) -> None:
    session.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now or datetime.now(UTC))
    )


def revoke_all_user_sessions(session: Session, user: User) -> None:
    session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    session.commit()
