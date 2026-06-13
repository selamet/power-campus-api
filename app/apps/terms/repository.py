"""Data-access helpers for terms."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.terms.models import Term


class TermRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Term]:
        """Terms, most recent period first."""
        result = await self._session.scalars(
            select(Term).order_by(Term.start_date.desc(), Term.id.desc())
        )
        return list(result)

    async def get_by_id(self, term_id: int) -> Term | None:
        return await self._session.get(Term, term_id)

    def add(self, term: Term) -> None:
        self._session.add(term)
