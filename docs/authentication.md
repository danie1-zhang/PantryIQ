# Authentication

PantryIQ uses short-lived JWT access tokens and opaque rotating refresh tokens. Passwords are hashed with Argon2 through `pwdlib`; plaintext passwords are never stored or returned.

## Session lifecycle

Registration normalizes email addresses and usernames, validates the password, and creates an active user. Registration does not log the user in automatically. Login verifies either an email or username using one generic failure response, returns a 15-minute access token, and sets a longer-lived refresh token as an HttpOnly cookie.

The access token contains only the user ID, token type, issued and expiration times, and a unique token ID. React holds it in memory and sends it as a bearer token. `get_current_user` validates the signature, expiration, required claims, token type, and user status before loading the user. Pantry and meal services continue to scope every owned query to that user ID.

The refresh token is random opaque data. PostgreSQL stores only its SHA-256 hash. A successful refresh revokes the presented record and creates a replacement in the same family. Reusing a revoked token revokes every active token in that family. Logout revokes the current token; logout-all revokes all refresh tokens for the authenticated user.

The frontend includes cookies on API requests, coordinates concurrent refresh attempts through one shared promise, retries a failed request once, and clears authentication and TanStack Query data if refresh fails. Initial page loading attempts refresh before protected routes decide whether to redirect. Access tokens and refresh tokens are never stored in local storage.

## Configuration

Required backend settings are documented in `.env.example`:

```dotenv
JWT_SECRET_KEY=
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
AUTH_COOKIE_SECURE=false
AUTH_COOKIE_SAMESITE=lax
FRONTEND_ORIGIN=http://localhost:5173
```

Generate a local secret with `openssl rand -hex 32` and place it only in `.env` and `.env.test`. Production must obtain the secret from its secret manager, use HTTPS, set `AUTH_COOKIE_SECURE=true`, and allow only its real frontend origin. Changing the JWT secret invalidates all access tokens; refresh records remain revocable but users must refresh or log in again.

The cookie path is `/api/v1/auth`, so the browser sends the refresh credential only to authentication endpoints. `SameSite=lax` suits same-site deployments. A truly cross-site frontend requires `SameSite=none`, secure cookies, HTTPS, and a deliberate CSRF review.

## Limits and production work

Login, registration, and refresh should be rate limited at the edge or application layer before public deployment. Refresh records should eventually be pruned after expiration. HTTPS, secure response headers, monitoring, secret rotation, and account-recovery/email-verification flows are deployment concerns not implemented here.
