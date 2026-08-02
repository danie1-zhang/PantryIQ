from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Response
from sqlalchemy import select

from src.app.settings import Settings, get_settings
from src.database.models import RefreshToken, User
from src.security.cookies import REFRESH_COOKIE_NAME, set_refresh_cookie
from src.security.passwords import hash_password, verify_password
from src.security.tokens import create_access_token

PASSWORD = "correct horse battery staple"


def register_payload(**overrides):
    payload = {
        "email": "New.User@Example.COM",
        "username": "new_user",
        "password": PASSWORD,
        "name": "New User",
    }
    payload.update(overrides)
    return payload


def create_login_user(session, **overrides) -> User:
    values = {
        "email": "login@example.com",
        "username": "login_user",
        "password_hash": hash_password(PASSWORD),
        "name": "Login User",
        "is_active": True,
    }
    values.update(overrides)
    user = User(**values)
    session.add(user)
    session.commit()
    return user


def test_registration_normalizes_and_never_exposes_plaintext(client, api_session) -> None:
    response = client.post("/api/v1/auth/register", json=register_payload())

    assert response.status_code == 201
    assert response.json()["email"] == "new.user@example.com"
    assert response.json()["username"] == "new_user"
    assert "password" not in response.json()
    assert "password_hash" not in response.json()
    user = api_session.scalar(select(User).where(User.email == "new.user@example.com"))
    assert user is not None
    assert user.password_hash != PASSWORD
    assert verify_password(PASSWORD, user.password_hash)


def test_registration_rejects_duplicate_email_and_username(client, api_session) -> None:
    create_login_user(api_session)

    duplicate_email = client.post(
        "/api/v1/auth/register", json=register_payload(email="LOGIN@EXAMPLE.COM")
    )
    duplicate_username = client.post(
        "/api/v1/auth/register", json=register_payload(username="login_user")
    )

    assert duplicate_email.status_code == 409
    assert duplicate_username.status_code == 409


def test_login_by_email_sets_cookie_and_creates_safe_tokens(client, api_session) -> None:
    user = create_login_user(api_session)
    response = client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "LOGIN@EXAMPLE.COM", "password": PASSWORD},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert "password_hash" not in body["user"]
    payload = jwt.decode(
        body["access_token"],
        get_settings().jwt_secret_key.get_secret_value(),
        algorithms=[get_settings().jwt_algorithm],
    )
    assert payload["sub"] == str(user.id)
    assert payload["type"] == "access"
    assert set(payload) == {"sub", "type", "iat", "exp", "jti"}
    record = api_session.scalar(select(RefreshToken).where(RefreshToken.user_id == user.id))
    assert record is not None
    assert record.token_hash != response.cookies[REFRESH_COOKIE_NAME]
    assert len(record.token_hash) == 64
    cookie = response.headers["set-cookie"]
    assert f"{REFRESH_COOKIE_NAME}=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Secure" not in cookie


def test_production_refresh_cookie_is_secure(test_settings) -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        database_url=test_settings.database_url,
        jwt_secret_key="production-secret-key-that-is-at-least-32-characters",
        auth_cookie_secure=True,
    )
    response = Response()
    set_refresh_cookie(response, "opaque-token", settings)

    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "Path=/api/v1/auth" in cookie


def test_login_by_username_works(client, api_session) -> None:
    create_login_user(api_session)
    response = client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "LOGIN_USER", "password": PASSWORD},
    )
    assert response.status_code == 200


def test_login_failure_is_generic_for_bad_password_unknown_and_inactive(
    client, api_session
) -> None:
    create_login_user(api_session)
    create_login_user(
        api_session, email="inactive@example.com", username="inactive", is_active=False
    )
    attempts = [
        {"email_or_username": "login@example.com", "password": "wrong"},
        {"email_or_username": "missing@example.com", "password": "wrong"},
        {"email_or_username": "inactive", "password": PASSWORD},
    ]

    responses = [client.post("/api/v1/auth/login", json=attempt) for attempt in attempts]
    assert [response.status_code for response in responses] == [401, 401, 401]
    assert {response.json()["detail"] for response in responses} == {
        "Invalid email/username or password"
    }


