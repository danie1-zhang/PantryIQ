# FastAPI Decision Log

This document records the main decisions behind the HTTP API. It describes the current implementation, not every feature that may eventually be added.

# Role of the API

FastAPI sits between the future React client and the application’s data and business logic:

HTTP request
    → FastAPI route
    → Pydantic validation
    → service function
    → SQLAlchemy session
    → PostgreSQL
    → response schema
    → JSON response

The browser does not connect directly to PostgreSQL or run the optimizer. Ownership checks, nutrition calculations, pantry updates, and transactions stay in the backend.

FastAPI was selected because the optimizer is already written in Python. It also provides dependency injection, Pydantic integration, OpenAPI generation, and interactive documentation without requiring another backend stack.

The application remains a modular monolith. Routes, schemas, services, database code, and optimization code have separate responsibilities, but they run as one deployable backend. There is no current need for service-to-service networking or distributed transactions.

# Versioning and application setup

Public endpoints use the `/api/v1` prefix. A later incompatible API can use another version without immediately breaking V1 clients.

The application entry point is `src.app.main:app`. It:

- creates the FastAPI application
- registers domain-error handlers
- installs the route modules under `/api/v1`
- configures CORS from validated settings
- does not create tables at startup

Alembic remains responsible for schema changes. API documentation is available at `/docs` while the application is running.

# Code organization

src/
├── api/
│   ├── dependencies.py
│   ├── exception_handlers.py
│   └── routes/
├── app/
│   ├── main.py
│   └── settings.py
├── database/
│   ├── models.py
│   └── session.py
├── schemas/
├── services/
├── optimizer/
└── legacy/

Routes define HTTP paths, accept validated data, call services, and return response models. They should not contain large queries or transaction workflows.

Schemas define the public contract. SQLAlchemy models are kept separate so database-only fields, such as `password_hash`, are not exposed accidentally. Response builders also translate internal names such as `carbohydrate_goal` into the API’s `carbs_goal`.

Services contain ownership rules, queries, pantry behavior, optimizer integration, and meal-acceptance logic. They raise application exceptions rather than FastAPI exceptions, which keeps them usable outside HTTP code.

Dependencies provide one database session per request and resolve the current user from a verified bearer access token.

The CSV-era pantry and command-line user classes live in `src/legacy`; `src/database` is reserved for PostgreSQL persistence.

# Validation and data integrity

Validation happens at three levels:

1. Pydantic checks request structure, UUIDs, dates, numeric ranges, duplicate meal items, and field lengths.
2. Services enforce ownership and rules that depend on current database state.
3. PostgreSQL constraints protect stored data even if another caller bypasses the API.

Frontend validation may improve usability, but it is never treated as authoritative.

The API uses explicit response schemas rather than returning arbitrary ORM objects. Password hashes, database URLs, and internal secrets are never included in responses.

## Sessions and transactions

Each request receives its own synchronous SQLAlchemy session. Sessions are not shared between requests.

Read operations do not commit. Write services commit once at the business boundary. Closing the request session rolls back any uncommitted work after an expected failure.

Synchronous SQLAlchemy is used throughout. Introducing a second asynchronous database pattern would complicate session and transaction behavior without helping the current workload.

# Authentication and identity

Registration hashes passwords with Argon2. Login issues a short-lived JWT access token and an opaque refresh token whose hash is stored in PostgreSQL. Refresh rotates the token; reuse revokes its family. The browser keeps access tokens in memory and refresh tokens in an HttpOnly cookie.

Clients cannot provide arbitrary user IDs. Every user-owned query receives its identity through the verified current-user dependency and scopes records by that user.

Owned records are queried using both their ID and the current user’s ID. A record belonging to someone else returns `404`, which avoids disclosing that the record exists.

# Error handling

Services raise a small set of domain errors:

- `ResourceNotFoundError`
- `BusinessRuleError`
- `ConflictError`

FastAPI handlers translate them to `404`, `400`, and `409` responses. Pydantic validation failures return `422`. Unexpected exceptions remain visible as server errors instead of being mislabeled as client mistakes.

# Endpoint decisions

# Health

`GET /api/v1/health` returns `{"status": "ok"}`. It confirms that the application is running but does not require a successful database query. A separate readiness check can be added if deployment infrastructure needs one.

# Foods

`GET /api/v1/foods` supports name/brand search, category filtering, limits, and offsets. Results are ordered consistently by name.

`GET /api/v1/foods/{food_id}` returns one canonical food or `404`.

The current `Food` model has no `is_active` column, so every stored food is considered active. Deactivation can be added later if catalog administration requires it.

# Current user

