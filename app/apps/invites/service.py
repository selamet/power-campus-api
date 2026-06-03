"""Invite and self-service registration use cases."""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.invites.models import Invite, InviteStatus
from app.apps.invites.repository import InviteRepository
from app.apps.invites.schemas import CreateInviteRequest, WelcomeSubmitRequest
from app.apps.students.models import Enrollment, EnrollmentStatus, Student, StudentSource
from app.apps.students.repository import StudentRepository

# Level, plan and fee are agreed with the student later, during approval.
_DEFAULT_LEVEL = "Belirlenecek"
_DEFAULT_PLAN = "Belirlenecek"


class InviteNotFoundError(Exception):
    """Raised when no invite matches the given TCKN."""


class InviteAlreadyCompletedError(Exception):
    """Raised when a welcome form is submitted for an already-used invite."""


class InviteService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._invites = InviteRepository(session)
        self._students = StudentRepository(session)

    async def create_invite(self, payload: CreateInviteRequest) -> Invite:
        """Create a new invite, or refresh an existing one for the same TCKN."""
        invite = await self._invites.get_by_tckn(payload.tckn)
        if invite is None:
            invite = Invite(tckn=payload.tckn)
            self._invites.add(invite)
        invite.phone = payload.phone
        invite.name = payload.name
        invite.lang = payload.lang
        invite.course = payload.course
        invite.status = InviteStatus.pending
        invite.student_id = None
        await self._session.commit()
        await self._session.refresh(invite)
        return invite

    async def get_invite(self, tckn: str) -> Invite:
        invite = await self._invites.get_by_tckn(tckn)
        if invite is None:
            raise InviteNotFoundError(tckn)
        return invite

    async def submit_welcome(self, tckn: str, payload: WelcomeSubmitRequest) -> Student:
        """Convert a submitted welcome form into a pending student record."""
        invite = await self.get_invite(tckn)
        if invite.status is InviteStatus.completed:
            raise InviteAlreadyCompletedError(tckn)

        student = Student(
            student_code=await self._students.next_student_code(),
            name=payload.name,
            email=payload.email,
            phone=payload.phone,
            joined_at=date.today(),
            source=StudentSource.invite,
            tckn=tckn,
            birth_date=payload.birth_date,
            gender=payload.gender,
            city=payload.city,
            address=payload.address,
            education_level=payload.education_level,
            school=payload.school,
            department=payload.department,
            grade=payload.grade,
            contact_name=payload.contact_name,
            contact_relation=payload.contact_relation,
            contact_phone=payload.contact_phone,
        )
        student.enrollments.append(
            Enrollment(
                lang=invite.lang,
                level=_DEFAULT_LEVEL,
                course=invite.course,
                plan=_DEFAULT_PLAN,
                status=EnrollmentStatus.pending,
                fee=0,
                paid=0,
                start_at=date.today(),
            )
        )
        self._students.add(student)
        await self._session.flush()

        invite.status = InviteStatus.completed
        invite.student_id = student.id
        await self._session.commit()
        # No refresh: expire_on_commit is off, so the in-memory student (with its
        # enrollment) stays usable; refreshing would expire the loaded collection.
        return student
