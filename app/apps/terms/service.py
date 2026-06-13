"""Term management use cases."""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.terms.models import Term
from app.apps.terms.naming import playful_name
from app.apps.terms.repository import TermRepository
from app.apps.terms.schemas import CreateTermRequest, TermOut, TermUpdate


class TermNotFoundError(Exception):
    """Raised when no term matches the given id."""


class InvalidTermDatesError(Exception):
    """Raised when a term would end before it starts."""

    message = "Dönem bitiş tarihi başlangıçtan önce olamaz."


class TermService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TermRepository(session)

    async def list_terms(self) -> list[TermOut]:
        today = date.today()
        return [TermOut.from_model(term, today=today) for term in await self._repo.list_all()]

    async def create_term(self, payload: CreateTermRequest) -> TermOut:
        if payload.end < payload.start:
            raise InvalidTermDatesError
        name = (payload.name or "").strip() or playful_name(payload.start.year)
        term = Term(name=name, start_date=payload.start, end_date=payload.end)
        self._repo.add(term)
        await self._session.commit()
        return TermOut.from_model(term, today=date.today())

    async def update_term(self, term_id: int, payload: TermUpdate) -> TermOut:
        term = await self._repo.get_by_id(term_id)
        if term is None:
            raise TermNotFoundError(term_id)
        data = payload.model_dump(exclude_unset=True)
        name = data.get("name")
        if name is not None and name.strip():
            term.name = name.strip()
        if data.get("start") is not None:
            term.start_date = data["start"]
        if data.get("end") is not None:
            term.end_date = data["end"]
        if term.end_date < term.start_date:
            raise InvalidTermDatesError
        await self._session.commit()
        return TermOut.from_model(term, today=date.today())
