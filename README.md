# PantryIQ

PantryIQ builds meals from food you already have. Users can manage a pantry, set nutrition goals, describe preferences in plain English, and generate a meal with Google OR-Tools.

# Features

- Account registration and login
- Food catalog search and pantry tracking
- Profile and nutrition goals
- Natural-language dietary preferences
- CP-SAT meal optimization
- Transactional inventory deductions
- Meal history
- Responsive React interface

# Stack

The backend uses FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, and OR-Tools. The frontend uses React, TypeScript, Vite, TanStack Query, and React Router. Tests use Pytest, Vitest, and React Testing Library.

# Run with Docker

Docker Compose runs the frontend, backend, and PostgreSQL database.

```bash
cp .env.example .env
docker compose up --build
```

Replace the placeholder database password and JWT secret in `.env` before starting. Add `LLM_API_KEY` if you want live preference parsing.

Once the containers are healthy:

- Frontend: http://localhost:3000
- API: http://localhost:8000
- API docs: http://localhost:8000/docs
- PostgreSQL: `localhost:5433`

Load the food catalog:

```bash
docker compose exec backend python scripts/seed_food_catalog.py
```

The seed is safe to run more than once. See the [Docker guide](docs/docker-decision-log.md) for logs, migrations, container tests, and database resets.

# Run locally without Docker

You will need Python 3.13+, [uv](https://docs.astral.sh/uv/), PostgreSQL, and Node.js 20+.

Install the backend and create your environment file:

```bash
uv sync
cp .env.example .env
```

Change `DATABASE_URL` in `.env` to use `localhost`, then create and prepare the database:

```bash
createdb nutrition_optimizer
uv run alembic upgrade head
uv run python scripts/seed_food_catalog.py
```

Start FastAPI:

```bash
uv run uvicorn src.app.main:app --reload
```

Start the frontend in a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173.

# Tests

Backend integration tests need a separate PostgreSQL database ending in `_test`. This naming requirement prevents the test cleanup process from touching development data.

```bash
createdb nutrition_optimizer_test
cp .env.example .env.test
```

Update `.env.test` with your test database URL, then run:

```bash
uv run python -m black --check .
uv run python -m ruff check .
uv run python -m pytest
```

Frontend checks:

```bash
cd frontend
npm run format:check
npm run lint
npm run typecheck
npm test
npm run build
```

Both `.env` and `.env.test` are ignored by Git.

# How meal generation works

The backend loads the signed-in user’s available pantry foods and removes anything that violates inventory, allergen, dietary, or ownership rules. Natural-language preferences are parsed into a validated structure; the language model never queries the database or controls authorization.

OR-Tools selects foods in half-serving increments. It first tries to satisfy every active constraint. If that is impossible, it returns the closest alternative and clearly identifies the missed goals. Nutrition totals are recalculated before the response is returned.

Generating a meal does not alter the pantry. Inventory changes only when the user accepts a meal, at which point the backend rechecks quantities and records everything in one database transaction.

# Project layout

alembic/        database migrations
data/           food catalog and preference metadata
docs/           design notes and setup guides
frontend/       React application and frontend tests
scripts/        catalog seed script
src/            API, services, database, security, and optimizer
tests/          backend and database tests
compose.yaml    local Docker stack

# Design notes

- [Database](docs/database-decision-log.md)
- [API](docs/fastapi-decision-log.md)
- [Frontend](docs/frontend-decision-log.md)
- [Authentication](docs/authentication-decision-log.md)
- [Optimizer](docs/cp-sat-optimizer-decision-log.md)
- [Natural-language preferences](docs/nlp_preference_layer_decision_log.md)

# Current limitations

The food catalog and its preference metadata are maintained locally. Meal quantities use half-serving increments. Live preference parsing requires an external LLM provider. Email verification, password recovery, learned long-term preferences, and public hosting are outside the current scope.
