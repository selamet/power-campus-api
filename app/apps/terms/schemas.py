"""Term API schemas."""

from datetime import date

from app.apps.terms.models import Term
from app.core.schemas import CamelModel


class TermOut(CamelModel):
    """A term as returned to the frontend."""

    id: int
    name: str
    start: date
    end: date
    # Whether today falls inside the term's date range.
    current: bool

    @classmethod
    def from_model(cls, term: Term, *, today: date) -> "TermOut":
        return cls(
            id=term.id,
            name=term.name,
            start=term.start_date,
            end=term.end_date,
            current=term.start_date <= today <= term.end_date,
        )


class CreateTermRequest(CamelModel):
    """Payload for creating a term; a blank name is auto-generated."""

    name: str | None = None
    start: date
    end: date


class TermUpdate(CamelModel):
    """Partial update of a term."""

    name: str | None = None
    start: date | None = None
    end: date | None = None
