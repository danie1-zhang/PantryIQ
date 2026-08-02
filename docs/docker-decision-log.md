# Docker setup

The Compose stack runs three services behind one browser-facing frontend origin:

Browser http://localhost:3000
  -> Nginx frontend container
     -> static React files
     -> /api/* proxy to backend:8000
        -> FastAPI
           -> postgres:5432

Nginx proxies `/api` to FastAPI, so the browser never needs to resolve Docker service names and local authentication cookies stay same-origin. FastAPI remains available directly at `http://localhost:8000` for development and API documentation.

# Prerequisites

- Docker Desktop or Docker Engine with Compose v2
- Free host ports 3000, 8000, and 5433, or alternate values in `.env`
- An LLM provider key if natural-language preference parsing should call a live provider

# Configure and start

```bash
cp .env.example .env
```

Replace `POSTGRES_PASSWORD` and `JWT_SECRET_KEY` in `.env`. Use an alphanumeric database password because it is interpolated into a URL. Generate a JWT secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Set `LLM_API_KEY` when live NLP parsing is needed. It is passed only to the backend container and is never included in the frontend image.

Validate and start the stack:

```bash
docker compose config
docker compose up --build
docker compose ps
```

Open `http://localhost:3000`. API documentation is at `http://localhost:8000/docs`, and the health endpoint is `http://localhost:8000/api/v1/health`.

# Migrations and food data

The backend entrypoint waits for PostgreSQL, runs `alembic upgrade head`, and starts Uvicorn only if migration succeeds. It never calls `Base.metadata.create_all()`.

Food seeding is disabled by default. To seed on the next backend start, set:
SEED_FOODS_ON_START=true

Then recreate the backend:

```bash
docker compose up -d --build --force-recreate backend
```

The seed script upserts foods by external source and ID, so repeated runs update existing catalog rows instead of duplicating them. Set the flag back to `false` afterward. To seed manually:

```bash
docker compose exec backend python scripts/seed_food_catalog.py
```

# Common operations

```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose exec backend sh
docker compose exec postgres psql -U pantryiq -d pantryiq
docker compose build backend
docker compose up -d --no-deps backend
docker compose down
```

The named `postgres_data` volume survives normal stops, starts, rebuilds, and `docker compose down`.

This command is destructive:

```bash
docker compose down -v
```

It removes the PostgreSQL volume and all local application data.

# Tests in containers

Backend and frontend Dockerfiles include separate test stages so test dependencies do not enter runtime images.

Backend tests require the isolated PostgreSQL test database used by the existing test configuration. With the stack running, create it once and build the test image:

```bash
docker compose exec postgres createdb -U pantryiq pantryiq_test
docker build --target test -t pantryiq-backend-test .
docker run --rm --network pantryiq_default \
  -e ENVIRONMENT=test \
  -e DATABASE_URL=postgresql+psycopg://pantryiq:YOUR_PASSWORD@postgres:5432/pantryiq_test \
  -e JWT_SECRET_KEY=replace_with_at_least_32_random_characters \
  pantryiq-backend-test python -m pytest
```

Replace `YOUR_PASSWORD` with the local `POSTGRES_PASSWORD`. The tests clear only the `_test` database. If the database already exists, `createdb` reports that fact and no action is needed.

Frontend tests, type checking, and production build:

```bash
docker build --target test -t pantryiq-frontend-test frontend
docker run --rm pantryiq-frontend-test npm test
docker run --rm pantryiq-frontend-test npm run typecheck
docker build --target runtime -t pantryiq-frontend frontend
```

# Authentication and local security

Local Compose uses an HttpOnly refresh cookie with `SameSite=lax` and `Secure=false` because the documented URL uses HTTP. The access token remains in frontend memory. Production must use HTTPS and set `AUTH_COOKIE_SECURE=true`. Keep an exact production frontend origin in `FRONTEND_ORIGIN` and `CORS_ORIGINS`; never use a wildcard with credentialed requests.

The proxy setup uses relative `VITE_API_BASE_URL=/api/v1`. Backend-only values such as the PostgreSQL password, JWT secret, and LLM API key are runtime environment variables and are not frontend build arguments.

# Production differences

This Compose file is a stable local deployment, not a complete public-cloud production platform. A public deployment still needs HTTPS termination, managed secret injection, backups, monitoring, production cookie settings, restricted database exposure, provider rate limiting, and an image registry/deployment target.
