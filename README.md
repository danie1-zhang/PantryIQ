# PantryIQ

PantryIQ is a full-stack meal planner that builds meals from food you already have. It tracks pantry inventory, applies nutrition goals and food preferences, and uses OR-Tools CP-SAT to find the best available meal.

## What it does

- Account registration and login with rotating refresh tokens
- Searchable food catalog and pantry management
- Nutrition goals for calories, protein, carbohydrates, fat, sodium, sugar, and cost
- Deterministic meal optimization with a relaxed fallback when no perfect meal exists
- Natural-language preferences such as “Greek, dairy-free, and not spicy”
- Transactional pantry deductions and meal history
- Responsive React interface

## Stack

- FastAPI, Pydantic, SQLAlchemy, Alembic, and PostgreSQL
- Google OR-Tools CP-SAT
- React, TypeScript, Vite, TanStack Query, and React Router
- Pytest, Vitest, and React Testing Library
- Docker and Docker Compose

## Quick start with Docker

Docker is the simplest way to run the complete application.

```bash
cp .env.example .env
docker compose up --build
```

Before starting, replace the placeholder PostgreSQL password and JWT secret in `.env`. Add `LLM_API_KEY` if you want live natural-language preference parsing.

Once the containers are healthy:

- Frontend: http://localhost:3000
- API: http://localhost:8000
- API documentation: http://localhost:8000/docs
- PostgreSQL: `localhost:5433`

Seed the food catalog once:

```bash
docker compose exec backend python scripts/seed_food_catalog.py
```

The seed is safe to rerun. Existing catalog rows are updated instead of duplicated.

See [the Docker guide](docs/docker-decision-log.md) for migrations, container tests, logs, persistence, and reset commands.

## Native development

Requirements:

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL
- Node.js 20+

Install backend dependencies and create the local configuration:

```bash
uv sync
cp .env.example .env
```

For native development, change `DATABASE_URL` in `.env` to use `localhost` rather than the Docker hostname:

```dotenv
DATABASE_URL=postgresql+psycopg://YOUR_POSTGRES_USER:YOUR_PASSWORD@localhost:5432/nutrition_optimizer
FRONTEND_ORIGIN=http://localhost:5173
CORS_ORIGINS=http://localhost:5173
```

Create and prepare the database:

```bash
createdb nutrition_optimizer
uv run alembic upgrade head
uv run python scripts/seed_food_catalog.py
```

Run FastAPI:

```bash
uv run uvicorn src.app.main:app --reload
```

Run the frontend in another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173.

## Tests

Backend integration tests require a separate PostgreSQL database whose name ends in `_test`:

```bash
createdb nutrition_optimizer_test
cp .env.example .env.test
```

Set these values in `.env.test`:

```dotenv
ENVIRONMENT=test
DATABASE_URL=postgresql+psycopg://YOUR_POSTGRES_USER:YOUR_PASSWORD@localhost:5432/nutrition_optimizer_test
JWT_SECRET_KEY=a-test-only-secret-that-is-at-least-32-characters
AUTH_COOKIE_SECURE=false
```

Run backend checks:

```bash
uv run python -m black --check .
uv run python -m ruff check .
uv run python -m pytest
```

Run frontend checks:

```bash
cd frontend
npm run format:check
npm run lint
npm run typecheck
npm test
npm run build
```

Tests refuse to clean a database unless its name ends in `_test`. Both `.env` and `.env.test` are ignored by Git.

## How meal generation works

FastAPI loads the authenticated user’s available pantry foods and converts them into typed optimizer inputs. Hard rules remove unsafe or unavailable foods. Soft preferences influence the objective without overriding nutrition, allergen, inventory, or ownership constraints.

CP-SAT first tries to find a fully feasible meal using half-serving increments. If that model is impossible, it solves a relaxed version that minimizes constraint violations. The nutrition evaluator then recalculates the result independently before it is returned.

Generating a meal never changes inventory. Inventory is deducted only after the user accepts a meal, when the backend revalidates quantities and writes the meal log in one transaction.

The older randomized optimizer remains available as a comparison baseline.

## Repository layout

```text
alembic/        database migrations
data/           food catalog and preference metadata
docs/           design notes and setup guides
frontend/       React application and frontend tests
scripts/        catalog seeding utilities
src/            FastAPI, database, services, security, and optimizer code
tests/          backend unit, API, optimizer, and database tests
compose.yaml    local three-service Docker stack
```

## Design notes

- [Database](docs/database-decision-log.md)
- [FastAPI](docs/fastapi-decision-log.md)
- [Frontend](docs/frontend-decision-log.md)
- [Authentication](docs/authentication-decision-log.md)
- [CP-SAT optimizer](docs/cp-sat-optimizer-decision-log.md)
- [Natural-language preferences](docs/nlp_preference_layer_decision_log.md)

## Current limitations

The food catalog and preference metadata are maintained locally. Optimization uses half-serving increments, and natural-language parsing needs a configured external LLM provider. Email verification, password recovery, learned long-term preferences, and production infrastructure are not implemented yet.