def test_current_user_requires_valid_active_access_token(client, api_user, api_session) -> None:
    valid = client.get("/api/v1/users/me")
    missing = client.get("/api/v1/users/me", headers={"Authorization": ""})
    malformed = client.get("/api/v1/users/me", headers={"Authorization": "Bearer not-a-token"})
    opaque_refresh = client.get(
        "/api/v1/users/me", headers={"Authorization": "Bearer opaque-refresh-token"}
    )
    settings = get_settings()
    expired = jwt.encode(
        {
            "sub": str(api_user.id),
            "type": "access",
            "iat": datetime.now(UTC) - timedelta(hours=2),
            "exp": datetime.now(UTC) - timedelta(hours=1),
            "jti": "d6907d5c-02ea-4f06-9826-f98f9405dd02",
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    expired_response = client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {expired}"}
    )

    assert valid.status_code == 200
    for response in (missing, malformed, opaque_refresh, expired_response):
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"

    api_user.is_active = False
    api_session.commit()
    inactive = client.get("/api/v1/users/me")
    assert inactive.status_code == 401


def test_refresh_rotates_and_reuse_revokes_family(client, api_session) -> None:
    user = create_login_user(api_session)
    login = client.post(
        "/api/v1/auth/login",
        json={"email_or_username": user.email, "password": PASSWORD},
    )
    old_token = login.cookies[REFRESH_COOKIE_NAME]

    refreshed = client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200
    new_token = refreshed.cookies[REFRESH_COOKIE_NAME]
    assert new_token != old_token
    api_session.expire_all()
    records = list(api_session.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id)))
    assert len(records) == 2
    assert sum(record.revoked_at is not None for record in records) == 1

    client.cookies.set(REFRESH_COOKIE_NAME, old_token, path="/api/v1/auth")
    reused = client.post("/api/v1/auth/refresh")
    assert reused.status_code == 401
    api_session.expire_all()
    assert all(
        record.revoked_at is not None
        for record in api_session.scalars(
            select(RefreshToken).where(RefreshToken.user_id == user.id)
        )
    )


def test_refresh_rejects_unknown_expired_revoked_and_inactive_sessions(client, api_session) -> None:
    client.cookies.set(REFRESH_COOKIE_NAME, "unknown", path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh").status_code == 401

    user = create_login_user(api_session)
    client.post(
        "/api/v1/auth/login",
        json={"email_or_username": user.username, "password": PASSWORD},
    )
    record = api_session.scalar(select(RefreshToken).where(RefreshToken.user_id == user.id))
    record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    api_session.commit()
    assert client.post("/api/v1/auth/refresh").status_code == 401

    client.post(
        "/api/v1/auth/login",
        json={"email_or_username": user.username, "password": PASSWORD},
    )
    record = api_session.scalar(
        select(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .order_by(RefreshToken.created_at.desc())
    )
    record.revoked_at = datetime.now(UTC)
    api_session.commit()
    assert client.post("/api/v1/auth/refresh").status_code == 401

    client.post(
        "/api/v1/auth/login",
        json={"email_or_username": user.username, "password": PASSWORD},
    )
    user.is_active = False
    api_session.commit()
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_logout_is_idempotent_and_logout_all_revokes_sessions(client, api_session) -> None:
    user = create_login_user(api_session)
    client.post(
        "/api/v1/auth/login",
        json={"email_or_username": user.username, "password": PASSWORD},
    )
    first_logout = client.post("/api/v1/auth/logout")
    second_logout = client.post("/api/v1/auth/logout")
    assert first_logout.status_code == 204
    assert second_logout.status_code == 204
    assert f'{REFRESH_COOKIE_NAME}=""' in first_logout.headers["set-cookie"]

    client.post(
        "/api/v1/auth/login",
        json={"email_or_username": user.username, "password": PASSWORD},
    )
    client.post(
        "/api/v1/auth/login",
        json={"email_or_username": user.username, "password": PASSWORD},
    )
    access_token = create_access_token(user.id, get_settings())
    response = client.post(
        "/api/v1/auth/logout-all", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 204
    api_session.expire_all()
    assert all(
        record.revoked_at is not None
        for record in api_session.scalars(
            select(RefreshToken).where(RefreshToken.user_id == user.id)
        )
    )


def test_all_owned_routes_reject_unauthenticated_requests(client) -> None:
    requests = [
        ("GET", "/api/v1/pantry", None),
        ("POST", "/api/v1/pantry/items", {}),
        ("PATCH", "/api/v1/pantry/items/00000000-0000-0000-0000-000000000000", {}),
        ("DELETE", "/api/v1/pantry/items/00000000-0000-0000-0000-000000000000", None),
        ("GET", "/api/v1/users/me", None),
        ("PATCH", "/api/v1/users/me", {}),
        ("POST", "/api/v1/meals/generate", {}),
        ("POST", "/api/v1/meals/accept", {}),
        ("GET", "/api/v1/meals", None),
        ("GET", "/api/v1/meals/00000000-0000-0000-0000-000000000000", None),
    ]

    for method, path, body in requests:
        response = client.request(method, path, json=body, headers={"Authorization": ""})
        assert response.status_code == 401, (method, path, response.text)


def test_complete_browser_session_flow(client) -> None:
    registered = client.post("/api/v1/auth/register", json=register_payload())
    assert registered.status_code == 201

    logged_in = client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "new_user", "password": PASSWORD},
    )
    access_token = logged_in.json()["access_token"]
    pantry = client.get("/api/v1/pantry", headers={"Authorization": f"Bearer {access_token}"})
    assert pantry.status_code == 200
    assert pantry.json() == []

    refreshed = client.post("/api/v1/auth/refresh")
    rotated_access_token = refreshed.json()["access_token"]
    assert rotated_access_token != access_token
    assert (
        client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {rotated_access_token}"},
        ).json()["username"]
        == "new_user"
    )

    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.post("/api/v1/auth/refresh").status_code == 401
