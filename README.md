# Pantry Meal Optimizer

A pantry-based nutrition optimization system that recommends the highest-scoring meal a user can make from the foods currently available in their pantry.

---

## Motivation

Meal planning is often treated as a search problem:

> Given the foods currently available and a set of nutrition goals, what is the best meal to eat?

This project explores that problem by combining pantry management, nutrition evaluation, and optimization.

Version 1 established the optimization pipeline. The current application adds PostgreSQL persistence, a FastAPI API, and a React frontend.

---

## Features

- Food catalog
- Pantry management
- Nutrition constraint evaluation
- Deterministic OR-Tools CP-SAT meal optimization
- Optional randomized optimizer baseline
- Meal feasibility scoring
- Best meal selection
- Pantry updates after meal acceptance
- PostgreSQL persistence with SQLAlchemy 2
- Alembic database migrations
- Isolated unit and PostgreSQL integration tests
- FastAPI endpoints for pantry, profiles, and meals
- Responsive React and TypeScript frontend

---

## Local Setup

### Requirements

- Python 3.13 or newer
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL

Install the Python dependencies:

```bash
uv sync
```

### Development environment

Create `.env` in the repository root:

```dotenv
ENVIRONMENT=development
DATABASE_URL=postgresql+psycopg://YOUR_POSTGRES_USER@localhost:5432/nutrition_optimizer
CORS_ORIGINS=http://localhost:5173
FRONTEND_ORIGIN=http://localhost:5173
JWT_SECRET_KEY=replace-with-output-from-openssl-rand-hex-32
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
AUTH_COOKIE_SECURE=false
AUTH_COOKIE_SAMESITE=lax
```

Homebrew PostgreSQL usually creates a role matching your macOS username. You can check it with:

```bash
psql -d postgres -Atc 'SELECT current_user'
```

Create the development database, apply its migrations, and import the food catalog:

```bash
createdb nutrition_optimizer
uv run alembic upgrade head
uv run python scripts/seed_food_catalog.py
```

Create an account through `/register`. The catalog seed command can be run again safely; existing catalog records are updated rather than duplicated.

### Test environment

Create a second file named `.env.test`:

```dotenv
ENVIRONMENT=test
DATABASE_URL=postgresql+psycopg://YOUR_POSTGRES_USER@localhost:5432/nutrition_optimizer_test
CORS_ORIGINS=http://localhost:5173
FRONTEND_ORIGIN=http://localhost:5173
JWT_SECRET_KEY=a-test-only-secret-that-is-at-least-32-characters
AUTH_COOKIE_SECURE=false
```

Create the isolated test database:

```bash
createdb nutrition_optimizer_test
```

Then run the complete test suite:

```bash
uv run pytest
```

The database test fixtures apply the Alembic migration and clean the test tables between tests. Test configuration is rejected unless the database name ends in `_test`, which protects the development database from test cleanup.

Both `.env` and `.env.test` are ignored by Git. Commit `.env.example` only; never commit real database passwords or other secrets.

### Run the API

```bash
uv run uvicorn src.app.main:app --reload
```

The API is available under `http://127.0.0.1:8000/api/v1`. Interactive OpenAPI documentation is available at `http://127.0.0.1:8000/docs`.

### Run the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` requests to the local FastAPI server. To use another API host, set `VITE_API_BASE_URL` to its full `/api/v1` URL before starting Vite.

Frontend checks:

```bash
cd frontend
npm run typecheck
npm run lint
npm run format:check
npm test
npm run build
```

Run `npm run format` after editing frontend files to apply the shared formatting rules.

---

## Project Structure

```
.
├── data/
│   └── food_catalog.csv
│
├── docs/
│   └── v1_decision_log.md
│
├── src/
│   ├── database/
│   │   ├── models.py
│   │   └── session.py
│   ├── legacy/
│   │   ├── pantry.py
│   │   └── user.py
│   │
│   └── optimizer/
│       ├── nutrition_constraints.py
│       └── best_meal.py
│
├── alembic/
├── frontend/
│   └── src/
├── scripts/
│   └── seed_food_catalog.py
└── tests/
```

---

## How It Works

```
Food Catalog
      │
      ▼
 Pantry
      │
      ▼
Build CP-SAT Model
      │
      ▼
Evaluate Nutrition Constraints
      │
      ▼
Solve Strict or Relaxed Model
      │
      ▼
Verify and Return Best Meal
```

---

## Optimization Pipeline

Each candidate meal is represented as

```python
{
    "food_id": servings
}
```

The default CP-SAT optimizer

1. converts servings and nutrition data to consistent integer units
2. enforces pantry, meal-structure, and nutrition constraints
3. minimizes normalized target deviations and secondary preferences
4. retries with explicit violation variables if the strict model is infeasible
5. independently recalculates and scores the solved meal

The original randomized search remains available as an explicit baseline. See `docs/cp-sat-optimizer.md` for model details and limitations.

---

## Current Constraints

Required

- Calories
- Protein
- Carbohydrates
- Fat

Optional

- Sodium
- Sugar
- Cost

---

## Current Architecture

The project consists of the optimizer, PostgreSQL persistence layer, FastAPI service layer, and React client. The original CSV pantry workflow remains under `src/legacy` for reference.

### Pantry

Stores and manages the user's available foods.

### Nutrition Constraint Evaluator

Scores individual candidate meals.

### Meal Optimizer

Generates candidate meals and returns the best one found.

### API and frontend

FastAPI exposes versioned endpoints under `/api/v1`. The React client uses TanStack Query for API state and keeps route, form, and authentication concerns separate.

### Database

SQLAlchemy models store users, foods, pantry inventory, and accepted meals in PostgreSQL. Alembic manages schema changes, and the CSV catalog provides the initial food records.

### Authentication

Argon2 password hashes protect credentials. Short-lived JWT access tokens remain in browser memory, while rotating opaque refresh tokens use an HttpOnly cookie and hashed PostgreSQL records. See `docs/authentication.md`.

---

## Current Limitations

The current application intentionally keeps several production concerns out of scope.

Current limitations include

- manually maintained food catalog
- half-serving decision increments
- no deployment
- one meal optimization only
- no learned user preferences

---

## Future Work

Planned improvements include

- automated food ingestion
- better optimization algorithms
- continuous serving optimization
- email verification and account recovery
- production deployment
- machine learning preference model
- LLM-powered meal assistant

---

## Purpose

This project is primarily intended as a learning project exploring

- optimization
- software architecture
- data engineering
- machine learning integration
- full-stack application development

The long-term goal is to evolve this project into a production-style nutrition recommendation system.
