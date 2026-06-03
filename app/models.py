"""Single import surface for all ORM models.

Importing this module ensures every model is registered on ``Base.metadata``,
which Alembic autogenerate and the seed script rely on.
"""

from app.apps.invites.models import Invite
from app.apps.students.models import Enrollment, Student
from app.apps.users.models import User
from app.core.base import Base

__all__ = ["Base", "Enrollment", "Invite", "Student", "User"]
