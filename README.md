# Power Campus API

Backend API for the Power Campus academy management platform, built with
FastAPI and SQLAlchemy 2.0.

## Requirements

- Python 3.13+

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Conventions

- **Database columns** use `camelCase`; **Python attributes** use `snake_case`.
- **API payloads** are `camelCase` (to match the frontend); request bodies
  accept both `camelCase` and `snake_case`.
- Every table inherits audit columns: `createdAt`, `createdBy`, `updatedAt`,
  `updatedBy`.

More setup and run instructions are added as the project grows.
