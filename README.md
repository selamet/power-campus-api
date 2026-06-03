# Power Campus API

Backend API for the Power Campus academy management platform, built with
FastAPI and SQLAlchemy 2.0 (async).

## Requirements

- Python 3.13+

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Database

SQLite is used for local development (see `DATABASE_URL` in `.env`); switch to
PostgreSQL by changing that URL — no code changes required.

```bash
alembic upgrade head     # create / migrate the schema
python -m app.seed       # load staff accounts and sample students
```

## Run

```bash
uvicorn app.main:app --reload
# API:  http://localhost:8000/api/v1
# Docs: http://localhost:8000/docs
```

### Seed credentials

| Role    | Email                          | Password       |
| ------- | ------------------------------ | -------------- |
| Admin   | `admin@powerakademi.com`       | `admin1234`    |
| Manager | `elif.demir@powerakademi.com`  | `manager1234`  |

Only `admin` and `manager` accounts can sign in for now; `teacher` and
`student` are records without login.

## Endpoints (v1)

| Method | Path                          | Auth           | Description                |
| ------ | ----------------------------- | -------------- | -------------------------- |
| POST   | `/auth/login`                 | —              | Sign in, returns a token   |
| GET    | `/auth/me`                    | Bearer         | Current user               |
| GET    | `/students`                   | Bearer         | List students              |
| POST   | `/students`                   | Admin/Manager  | Create a student           |
| PATCH  | `/students/{code}/approve`    | Admin/Manager  | Approve a pending student  |
| PATCH  | `/students/{code}/reject`     | Admin/Manager  | Reject (delete) a student  |

## Connecting the frontend

Point the `power-campus-web` app at this API by setting its environment:

```bash
# power-campus-web/.env.local
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_USE_MOCKS=false
```

## Conventions

- **Database columns** use `camelCase`; **Python attributes** use `snake_case`.
- **API payloads** are `camelCase` (to match the frontend); request bodies
  accept both `camelCase` and `snake_case`.
- Every table inherits audit columns: `createdAt`, `createdBy`, `updatedAt`,
  `updatedBy`. `createdBy` / `updatedBy` are filled automatically from the
  authenticated user on every insert and update.

## Quality checks

```bash
ruff check app
mypy app
pytest
```
