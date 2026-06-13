"""Reset the development database and fill it with demo data for manual testing.

DESTRUCTIVE — this drops every table, recreates the schema from the models, then
inserts an admin, three staff accounts and 100 students (each with an enrollment,
finance and payment history) spread across a few terms. Local/dev use only::

    python -m app.seed_demo

It never runs on import; the wipe only happens when invoked as a script.
"""

import asyncio
import random
from datetime import date, timedelta

import app.models  # noqa: F401  -- registers every model on Base.metadata
from app.apps.payments.models import Payment
from app.apps.payments.service import PaymentService
from app.apps.students.models import Enrollment, EnrollmentStatus, Student, StudentSource
from app.apps.students.repository import provisional_code
from app.apps.terms.models import Term
from app.apps.users.models import User, UserPermission, UserRole
from app.apps.users.permissions import Permission
from app.core.base import Base
from app.core.config import settings
from app.core.db import AsyncSessionLocal, engine
from app.core.security import hash_password

_CODE_OFFSET = 1059  # mirrors StudentRepository: student id=1 -> PA-1060

FIRST_NAMES = (
    "Ahmet", "Mehmet", "Mustafa", "Ali", "Hüseyin", "Hasan", "İbrahim", "Emre",
    "Burak", "Can", "Deniz", "Kaan", "Yusuf", "Berk", "Ozan", "Selim",
    "Zeynep", "Elif", "Ayşe", "Fatma", "Merve", "Buse", "Ece", "İrem",
    "Selin", "Derya", "Aslı", "Gizem", "Esra", "Büşra", "Nur", "Sena",
)
LAST_NAMES = (
    "Yılmaz", "Kaya", "Demir", "Şahin", "Çelik", "Yıldız", "Yıldırım", "Öztürk",
    "Aydın", "Özdemir", "Arslan", "Doğan", "Kılıç", "Aslan", "Çetin", "Kara",
    "Koç", "Kurt", "Özkan", "Şimşek", "Polat", "Korkmaz", "Erdoğan", "Aksoy",
)
CITIES = (
    "İstanbul", "Ankara", "İzmir", "Bursa", "Antalya", "Adana", "Konya",
    "Gaziantep", "Kayseri", "Eskişehir", "Trabzon", "Samsun",
)
LANGUAGES = ("İngilizce", "İngilizce", "İngilizce", "Almanca", "Fransızca", "İspanyolca", "Rusça")
LEVELS = (
    "A1 — Başlangıç", "A2 — Temel", "B1 — Orta",
    "B2 — Orta-Üstü", "C1 — İleri", "C2 — Üst Düzey",
)
COURSES = ("Hafta İçi Sabah", "Hafta İçi Akşam", "Hafta Sonu Yoğun", "Birebir Özel", "Online Canlı")
PLANS = ("Peşin", "2 Taksit", "3 Taksit", "4 Taksit", "6 Taksit", "9 Taksit", "12 Taksit")
PAY_METHODS = ("Kredi Kartı", "Banka Havalesi / EFT", "Nakit")
GENDERS = ("Kadın", "Erkek")

# (email, full name, role, password, permissions) for the three staff accounts.
STAFF = (
    (
        "ofis@powerakademi.com",
        "Office Manager",
        "ofis1234",
        [
            Permission.dashboard_read, Permission.students_read, Permission.students_write,
            Permission.finance_read, Permission.finance_write, Permission.invites_write,
            Permission.terms_read, Permission.terms_write, Permission.users_read,
        ],
    ),
    (
        "kayit@powerakademi.com",
        "Registration Officer",
        "kayit1234",
        [
            Permission.dashboard_read, Permission.students_read, Permission.students_write,
            Permission.invites_write, Permission.terms_read,
        ],
    ),
    (
        "muhasebe@powerakademi.com",
        "Accountant",
        "muhasebe1234",
        [
            Permission.dashboard_read, Permission.students_read,
            Permission.finance_read, Permission.finance_write,
        ],
    ),
)

_SLUG = str.maketrans("çğıİöşüÇĞÖŞÜ", "cgiiosuCGOSU")


def _slug(value: str) -> str:
    return value.translate(_SLUG).replace(" ", "").lower()


def _phone() -> str:
    raw = f"05{random.randint(300000000, 599999999)}"
    return f"{raw[:4]} {raw[4:7]} {raw[7:9]} {raw[9:11]}"


async def _reset_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


