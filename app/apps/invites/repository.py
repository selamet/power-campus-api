"""Data-access helpers for invites."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.invites.models import Invite


class InviteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_tckn(self, tckn: str) -> Invite | None:
        result = await self._session.scalars(select(Invite).where(Invite.tckn == tckn))
        return result.first()

    def add(self, invite: Invite) -> None:
        self._session.add(invite)
