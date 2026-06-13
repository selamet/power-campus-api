"""Term (semester) model: a dated period a student enrolls into."""

from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import AuditedBase


class Term(AuditedBase):
    """A teaching period courses run in (e.g. a semester).

    ``name`` is always stored: when staff leave it blank a playful one is
    generated at creation, so the UI has a stable label to show.
    """

    __tablename__ = "terms"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    start_date: Mapped[date] = mapped_column("startDate", Date, nullable=False)
    end_date: Mapped[date] = mapped_column("endDate", Date, nullable=False)
