"""Append-only helper for recording events on a student's activity log.

Kept in its own module (not ``service.py``) so the payments service can import
it without a circular dependency.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.students.models import ActivityKind, Student, StudentActivity


def log_activity(
    session: AsyncSession,
    student: Student,
    kind: ActivityKind,
    message: str,
    meta: dict[str, Any] | None = None,
) -> None:
    """Append an activity row inside the caller's transaction.

    ``createdBy`` (the actor) is stamped by the session audit hook on flush;
    the row is persisted when the caller commits. The student must already have
    an id (i.e. be flushed) so ``student.id`` is available.
    """
    session.add(
        StudentActivity(student_id=student.id, kind=kind, message=message, meta=meta)
    )
