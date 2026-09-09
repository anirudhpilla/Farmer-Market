# Farmer Market

Farmer Market is the React + FastAPI shopping-cart assessment described in
`Farmer-Products-Final-Project-Outline.md`.

The project is being implemented in explainable vertical slices. The current
iteration provides the public product catalog and admin authentication with
rotating refresh tokens, plus protected product creation, editing, activation,
stock updates, and soft deletion.

## Repository layout

```text
backend/   FastAPI application, SQLAlchemy models, and Alembic migrations
frontend/  React and TypeScript application
```

Detailed setup instructions will grow with the implementation. For now, copy
the environment examples, start PostgreSQL, install dependencies, run the
migration, and start both applications.

## Run the current iteration

Prerequisites: Python 3.12+, `uv`, Node.js 20+, npm, Docker, and Docker Compose.

```bash
docker compose up -d db

cd backend
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run python -m app.scripts.seed_catalog
uv run python -m app.scripts.seed_admin
uv run uvicorn app.main:app --reload
```

In a second terminal:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open `http://localhost:5173` to browse the catalog. FastAPI documentation is at
`http://localhost:8000/docs`.

The seed command is safe to rerun: it creates missing categories and products
whose names are not already present. It is development/demo setup, not an
application-startup responsibility.

## Current API

```text
GET /api/v1/health
GET /api/v1/categories
GET /api/v1/products
GET /api/v1/products/{product_id}
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
GET /api/v1/auth/me
GET /api/v1/admin/products
POST /api/v1/admin/products
GET /api/v1/admin/products/{product_id}
PATCH /api/v1/admin/products/{product_id}
DELETE /api/v1/admin/products/{product_id}
PATCH /api/v1/admin/products/{product_id}/status
PATCH /api/v1/admin/products/{product_id}/stock
```

The product list accepts `search`, `category_id`, `page`, and `page_size` query
parameters. Customer endpoints return only active, non-deleted products.

The login page is at `http://localhost:5173/admin/login`. Set `ADMIN_EMAIL`
and `ADMIN_PASSWORD` in `backend/.env` before running the admin seed command.
The access token remains in frontend memory. The opaque refresh token is stored
in an HttpOnly cookie, while only its SHA-256 digest is stored in PostgreSQL.
Each refresh consumes the old token and creates a replacement; presenting a
consumed token revokes that refresh family.

After signing in, open `http://localhost:5173/admin`. Product edits intentionally
exclude stock and status: those have explicit controls in the admin list. Stock
updates send the product version last read by the browser; stale versions return
409 instead of overwriting a newer inventory value. Delete is a soft delete, so
the row remains available for future order-history relationships.

Examples:

```text
GET /api/v1/products?search=tomato
GET /api/v1/products?category_id=2&page=1&page_size=6
```

## Checks

```bash
cd backend
uv run ruff check .
uv run pytest

cd ../frontend
npm run lint
npm run build
```

The first migration contains the catalog tables and the second adds
authentication. Admin product management reuses the existing product columns,
so it does not invent an empty migration. Cart and order tables will be added
when those features are implemented. Do not use `Base.metadata.create_all()` in
application startup: Alembic is the versioned, reviewable source of database
changes.
