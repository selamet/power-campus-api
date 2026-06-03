"""Idempotent development seed: staff accounts and sample students.

Run after applying migrations::

    alembic upgrade head
    python -m app.seed
"""

import asyncio
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.students.models import Enrollment, EnrollmentStatus, Student, StudentSource
from app.apps.users.models import User, UserRole
from app.core.config import settings
from app.core.context import current_user_id
from app.core.db import AsyncSessionLocal
from app.core.security import hash_password

MANAGER_EMAIL = "elif.demir@powerakademi.com"
MANAGER_PASSWORD = "manager1234"


def _student(
    code: str,
    name: str,
    email: str,
    phone: str,
    joined: str,
    source: StudentSource | None,
    *,
    lang: str,
    level: str,
    course: str,
    plan: str,
    status: EnrollmentStatus,
    fee: int,
    paid: int,
    start: str,
    next_payment: str | None,
) -> Student:
    return Student(
        student_code=code,
        name=name,
        email=email,
        phone=phone,
        joined_at=date.fromisoformat(joined),
        source=source,
        enrollments=[
            Enrollment(
                lang=lang,
                level=level,
                course=course,
                plan=plan,
                status=status,
                fee=fee,
                paid=paid,
                start_at=date.fromisoformat(start),
                next_payment_at=date.fromisoformat(next_payment) if next_payment else None,
            )
        ],
    )


def _sample_students() -> list[Student]:
    a, p, i = EnrollmentStatus.active, EnrollmentStatus.pending, EnrollmentStatus.inactive
    return [
        _student("PA-1042", "Zeynep Kaya", "zeynep.kaya@gmail.com", "0532 114 22 87", "2026-01-28", None, lang="İngilizce", level="B1 — Orta", course="Hafta İçi Akşam", plan="3 Taksit", status=a, fee=18500, paid=18500, start="2026-02-03", next_payment=None),
        _student("PA-1043", "Mert Yıldız", "mert.yildiz@outlook.com", "0541 308 91 04", "2026-02-01", None, lang="Almanca", level="A2 — Temel", course="Hafta Sonu Yoğun", plan="4 Taksit", status=a, fee=21000, paid=14000, start="2026-02-10", next_payment="2026-06-10"),
        _student("PA-1051", "Aylin Şahin", "aylin.sahin@gmail.com", "0505 762 33 18", "2026-05-28", StudentSource.invite, lang="İngilizce", level="C1 — İleri", course="Online Canlı", plan="Peşin", status=p, fee=24500, paid=0, start="2026-06-15", next_payment="2026-06-15"),
        _student("PA-1052", "Can Öztürk", "can.ozturk@gmail.com", "0533 901 45 76", "2026-05-29", StudentSource.invite, lang="İngilizce", level="A1 — Başlangıç", course="Hafta İçi Sabah", plan="2 Taksit", status=p, fee=16500, paid=0, start="2026-06-09", next_payment="2026-06-09"),
        _student("PA-1038", "Selin Arslan", "selin.arslan@gmail.com", "0542 667 12 90", "2026-01-15", None, lang="Fransızca", level="B2 — Orta-Üstü", course="Birebir Özel", plan="4 Taksit", status=a, fee=32000, paid=24000, start="2026-01-20", next_payment="2026-06-20"),
        _student("PA-1029", "Burak Çelik", "burak.celik@gmail.com", "0536 220 88 41", "2025-12-01", None, lang="İngilizce", level="B1 — Orta", course="Hafta İçi Akşam", plan="Peşin", status=a, fee=18500, paid=18500, start="2025-12-08", next_payment=None),
        _student("PA-1055", "Deniz Aydın", "deniz.aydin@gmail.com", "0507 145 39 22", "2026-05-30", StudentSource.manual, lang="İspanyolca", level="A1 — Başlangıç", course="Hafta Sonu Yoğun", plan="3 Taksit", status=p, fee=19500, paid=0, start="2026-06-22", next_payment="2026-06-22"),
        _student("PA-1011", "Ece Koç", "ece.koc@gmail.com", "0538 472 60 15", "2025-11-05", None, lang="İngilizce", level="C2 — Üst Düzey", course="Online Canlı", plan="4 Taksit", status=a, fee=26000, paid=19500, start="2025-11-12", next_payment="2026-06-12"),
        _student("PA-1009", "Kaan Demirtaş", "kaan.d@gmail.com", "0535 119 47 83", "2025-08-25", None, lang="Almanca", level="B1 — Orta", course="Hafta İçi Akşam", plan="Peşin", status=i, fee=17500, paid=17500, start="2025-09-01", next_payment=None),
        _student("PA-1058", "Naz Yılmaz", "naz.yilmaz@gmail.com", "0543 882 11 09", "2026-03-10", None, lang="İngilizce", level="A2 — Temel", course="Hafta İçi Sabah", plan="3 Taksit", status=a, fee=16500, paid=11000, start="2026-03-15", next_payment="2026-06-15"),
    ]


async def _ensure_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str,
    role: UserRole,
    branch: str,
) -> User:
    existing = (await session.scalars(select(User).where(User.email == email))).first()
    if existing is not None:
        return existing
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role=role,
        branch=branch,
    )
    session.add(user)
    await session.flush()
    return user


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        admin = await _ensure_user(
            session,
            email=settings.seed_admin_email,
            password=settings.seed_admin_password,
            full_name="Sistem Yöneticisi",
            role=UserRole.admin,
            branch="Power Akademi",
        )
        await _ensure_user(
            session,
            email=MANAGER_EMAIL,
            password=MANAGER_PASSWORD,
            full_name="Elif Demir",
            role=UserRole.manager,
            branch="Kadıköy Şube",
        )
        await session.commit()

        # Attribute seeded students to the admin account.
        current_user_id.set(admin.id)

        student_count = await session.scalar(select(func.count()).select_from(Student))
        if not student_count:
            session.add_all(_sample_students())
            await session.commit()
            print(f"Seeded {len(_sample_students())} students.")
        else:
            print(f"Students already present ({student_count}); skipped.")

        print(f"Admin login: {settings.seed_admin_email} / {settings.seed_admin_password}")
        print(f"Manager login: {MANAGER_EMAIL} / {MANAGER_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
