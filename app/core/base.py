"""Declarative base and the audited mixin shared by every model.

Database columns are ``camelCase`` while Python attributes stay ``snake_case``;
the mapping is declared explicitly on each column.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Deterministic names for indexes and constraints so Alembic autogenerate and
# migrations stay portable (Postgres names anonymous constraints itself, which
# makes later ALTER/DROP brittle). See SQLAlchemy "Configuring Constraint
# Naming Conventions".
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


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