def _build_terms(today: date) -> list[Term]:
    return [
        Term(
            name="2025 Bahar",
            start_date=today - timedelta(days=240),
            end_date=today - timedelta(days=90),
        ),
        Term(
            name="2026 Güz",
            start_date=today - timedelta(days=20),
            end_date=today + timedelta(days=110),
        ),
        Term(
            name="2026 Bahar",
            start_date=today + timedelta(days=120),
            end_date=today + timedelta(days=260),
        ),
    ]


def _build_student(index: int, today: date) -> Student:
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    joined = today - timedelta(days=random.randint(10, 700))
    status = random.choices(
        [EnrollmentStatus.active, EnrollmentStatus.pending, EnrollmentStatus.inactive],
        weights=[70, 20, 10],
    )[0]
    fee = random.randint(8, 36) * 500  # 4.000 – 18.000 ₺
    if status is EnrollmentStatus.pending:
        paid = 0
    elif status is EnrollmentStatus.inactive:
        paid = random.choice([0, fee // 4, fee // 2])
    else:
        paid = random.choice([fee, fee, fee // 2, fee // 3, max(fee - 1500, 0), 0])
    paid = max(0, min(paid, fee))

    student = Student(
        student_code=provisional_code(),
        name=f"{first} {last}",
        email=f"{_slug(first)}.{_slug(last)}{index}@ornek.com",
        phone=_phone(),
        joined_at=joined,
        source=random.choice([StudentSource.manual, StudentSource.invite]),
        city=random.choice(CITIES),
        gender=random.choice(GENDERS),
        birth_date=date(random.randint(1985, 2007), random.randint(1, 12), random.randint(1, 28)),
    )
    student.enrollments.append(
        Enrollment(
            lang=random.choice(LANGUAGES),
            level=random.choice(LEVELS),
            course=random.choice(COURSES),
            plan=random.choice(PLANS),
            status=status,
            fee=fee,
            paid=paid,
            start_at=joined,
            terms=random.randint(1, 4),
        )
    )
    return student


async def seed_demo() -> None:
    random.seed(42)
    await _reset_schema()
    today = date.today()

    async with AsyncSessionLocal() as session:
        # Admin + three scoped staff accounts.
        session.add(
            User(
                email=settings.seed_admin_email,
                password_hash=hash_password(settings.seed_admin_password),
                full_name="Sistem Yöneticisi",
                role=UserRole.admin,
                branch="Power Akademi",
            )
        )
        for email, name, _password, permissions in STAFF:
            session.add(
                User(
                    email=email,
                    password_hash=hash_password(_password),
                    full_name=name,
                    role=UserRole.manager,
                    branch="Power Akademi",
                    permissions=[UserPermission(permission=p.value) for p in permissions],
                )
            )

        # Terms.
        terms = _build_terms(today)
        session.add_all(terms)

        # 100 students, each with one enrollment.
        students = [_build_student(index, today) for index in range(100)]
        session.add_all(students)
        await session.flush()  # assign ids to students, enrollments and terms

        # Public codes derived from the autoincrement id (race-free, like the app).
        for student in students:
            student.student_code = f"PA-{_CODE_OFFSET + student.id}"

        # Finance: opening payment for collected amounts, then an installment
        # schedule for the remaining balance. Spread enrollments across terms so
        # the term rosters have data to show.
        payments = PaymentService(session)
        past_term, current_term, _future = terms
        for student in students:
            enrollment = student.enrollments[-1]
            if enrollment.paid > 0:
                session.add(
                    Payment(
                        enrollment_id=enrollment.id,
                        amount=enrollment.paid,
                        paid_at=enrollment.start_at + timedelta(days=2),
                        method=random.choice(PAY_METHODS),
                        note="Açılış tahsilatı",
                    )
                )
            payments.generate_schedule(enrollment)
            # ~55% land in the current term, ~20% in the past term, rest unassigned.
            roll = random.random()
            if roll < 0.55:
                enrollment.term_id = current_term.id
            elif roll < 0.75:
                enrollment.term_id = past_term.id

        await session.commit()

    print("Database reset and seeded.")
    print(f"  Admin    : {settings.seed_admin_email} / {settings.seed_admin_password}")
    for email, name, password, _permissions in STAFF:
        print(f"  Staff    : {email} / {password}  ({name})")
    print("  Students : 100")
    print("  Terms    : 2025 Bahar, 2026 Güz (current), 2026 Bahar")


if __name__ == "__main__":
    asyncio.run(seed_demo())
