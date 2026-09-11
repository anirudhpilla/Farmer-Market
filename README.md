# Farmer Market

A full-stack shopping-cart assessment built with React, TypeScript, FastAPI,
SQLAlchemy, and PostgreSQL. Customers can browse products and shop as guests.
An administrator can manage products and inspect confirmed orders.

The implementation is intentionally a small modular monolith. It keeps ordinary
queries inside clearly named route files and avoids generic repository/service
layers. The two workflows that need careful coordination—refresh-token rotation
and checkout—remain visible and testable rather than hidden behind scaffolding.

## Features

### Customer

- Responsive product catalog, details, search, category filter, and pagination
- Persistent anonymous cart with add, update, remove, totals, and stock warnings
- Checkout review with stale cart, price, availability, and stock validation
- Idempotent order placement and an owned order-confirmation page

### Administrator

- Seeded admin login with Argon2 password hashing
- Short-lived JWT access tokens held in browser memory
- Opaque HttpOnly refresh cookies with rotation and replay-family revocation
- Create, edit, activate/deactivate, soft-delete, and update product stock
- Optimistic version check for administrator stock edits
- Paginated confirmed-order list and order detail

### Correctness and security

- Pydantic request validation and response filtering
- PostgreSQL foreign keys, checks, uniqueness rules, and incremental migrations
- Decimal money on the backend and decimal strings in JSON
- Guest and refresh credentials stored as digests rather than raw tokens
- Origin plus session-bound CSRF checks on cookie-authenticated writes
- Basic single-process authentication throttling, request-ID logging, and safe global 500 responses
- Object-level cart and order ownership checks
- Transactional checkout with row locks, one commit, and immutable order snapshots

## Project layout

```text
backend/
  app/
    api/            catalog, auth, admin products, guest cart, and orders
    scripts/        repeatable development seed commands
    config.py       environment configuration
    database.py     async engine and request-scoped session
    models.py       SQLAlchemy tables and database constraints
    schemas.py      Pydantic API contracts
    security.py     passwords, JWTs, and opaque-token helpers
  migrations/       four incremental Alembic migrations
  tests/            focused API, business-rule, and schema tests
frontend/
  src/
    components/     small reusable display components
    pages/          customer and administrator screens
    api.ts          shared Axios client and API functions
    auth.tsx        administrator session state
    cart.tsx        guest cart state
```

## Prerequisites

- Python 3.12 or newer
- `uv`
- Node.js 20 or newer and npm
- PostgreSQL 15 or newer
- Docker and Docker Compose are optional conveniences for the database

## Local setup

Start PostgreSQL with Docker Compose:

```bash
docker compose up -d db
```

Set up and run the backend:

```bash
cd backend
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run python -m app.scripts.seed_catalog
uv run python -m app.scripts.seed_admin
uv run uvicorn app.main:app --reload
```

Set `ADMIN_EMAIL` and `ADMIN_PASSWORD` in `backend/.env` before running the
admin seed. The catalog seed is safe to rerun: it adds missing categories and
products by name. Neither seed runs automatically during application startup.

In another terminal, run the frontend:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open:

- Customer application: `http://localhost:5173`
- Admin login: `http://localhost:5173/admin/login`
- Interactive API documentation: `http://localhost:8000/docs`

The checked-in environment examples document every setting. Development uses
separate localhost origins and non-secure cookies. Set secure cookies in an
HTTPS deployment and keep the configured frontend origin exact.

## API summary

```text
GET    /api/v1/health
GET    /api/v1/categories
GET    /api/v1/products
GET    /api/v1/products/{product_id}

POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout
GET    /api/v1/auth/me

GET    /api/v1/admin/products
POST   /api/v1/admin/products
GET    /api/v1/admin/products/{product_id}
PATCH  /api/v1/admin/products/{product_id}
DELETE /api/v1/admin/products/{product_id}
PATCH  /api/v1/admin/products/{product_id}/status
PATCH  /api/v1/admin/products/{product_id}/stock

POST   /api/v1/guest-session
GET    /api/v1/cart
POST   /api/v1/cart/items
PATCH  /api/v1/cart/items/{item_id}
DELETE /api/v1/cart/items/{item_id}

POST   /api/v1/orders/checkout
GET    /api/v1/orders/{order_id}
GET    /api/v1/admin/orders
GET    /api/v1/admin/orders/{order_id}
```

Product listing accepts `search`, `category_id`, `page`, and `page_size`.
Public routes expose only active, non-deleted products. Admin product listing
also includes inactive products but not soft-deleted rows.

## Authentication design

The access token is a short-lived signed JWT stored only in frontend memory.
The refresh credential is a random opaque token in an HttpOnly cookie, while
PostgreSQL stores only its SHA-256 digest. A successful refresh consumes the old
token and returns a replacement. Reusing a consumed token revokes the entire
refresh family.

The frontend allows only one refresh request in flight per browser tab and
retries an eligible admin request once. Logout revokes the family and clears
browser state. Already issued access JWTs remain valid until their short expiry.

## Guest ownership and cart behavior

The server establishes an anonymous guest credential in an HttpOnly cookie.
Cart routes derive the guest, cart, and item from that credential; they do not
trust customer or cart IDs supplied by the browser. The frontend sends a
separate guest CSRF value on every mutation.

