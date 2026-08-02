from fastapi import Response

from src.app.settings import Settings

REFRESH_COOKIE_NAME = "pantryiq_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def set_refresh_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path=REFRESH_COOKIE_PATH,
    )


def clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path=REFRESH_COOKIE_PATH,
    )
