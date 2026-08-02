from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, EmailStr, StringConstraints, field_validator

from src.database.models import User
from src.security.passwords import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH

Username = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=3,
        max_length=50,
        pattern=r"^[A-Za-z0-9_.-]+$",
    ),
]
Password = Annotated[
    str,
    StringConstraints(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH),
]


class RegisterRequest(BaseModel):
    email: EmailStr
    username: Username
    password: Password
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.lower()


class LoginRequest(BaseModel):
    email_or_username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    password: Annotated[str, StringConstraints(min_length=1, max_length=MAX_PASSWORD_LENGTH)]


class AuthUserResponse(BaseModel):
    id: UUID
    email: str
    username: str
    name: str
    created_at: datetime

    @classmethod
    def from_user(cls, user: User) -> "AuthUserResponse":
        return cls(
            id=user.id,
            email=user.email,
            username=user.username,
            name=user.name,
            created_at=user.created_at,
        )


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUserResponse


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
