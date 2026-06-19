"""Single import surface for all ORM models.

Importing this module ensures every model is registered on ``Base.metadata``,
which Alembic autogenerate and the seed script rely on.
"""

from app.apps.classes.models import ClassLesson, SchoolClass
from app.apps.invites.models import Invite
from app.apps.payments.models import Installment, Payment
from app.apps.schedule.models import (
    ScheduleConfig,
    ScheduleRuleTemplate,
    ScheduleSession,
    TermScheduleSettings,
)
from app.apps.students.models import Enrollment, Student, StudentActivity
from app.apps.teachers.models import Teacher
from app.apps.terms.models import Term
from app.apps.users.models import User
from app.core.base import Base

__all__ = [
    "Base",
    "ClassLesson",
    "Enrollment",
    "Installment",
    "Invite",
    "Payment",
    "ScheduleConfig",
    "ScheduleRuleTemplate",
    "ScheduleSession",
    "SchoolClass",
    "Student",
    "StudentActivity",
    "Teacher",
    "Term",
    "TermScheduleSettings",
    "User",
]
