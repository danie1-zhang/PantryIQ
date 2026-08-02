# Pantry Meal Optimizer

A pantry-based nutrition optimization system that recommends the highest-scoring meal a user can make from the foods currently available in their pantry.

---

## Motivation

Meal planning is often treated as a search problem:

> Given the foods currently available and a set of nutrition goals, what is the best meal to eat?

This project explores that problem by combining pantry management, nutrition evaluation, and optimization.

Version 1 established the optimization pipeline. The current version adds a PostgreSQL persistence layer while keeping the API and frontend as future work.

---

## Features

- Food catalog
- Pantry management
- Nutrition constraint evaluation
- Randomized candidate meal generation
- Meal feasibility scoring
- Best meal selection
- Pantry updates after meal acceptance
- PostgreSQL persistence with SQLAlchemy 2
- Alembic database migrations
- Isolated unit and PostgreSQL integration tests

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
uv run python scripts/seed_development_user.py
```

The seed command can be run again safely. Existing catalog records are updated rather than duplicated.

### Test environment

Create a second file named `.env.test`:

```dotenv
ENVIRONMENT=test
DATABASE_URL=postgresql+psycopg://YOUR_POSTGRES_USER@localhost:5432/nutrition_optimizer_test
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
│   │   ├── session.py
│   │   ├── pantry.py
│   │   └── user.py
│   │
│   └── optimizer/
│       ├── nutrition_constraints.py
│       └── best_meal.py
│
├── alembic/
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
Generate Candidate Meals
      │
      ▼
Evaluate Nutrition Constraints
      │
      ▼
Score Each Candidate
      │
      ▼
Return Highest Scoring Meal
```

---

## Optimization Pipeline

Each candidate meal is represented as

```python
{
    "food_id": servings
}
```

For every generated candidate, the system

1. calculates nutrition totals
2. evaluates constraints
3. computes a feasibility score
4. ranks the candidate

After evaluating many candidates, the optimizer returns the highest-scoring feasible meal.

If no feasible meal exists, the highest-scoring infeasible meal is returned along with a disclaimer.

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

The project currently consists of the optimizer, legacy CSV pantry workflow, and PostgreSQL persistence layer.

### Pantry

Stores and manages the user's available foods.

### Nutrition Constraint Evaluator

Scores individual candidate meals.

### Meal Optimizer

Generates candidate meals and returns the best one found.

### User

Coordinates the entire application and user interaction.

### Database

SQLAlchemy models store users, foods, pantry inventory, and accepted meals in PostgreSQL. Alembic manages schema changes, and the CSV catalog provides the initial food records.

---

## Current Limitations

Version 1 intentionally keeps the system simple.

Current limitations include

- manually maintained food catalog
- randomized search
- no frontend
- no API routes yet
- no authentication yet
- no deployment
- one meal optimization only
- no learned user preferences

---

## Future Work

Planned improvements include

- automated food ingestion
- better optimization algorithms
- continuous serving optimization
- REST API
- web frontend
- user accounts
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
