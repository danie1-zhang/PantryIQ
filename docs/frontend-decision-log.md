# Frontend Decision Log

## Scope

The frontend provides the browser interface for pantry management, meal generation, meal history, and profile settings. It talks to FastAPI through `/api/v1`; it never connects directly to PostgreSQL or duplicates backend business rules.

The main request flow is:

```text
React page → API client → FastAPI → database or optimizer
           ← TanStack Query ← JSON response
```

## Stack

The frontend uses React, TypeScript, Vite, React Router, TanStack Query, and standard CSS.

- **React** fits the app's interactive forms and reusable views.
- **TypeScript** catches mismatches between components and API data during development.
- **Vite** keeps local development and production builds simple.
- **React Router** handles page navigation without full reloads.
- **TanStack Query** manages API caching, loading states, errors, mutations, and refetching.
- **Standard CSS** is enough for the current design and avoids adding another styling dependency.

Next.js was unnecessary because the app does not need server rendering, server components, or frontend API routes. Redux was also unnecessary because most shared data comes from the backend and belongs in TanStack Query's cache.

## Project structure

```text
frontend/src/
├── api/          API client and resource hooks
├── auth/         temporary login boundary
├── components/   reusable forms and cards
├── pages/        route-level views
├── router/       route definitions
├── test/         shared test setup and fixtures
└── types/        API request and response types
```

Pages coordinate queries and mutations. Components handle presentation and local form state. API modules are responsible for HTTP calls and cache invalidation.

## API client

All requests go through `src/api/client.ts`. It handles the base URL, JSON headers, response parsing, and readable API errors in one place.

The default base URL is `/api/v1`. Local Vite requests are proxied to FastAPI at `http://127.0.0.1:8000`. A different backend can be selected with:

```dotenv
VITE_API_BASE_URL=https://example.com/api/v1
```

Only public browser configuration should use a `VITE_` variable. Secrets must remain in the backend environment.

The client contains a temporary hook for attaching a future bearer token. When authentication is implemented, secure HTTP-only cookies would be safer than storing long-lived tokens in local storage.

## Server state

TanStack Query owns backend data such as foods, pantry items, profile details, and meal history. Components do not copy this data into a global store.

Mutations invalidate the related queries:

- Pantry creates, updates, and deletes refresh pantry data.
- Accepting a meal refreshes both pantry and meal history.
- Updating a profile replaces the cached profile with the response.

Local React state is limited to form values, modal visibility, and the current unsaved recommendation.

## Routes

```text
/login
/dashboard
/pantry
/generate-meal
/meals
/profile
```

Protected routes share the same layout and navigation. Unknown routes redirect to the dashboard.

### Login

Authentication is not implemented yet. The login page only enables access to the seeded development user already selected by FastAPI. The entered values are not sent to the backend.

This behavior is isolated under `src/auth` so real authentication can replace it without changing every page. It is strictly a development convenience and must not be treated as security.

### Dashboard

The dashboard loads the current profile, available pantry items, and the three most recent meals. It shows pantry counts and shortcuts to add food or generate a meal.

The meal metric is labeled **Recent meals** because the API request loads only three records, not a total count.

### Pantry

The pantry page uses:

```text
GET    /api/v1/pantry
GET    /api/v1/foods?query=...
POST   /api/v1/pantry/items
PATCH  /api/v1/pantry/items/{id}
DELETE /api/v1/pantry/items/{id}
```

Users select foods from the canonical catalog instead of entering arbitrary names. This ensures every pantry item has nutrition data the optimizer can use.

The frontend validates obvious input mistakes for quicker feedback, but FastAPI remains authoritative. Deletion requires confirmation and removes only the pantry record, never the canonical food.

### Meal generation

The generator loads defaults from `GET /api/v1/users/me` and submits constraints to:

```text
POST /api/v1/meals/generate
```

The optimizer runs on the backend. The frontend displays the returned foods, servings, nutrition totals, feasibility score, constraint results, and disclaimer.

Recommendations remain temporary until accepted. Generate Another sends the same constraints again; a deterministic optimal model may return the same meal. Recommendation history is not stored.

### Meal acceptance

Accepted items, servings, rating, and notes are sent to:

```text
POST /api/v1/meals/accept
```

The frontend does not submit trusted nutrition totals. FastAPI recalculates them, deducts pantry servings, and creates the meal log in one transaction. After success, the app refreshes pantry and meal-history data and opens the history page.

### Meal history

The history page uses:

```text
GET /api/v1/meals
GET /api/v1/meals/{id}
```

The list shows the meal date, foods, servings, macros, rating, and notes. Selecting a meal opens its full snapshot without leaving the page.

### Profile

The profile page uses:

```text
GET   /api/v1/users/me
PATCH /api/v1/users/me
```

Users can update supported physical information and nutrition goals. Email and username are read-only. Password hashes, secrets, and database fields are never exposed.

## Validation and errors

Forms provide basic client-side validation and disable submit buttons during requests. Backend validation is still the final authority. FastAPI error details are converted into readable messages, including Pydantic validation errors.

Pages include loading, empty, error, success, and confirmation states where appropriate.

## Styling and accessibility

The interface uses responsive CSS for desktop and mobile layouts. Forms have explicit labels, request feedback uses accessible roles, and modals can be closed with Escape.

The current modal does not trap keyboard focus. That should be improved before treating the interface as fully accessible.

## Testing and code quality

Vitest and React Testing Library cover pantry rendering, add and edit validation, edit and delete actions, meal constraints, recommendation acceptance, profile updates, and loading and error states.

The frontend checks are:

```bash
npm run format:check
npm run lint
npm run typecheck
npm test
npm run build
```

GitHub Actions runs the same checks for frontend changes. Prettier handles formatting, while ESLint handles code-quality rules.

The current tests mock API hooks. A later end-to-end suite should exercise the real FastAPI application against an isolated test database.

## Known limitations

- Login is development-only and provides no real authentication.
- List pages do not yet expose pagination controls.
- Production hosting must route unknown browser paths back to `index.html` for React Router.
- There is no top-level React error boundary yet.
- Generated recommendations are not persisted until accepted.
- Solver optimality applies only to the encoded nutrition and meal-structure rules, not taste.
