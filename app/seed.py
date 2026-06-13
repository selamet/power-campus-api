"""Idempotent bootstrap: ensure the admin account exists.

Run after applying migrations::

    alembic upgrade head
    python -m app.seed

The admin holds every permission implicitly; further staff and their
permissions are created from the panel's "Yetkililer" page.
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.users.models import User, UserRole
from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.core.security import hash_password


async def _ensure_admin(session: AsyncSession) -> User:
    existing = (
        await session.scalars(select(User).where(User.email == settings.seed_admin_email))
    ).first()
    if existing is not None:
        return existing
    admin = User(
        email=settings.seed_admin_email,
        password_hash=hash_password(settings.seed_admin_password),
        full_name="Sistem Yöneticisi",
        role=UserRole.admin,
        branch="Power Akademi",
    )
    session.add(admin)
    await session.commit()
    return admin


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        await _ensure_admin(session)
        print(f"Admin login: {settings.seed_admin_email} / {settings.seed_admin_password}")


if __name__ == "__main__":
    asyncio.run(seed())
