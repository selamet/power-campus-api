"""Declarative base and the audited mixin shared by every model.

Database columns are ``camelCase`` while Python attributes stay ``snake_case``;
the mapping is declared explicitly on each column.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class AuditedBase(Base):
    """Abstract base adding a primary key and audit columns to every table.

    ``createdBy`` / ``updatedBy`` are filled in automatically by the session
    audit hook (see ``app.core.db``); ``createdAt`` / ``updatedAt`` are managed
    by the database.
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True)

    created_at: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    created_by: Mapped[int | None] = mapped_column(
        "createdBy",
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        "updatedAt",
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    updated_by: Mapped[int | None] = mapped_column(
        "updatedBy",
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
