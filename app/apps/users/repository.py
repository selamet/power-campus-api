"""Data-access helpers for user accounts."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.users.models import User, UserRole


class UserRepository:
    """Read access to the ``users`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: int) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.scalars(select(User).where(User.email == email))
        return result.first()

    async def list_staff(self) -> list[User]:
        """Every account that can be managed from the panel (non-students)."""
        result = await self._session.scalars(
            select(User).where(User.role != UserRole.student).order_by(User.full_name)
        )
        return list(result)
