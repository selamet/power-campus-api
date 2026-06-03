"""Async database engine, session factory and the audit flush hook."""

from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from app.core.base import AuditedBase
from app.core.config import settings
from app.core.context import current_user_id

engine = create_async_engine(settings.database_url, echo=settings.debug, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)


@event.listens_for(Session, "before_flush")
def _apply_audit_columns(session: Session, flush_context: object, instances: object) -> None:
    """Stamp ``createdBy`` / ``updatedBy`` from the request's current user.

    Runs on the underlying sync session that ``AsyncSession`` drives, so it
    covers every insert and update regardless of which service triggered it.
    """
    user_id = current_user_id.get()
    for obj in session.new:
        if isinstance(obj, AuditedBase):
            if obj.created_by is None:
                obj.created_by = user_id
            obj.updated_by = user_id
    for obj in session.dirty:
        if isinstance(obj, AuditedBase) and session.is_modified(obj):
            obj.updated_by = user_id


async def get_session() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency yielding a database session per request."""
    async with AsyncSessionLocal() as session:
        yield session
