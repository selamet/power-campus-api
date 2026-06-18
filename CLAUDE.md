# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Backend API for the Power Campus academy management platform: FastAPI + SQLAlchemy 2.0 (async), Python 3.13+. SQLite for local dev, PostgreSQL in production (switch via `DATABASE_URL` only — no code changes). The frontend lives in the sibling repo `power-campus-web`.

## Commands

```bash
# Setup (once)
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env

# Database
alembic upgrade head            # create / migrate schema
alembic revision --autogenerate -m "message"   # new migration (see note below)
python -m app.seed              # idempotent: ensure admin account exists

# Run
uvicorn app.main:app --reload   # API at /api/v1, docs at /docs

# Quality checks (run all three before considering work done)
ruff check app
mypy app                        # strict mode
pytest
pytest tests/test_terms.py                          # single file
pytest tests/test_terms.py::test_name -x            # single test, stop on first failure
```

## Architecture

### Module layout (`app/apps/<module>/`)
Each domain (`auth`, `users`, `students`, `terms`, `classes`, `teachers`, `invites`, `payments`, `dashboard`) is a self-contained vertical slice with a consistent layering:

- **`router.py`** — FastAPI endpoints. Thin: declares permission deps, calls the service, translates the service's domain exceptions into `HTTPException`. No business logic.
- **`service.py`** — business logic, transaction boundaries, raises typed domain errors (e.g. `TermNotFoundError`, `InvalidTermDatesError`).
- **`repository.py`** — data-access only (SQLAlchemy `select`/`get`/`add`). No business rules.
- **`models.py`** — ORM models for that domain.
- **`schemas.py`** — Pydantic request/response models.

Routers are wired in `app/main.py` (`create_app`), all under `settings.api_v1_prefix` (`/api/v1`).

### Cross-cutting conventions
- **camelCase vs snake_case**: DB columns are `camelCase`, Python attributes are `snake_case` — the mapping is declared explicitly on each `mapped_column` (e.g. `mapped_column("createdAt", ...)`). API payloads serialize to `camelCase` and accept both casings on input. All schemas extend `CamelModel` (`app/core/schemas.py`); all models extend `AuditedBase` (`app/core/base.py`).
- **Audit columns are automatic**: every table gets `createdAt`/`createdBy`/`updatedAt`/`updatedBy` from `AuditedBase`. `createdBy`/`updatedBy` are filled by a SQLAlchemy `before_flush` hook in `app/core/db.py` that reads the acting user from a `ContextVar` (`app/core/context.py`). The auth dependency sets that ContextVar — **do not thread the user id through service calls** for audit purposes.
- **Constraint naming**: `Base.metadata` uses an explicit `NAMING_CONVENTION` (`app/core/base.py`) so Alembic-generated migrations stay portable across SQLite/Postgres. Don't rely on anonymous constraint names.
- **Error responses**: HTTP errors are reshaped to `{"message": ...}` and validation errors to `{"message": ..., "errors": [...]}` by exception handlers in `main.py`, to match the frontend client. User-facing messages are in Turkish.

### Authorization
Two dependency factories in `app/core/deps.py`:
- `require_roles(*roles)` — role gate (`admin`, `manager`, `teacher`, `student`).
- `require_permission(*perms)` — fine-grained `module:action` gate; `admin` implicitly holds all permissions. Also enforces forced first-login password reset (blocks every protected route until the user changes their password).

Permissions are an enum + UI catalog in `app/apps/users/permissions.py` (single source of truth). Routers declare reusable annotated deps, e.g. `CanWrite = Annotated[User, Depends(require_permission(Permission.terms_write))]`. Note a permission can cross modules (enrolling students into a term requires `students:write`, not `terms:write`).

Auth is JWT bearer. Tokens issued before `password_changed_at` are rejected, so a password reset invalidates old sessions. Only `admin`/`manager` accounts can sign in; `teacher`/`student` are records without login.

### Models registration
`app/models.py` re-imports every ORM model so they register on `Base.metadata`. Alembic autogenerate (`alembic/env.py`), the seed script, and the test schema builder all depend on importing it — **add new models to `app/models.py`**.

## Testing
`tests/conftest.py` gives each test an isolated throwaway SQLite DB (schema built from ORM metadata, not migrations) and an `AsyncClient` with `get_session` overridden. Key fixtures: `make_user` (inserts a user directly, bypassing the API), `admin`, `login` (returns bearer headers), `client`. `asyncio_mode = "auto"`, so async tests need no decorator.

## Conventions when adding a domain module
Mirror an existing slice (`terms` is the smallest complete example): create `router/service/repository/models/schemas.py`, register the model in `app/models.py`, add a `Permission` entry + catalog group in `app/apps/users/permissions.py`, include the router in `app/main.py`, and generate an Alembic migration.