`GET /api/v1/users/me` returns public profile fields and default nutrition goals. It never returns `password_hash`.

`PATCH /api/v1/users/me` updates only supplied profile and nutrition fields. Email, username, password data, IDs, and timestamps cannot be changed through this endpoint.

# Pantry

`GET /api/v1/pantry` returns the current user’s inventory joined with its canonical food details. By default, unavailable and depleted items are omitted.

`POST /api/v1/pantry/items` creates or increments a user-food row. PostgreSQL `ON CONFLICT DO UPDATE` makes the upsert safe when concurrent requests add the same food. The unique `(user_id, food_id)` rule is preserved, and simultaneous additions combine their quantities rather than creating duplicates.

New rows return `201`; ordinary updates return `200`. In an extremely narrow concurrent first-insert race, both callers may be told the row was newly created even though only one physical row is stored. Data remains correct.

`PATCH /api/v1/pantry/items/{pantry_item_id}` updates quantities and metadata without allowing ownership or food IDs to change. When servings reach zero, the item is marked unavailable and its per-meal maximum is reduced to zero.

`DELETE /api/v1/pantry/items/{pantry_item_id}` deletes only the inventory row. It never deletes the canonical food.

# Meal generation

`POST /api/v1/meals/generate` loads usable pantry items for the current user and converts them into typed optimizer inputs. Category spelling is normalized in the adapter boundary.

OR-Tools CP-SAT is the default strategy. The request can select the original randomized optimizer as a baseline. CP-SAT uses half-serving decisions, a bounded 0.1–10 second solve time, strict nutrition constraints, and a relaxed model when strict nutrition is infeasible. The response includes the method, solver status, objective metadata, solve time, and any constraint violations.

Generation requests may include up to 20 previously returned meals. The optimizer excludes those exact food-and-serving combinations without storing recommendation history. This gives the current browser session variety while keeping generation read-only.

The existing nutrition evaluator independently recalculates and scores every result. Generation does not deduct inventory or persist recommendation history. Generate Another simply calls the endpoint again and may return the same deterministic optimum.

# Meal acceptance

`POST /api/v1/meals/accept` performs the main transactional workflow:

1. Validate the request and reject duplicate food IDs.
2. Load the current user’s requested pantry rows.
3. Lock those pantry rows with `FOR UPDATE`.
4. Verify availability and quantities before changing anything.
5. Recalculate nutrition from canonical food records.
6. Deduct servings and update availability.
7. Create one meal log and its snapshot items.
8. Commit once.

If validation fails, the request session rolls back and no partial deductions or log rows remain.

The backend never trusts nutrition totals sent by the client. Food names and per-serving nutrition are stored as snapshots so historical meals do not change when canonical nutrition is corrected later.

The schema does not currently store total meal cost or cost snapshots. The generation response can calculate cost, but accepted-meal history does not invent fields that are absent from the database.

# Meal history

`GET /api/v1/meals` returns only the current user’s accepted meals, newest first, with bounded pagination and eagerly loaded items.

`GET /api/v1/meals/{meal_log_id}` returns one owned meal and its snapshots. Missing records and records owned by another user both return `404`.

# Pagination

Food search, pantry retrieval, and meal history use bounded `limit` and `offset` parameters. Offset pagination is adequate for current data volumes. Cursor pagination can be considered if large datasets make offsets inefficient.

# CORS and configuration

CORS origins come from validated environment configuration:

```dotenv
CORS_ORIGINS=http://localhost:5173
```

Multiple origins may be comma-separated. Production should list only known frontend origins.

Other configuration currently includes `ENVIRONMENT` and `DATABASE_URL`. `.env` and `.env.test` are ignored; `.env.example` contains safe placeholders.

# Testing and CI

API tests use `nutrition_optimizer_test`, apply Alembic migrations, and clean the test tables between cases. The settings layer refuses test mode unless the database name ends in `_test`.

Tests cover authentication and refresh rotation, health, food queries, profile updates, pantry ownership and CRUD, atomic upserts, deterministic optimizer responses, meal acceptance, rollback behavior, snapshots, and meal-history isolation.

The concurrent pantry test uses two independent SQLAlchemy sessions to verify that simultaneous first additions create one row with the combined quantity.

GitHub Actions runs Black, Ruff, the complete pytest suite, and an application-import check against a PostgreSQL service for every push and pull request.

# Deliberately deferred work

- food deactivation and catalog administration
- recommendation-history tables
- React integration
- RabbitMQ and background workers
- Docker and deployment configuration
- rate limiting and production monitoring
- query-specific index tuning based on measured traffic

These features should be added when their product stage requires them rather than expanding the initial API unnecessarily.
