# Farmer Market

Farmer Market is the React + FastAPI shopping-cart assessment described in
`Farmer-Products-Final-Project-Outline.md`.

The project is being implemented in explainable vertical slices. The current
iteration provides the application skeleton, database models and first
migration, a database-backed health endpoint, and the public product catalog.

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

## Current public API

```text
GET /api/v1/health
GET /api/v1/categories
GET /api/v1/products
GET /api/v1/products/{product_id}
```

The product list accepts `search`, `category_id`, `page`, and `page_size` query
parameters. Customer endpoints return only active, non-deleted products.

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

The first migration contains only the catalog tables used in this iteration.
Authentication, cart, and order tables will be added by the migrations that
introduce those features. This keeps each database change small and easy to
explain. Do not use `Base.metadata.create_all()` in application startup:
Alembic is the versioned, reviewable source of database changes.