Repeatedly adding one product increments its existing cart line. Cart prices
are current catalog prices and are not reserved. The server calculates all line
totals and the grand total with `Decimal`.

## Transactional checkout

Checkout receives the reviewed cart version, line quantities, and prices as
comparison data. It never trusts them as the source of inventory or money.

Inside one database transaction, the backend:

1. Locks the guest and open cart, serializing checkout against cart edits.
2. Confirms the cart version and exact contents.
3. Locks products in ascending ID order.
4. Rechecks status, deletion, stock, and reviewed prices.
5. Decrements stock and increments product versions.
6. Creates the order and immutable name/price/quantity snapshots.
7. Converts the cart and commits once.

Any failure before commit rolls back the complete unit of work. A unique cart
relationship prevents converting the same cart twice. `Idempotency-Key` plus a
request fingerprint lets a lost successful response be replayed without another
stock decrement, while rejecting reuse of the key for different input.

## Database migrations

```text
20260908_01  categories and products
20260909_02  users and rotating refresh sessions/tokens
20260910_03  guest sessions, carts, and cart items
20260911_04  orders and immutable order-item snapshots
```

Alembic is the only schema source. The application does not call
`Base.metadata.create_all()` at startup.

## Verification

```bash
cd backend
uv run ruff check .
uv run pytest
uv run alembic upgrade head --sql

cd ../frontend
npm run lint
npm run build
```

The latest automated run contains 51 passing backend tests. It covers protected
routes, refresh rotation and replay, cart ownership and CSRF, current-price
totals, checkout snapshots, stale-price rejection, idempotent replay, mismatched
idempotency use, and database constraints. Frontend lint, TypeScript compilation,
and the Vite production build also pass. The changed backend files pass Ruff;
the full Ruff run reports an existing import-order issue in `tests/test_health.py`.

Unexpected backend errors are logged with their request ID and returned as a
generic HTTP 500 response. Validation errors and intentional HTTP errors retain
FastAPI's normal, more specific responses.

Row-lock behavior should additionally be smoke-tested against a real PostgreSQL
instance using concurrent connections before production deployment. Unit mocks
and SQLite cannot prove PostgreSQL locking semantics.

## Suggested demonstration

1. Browse, search, and filter the customer catalog.
2. Sign in as the seeded administrator and create or edit a product.
3. Change stock and deactivate/reactivate the product.
4. Add products to the guest cart and update a quantity.
5. Intentionally reduce stock or change a price to show checkout conflict handling.
6. Review again and place the order.
7. Show the confirmation, empty active cart, reduced product stock, and admin order detail.
8. Retry the same checkout request to explain idempotency.

## Deliberate limitations and future enhancements

This assessment has no customer accounts, payment gateway, shipping, tax,
discounts, cancellation, or refunds. Process-local authentication throttling is
not deployment-wide. Multi-tab refresh coordination and scheduled expired-token
cleanup are deferred until the deployment requires them.

Product search intentionally uses simple parameterized substring matching. If
representative measurements show it is slow, evaluate PostgreSQL `pg_trgm` with
a GIN trigram index and compare `EXPLAIN (ANALYZE, BUFFERS)`, latency, index size,
and write cost before adopting it. The current catalog does not justify that
operational complexity.


## Catalog caching and rendering

The public product list and detail pages use TanStack Query. Product results stay
fresh for 30 seconds; categories stay fresh for 5 minutes. Query keys include the
search text, category, page, and page size, or the product ID for details. Search
is debounced by 300 ms; the public list keeps its filters in the URL so browser
Back returns to the same query. Previous results remain visible during fetching.

Successful product create/edit, stock/status changes, deletion, and checkout
invalidate public list and detail queries. Active queries refetch; inactive ones
refetch when used again. The cache lives in memory, is lost on reload, and does
not synchronize between tabs or users. Expiry makes data stale, but does not
start a polling timer: stale queries refetch on mount, window focus, or reconnect.
Checkout always validates current stock and prices on the backend.

`ProductCard` uses `memo` to skip parent-driven renders when its product prop is
unchanged. Query structural sharing preserves unchanged JSON object references.
Auth/cart actions use `useCallback`, and their context objects use `useMemo`.
Consumers still rerender when the context data they subscribe to changes. These
are targeted optimizations, not evidence of measured speedups; use the React
Profiler before adding more. See the [TanStack Query defaults documentation](https://tanstack.com/query/latest/docs/framework/react/guides/important-defaults).

Admin pages use `React.lazy` and an outlet-level `Suspense` boundary, so the shell
stays visible while their code loads. The admin list has debounced name search,
category filtering, and server pagination; inactive products remain manageable.
Its existing direct request flow is retained. Private orders and auth responses
are not placed in the product cache.

## Admin access and feedback

The footer keeps an Admin link for assessment reviewer convenience. `/admin`
remains protected and redirects to admin login when required. Moving or hiding
the link is a navigation decision, not an authorization measure. A production
deployment could restrict the admin surface through separate network/access
controls if its requirements justify that. Seed-account instructions belong in
this README, not the login UI.

Stock and status are edited only from the product table; the edit form omits
them. The create form still accepts initial values. Product saves, stock saves,
status changes, and deletion display inline success feedback.
