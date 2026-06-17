# Student Activity Log Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give each student a persisted, chronological activity log (created / approved / enrolled / payment events), written automatically by the service layer and shown read-only on the student detail page.

**Architecture:** A new `student_activities` table (one row per event) extending `AuditedBase`, so the acting user is captured automatically via the existing `createdBy` audit hook. A tiny `log_activity()` helper appends rows inside the caller's existing transaction; existing service flows call it. A single `GET /students/{code}/activity` endpoint returns the feed newest-first. The web detail page loads it and renders a read-only timeline.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 (async) + Alembic + pytest (api); Vite + React 18 + Redux Toolkit + TypeScript (web).

## Global Constraints

- **Two repos:** api = `/Users/selametsamli/projects/power-campus-api`, web = `/Users/selametsamli/projects/power-campus-web`. Commit each repo on its own feature branch.
- **Branch (api):** `feat/student-activity-log` (already created; the spec commit lives here).
- **DB column naming:** columns are `camelCase`, Python attributes `snake_case`, mapped explicitly per column.
- **Enum columns:** use the project pattern — `Enum(MyEnum, name="...", native_enum=False, values_callable=lambda c: [m.value for m in c])`.
- **Money:** whole Turkish Lira, integer, no sub-units.
- **Persisted user-facing strings are Turkish** (matching existing rows like `"Açılış tahsilatı"`). Activity `message` values are Turkish.
- **Permissions:** read = `Permission.students_read`, write = `Permission.students_write`. No new permission is added.
- **Commits:** English, conventional-commit style, **no Claude attribution / no Co-Authored-By line**, staged per task.
- **api tests:** pytest integration tests via `httpx.AsyncClient`; the test schema is built from ORM metadata (`Base.metadata.create_all`), so new tables appear in tests without running the migration. Run from the api repo root: `pytest tests/test_activity.py -v`.
- **web has no test runner.** Verify web tasks with `npm run lint` and `npm run typecheck` from the web repo root.
- **`reject` is intentionally NOT logged:** `reject_student` hard-deletes the student and cascade-deletes its activities, so a `rejected` event would be dead data.

---

### Task 1: Activity model, helper, read endpoint, and `created` event (api)

This is the first testable vertical slice: a model + migration + schema + repository + helper + endpoint, wired so that **creating a student** produces one activity row retrievable via the new endpoint.

**Files:**
- Modify: `app/apps/students/models.py` (add `ActivityKind`, `StudentActivity`, `Student.activities`)
- Create: `alembic/versions/d9c2b7e34a15_add_student_activities.py`
- Create: `app/apps/students/activity.py` (the `log_activity` helper)
- Modify: `app/apps/students/schemas.py` (add `ActivityOut`)
- Modify: `app/apps/students/repository.py` (add `list_activities`)
- Modify: `app/apps/students/service.py` (add `list_activities`; log on `create_student`)
- Modify: `app/apps/students/router.py` (add `GET /{code}/activity`)
- Test: `tests/test_activity.py`

**Interfaces:**
- Produces:
  - `ActivityKind` (`enum.StrEnum`) with members `created`, `approved`, `enrolled`, `payment_recorded`, `status_changed`, `note_added`. (The last two are reserved for later sub-projects; not emitted here.)
  - `StudentActivity` model with `student_id: int`, `kind: ActivityKind`, `message: str`, `meta: dict | None`, inherited `created_at`, `created_by`, and an `actor` relationship (`User | None`).
  - `log_activity(session: AsyncSession, student: Student, kind: ActivityKind, message: str, meta: dict | None = None) -> None`
  - `StudentRepository.list_activities(student_id: int) -> list[StudentActivity]` (newest first, `actor` eager-loaded)
  - `StudentService.list_activities(code: str) -> list[ActivityOut]`
  - `ActivityOut(CamelModel)`: `id: int`, `kind: ActivityKind`, `message: str`, `meta: dict | None`, `actor_name: str | None`, `created_at: datetime` → serialized as `actorName`, `createdAt`.
  - `GET /students/{code}/activity` → `list[ActivityOut]`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_activity.py`:

```python
"""Integration tests for the per-student activity log."""

from collections.abc import Awaitable, Callable

from app.apps.users.models import UserRole
from httpx import AsyncClient

from .conftest import API, Headers

Login = Callable[[str, str], Awaitable[Headers]]


def _student_payload(email: str, *, status: str = "active", fee: int = 10_000) -> dict:
    return {
        "name": "Test Öğrenci",
        "lang": "İngilizce",
        "level": "A1 — Başlangıç",
        "course": "Online Canlı",
        "status": status,
        "phone": "0500 000 00 00",
        "start": "2026-02-01",
        "fee": fee,
        "plan": "Peşin",
        "joined": "2026-01-01",
        "email": email,
    }


async def test_create_student_logs_activity(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    created = await client.post(
        f"{API}/students", headers=headers, json=_student_payload("act1@test.com")
    )
    code = created.json()["id"]

    res = await client.get(f"{API}/students/{code}/activity", headers=headers)
    assert res.status_code == 200
    rows = res.json()
    assert len(rows) == 1
    assert rows[0]["kind"] == "created"
    assert rows[0]["actorName"] == "Test User"
    assert rows[0]["message"]


async def test_activity_requires_read_permission(
    client: AsyncClient, make_user: Callable[..., Awaitable[None]], login: Login
) -> None:
    await make_user(email="noperm@test.com", password="pw12345678", role=UserRole.staff)
    headers = await login("noperm@test.com", "pw12345678")
    res = await client.get(f"{API}/students/PA-9999/activity", headers=headers)
    assert res.status_code == 403
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_activity.py -v`
Expected: FAIL — `GET …/activity` returns 404 (route not defined) / 405, so assertions fail.

- [ ] **Step 3: Add the model, enum, and relationship**

In `app/apps/students/models.py`:

Add `JSON` to the sqlalchemy import line:
```python
from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, Integer, String
```

Add the enum after `EnrollmentStatus`:
```python
class ActivityKind(enum.StrEnum):
    """A recorded event on a student's activity log."""

    created = "created"
    approved = "approved"
    enrolled = "enrolled"
    payment_recorded = "payment_recorded"
    # Reserved for later CRM sub-projects; defined now, emitted there.
    status_changed = "status_changed"
    note_added = "note_added"
```

Add the `activities` relationship to `Student` (next to `enrollments`):
```python
    activities: Mapped[list["StudentActivity"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
        order_by="StudentActivity.id",
    )
```

Add the model at the end of the file:
```python
class StudentActivity(AuditedBase):
    """One recorded event on a student's timeline (created, approved, ...).

    Immutable: rows are appended by the service layer as events occur. The
    acting user is captured automatically via ``createdBy`` (the audit hook),
    so no separate actor column is needed.
    """

    __tablename__ = "student_activities"

    student_id: Mapped[int] = mapped_column(
        "studentId",
        ForeignKey("students.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    kind: Mapped[ActivityKind] = mapped_column(
        Enum(
            ActivityKind,
            name="activityKind",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    # Optional structured detail, e.g. {"amount": 500} for a payment event.
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # The acting user, resolved through the inherited ``createdBy`` FK.
    actor: Mapped["User | None"] = relationship(
        "User", lazy="selectin", foreign_keys="StudentActivity.created_by"
    )
    student: Mapped["Student"] = relationship(back_populates="activities")
```

- [ ] **Step 4: Add the Alembic migration**

Create `alembic/versions/d9c2b7e34a15_add_student_activities.py`:
```python
"""add student activities

Revision ID: d9c2b7e34a15
Revises: b8d4f1a6027c
Create Date: 2026-06-18 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d9c2b7e34a15"
down_revision: Union[str, Sequence[str], None] = "b8d4f1a6027c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "student_activities",
        sa.Column("studentId", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("message", sa.String(length=255), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "createdAt",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("createdBy", sa.Integer(), nullable=True),
        sa.Column(
            "updatedAt",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("updatedBy", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["studentId"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["createdBy"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updatedBy"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("student_activities", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_student_activities_studentId"), ["studentId"], unique=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("student_activities", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_student_activities_studentId"))
    op.drop_table("student_activities")
```

- [ ] **Step 5: Add the `log_activity` helper**

Create `app/apps/students/activity.py`:
```python
"""Append-only helper for recording events on a student's activity log.

Kept in its own module (not ``service.py``) so the payments service can import
it without a circular dependency.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.students.models import ActivityKind, Student, StudentActivity


def log_activity(
    session: AsyncSession,
    student: Student,
    kind: ActivityKind,
    message: str,
    meta: dict | None = None,
) -> None:
    """Append an activity row inside the caller's transaction.

    ``createdBy`` (the actor) is stamped by the session audit hook on flush;
    the row is persisted when the caller commits. The student must already have
    an id (i.e. be flushed) so ``student.id`` is available.
    """
    session.add(
        StudentActivity(student_id=student.id, kind=kind, message=message, meta=meta)
    )
```

- [ ] **Step 6: Add the `ActivityOut` schema**

In `app/apps/students/schemas.py`, update the model import to include the new names:
```python
from app.apps.students.models import (
    ActivityKind,
    Enrollment,
    EnrollmentStatus,
    Student,
    StudentActivity,
    StudentSource,
)
```

Append the schema at the end of the file:
```python
class ActivityOut(CamelModel):
    """One activity-log entry for a student."""

    id: int
    kind: ActivityKind
    message: str
    meta: dict | None
    actor_name: str | None
    created_at: datetime

    @classmethod
    def from_model(cls, activity: StudentActivity) -> "ActivityOut":
        return cls(
            id=activity.id,
            kind=activity.kind,
            message=activity.message,
            meta=activity.meta,
            actor_name=activity.actor.full_name if activity.actor else None,
            created_at=activity.created_at,
        )
```

- [ ] **Step 7: Add the repository query**

In `app/apps/students/repository.py`, update the model import:
```python
from app.apps.students.models import Student, StudentActivity
```

Add the method to `StudentRepository` (after `get_by_identifier`):
```python
    async def list_activities(self, student_id: int) -> list[StudentActivity]:
        """A student's activity entries, newest first, with the actor loaded."""
        result = await self._session.scalars(
            select(StudentActivity)
            .where(StudentActivity.student_id == student_id)
            .order_by(StudentActivity.created_at.desc(), StudentActivity.id.desc())
            .options(selectinload(StudentActivity.actor))
        )
        return list(result)
```

- [ ] **Step 8: Wire the service — `list_activities` + log on create**

In `app/apps/students/service.py`:

Update imports — add the model enum, the helper, and the schema:
```python
from app.apps.students.models import (
    ActivityKind,
    Enrollment,
    EnrollmentStatus,
    Student,
)
from app.apps.students.activity import log_activity
from app.apps.students.schemas import (
    ActivityOut,
    EnrollmentOut,
    NewEnrollmentInput,
    NewStudentInput,
    StudentOut,
    StudentUpdate,
)
```

In `create_student`, after `await self._repo.assign_public_code(student)` and before the opening-payment block, append:
```python
        log_activity(
            self._session, student, ActivityKind.created, "Öğrenci kaydı oluşturuldu"
        )
```

Add a service method (e.g. after `list_enrollments`):
```python
    async def list_activities(self, code: str) -> list[ActivityOut]:
        """A student's activity log, newest first."""
        student = await self._get_or_404(code)
        rows = await self._repo.list_activities(student.id)
        return [ActivityOut.from_model(row) for row in rows]
```

- [ ] **Step 9: Add the endpoint**

In `app/apps/students/router.py`, add `ActivityOut` to the schema import:
```python
from app.apps.students.schemas import (
    ActivityOut,
    EnrollmentOut,
    NewEnrollmentInput,
    NewStudentInput,
    StudentOut,
    StudentUpdate,
)
```

Add the route (after `list_enrollments`):
```python
@router.get("/{code}/activity", response_model=list[ActivityOut])
async def list_activity(code: str, session: SessionDep, _: CanRead) -> list[ActivityOut]:
    """The student's activity log, newest first."""
    try:
        return await StudentService(session).list_activities(code)
    except StudentNotFoundError:
        raise _NOT_FOUND from None
```

- [ ] **Step 10: Run the tests to verify they pass**

Run: `pytest tests/test_activity.py -v`
Expected: PASS (both tests).

- [ ] **Step 11: Run the full api suite (no regressions)**

Run: `pytest -q`
Expected: all tests pass.

- [ ] **Step 12: Commit**

```bash
git add app/apps/students/models.py app/apps/students/activity.py \
  app/apps/students/schemas.py app/apps/students/repository.py \
  app/apps/students/service.py app/apps/students/router.py \
  alembic/versions/d9c2b7e34a15_add_student_activities.py tests/test_activity.py
git commit -m "feat(students): add student activity log with creation event and feed endpoint"
```

---

### Task 2: Log `approved` and `enrolled` events (api)

**Files:**
- Modify: `app/apps/students/service.py` (`approve_student`, `add_enrollment`)
- Test: `tests/test_activity.py` (add two tests)

**Interfaces:**
- Consumes: `log_activity`, `ActivityKind` (from Task 1).
- Produces: no new public symbols; `approve_student` emits `ActivityKind.approved`, `add_enrollment` emits `ActivityKind.enrolled`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_activity.py`:
```python
async def _create_term(client: AsyncClient, headers: Headers) -> int:
    res = await client.post(
        f"{API}/terms",
        headers=headers,
        json={"name": "2026 Güz", "start": "2026-09-01", "end": "2027-01-31"},
    )
    return res.json()["id"]


async def test_approve_logs_activity(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    created = await client.post(
        f"{API}/students",
        headers=headers,
        json=_student_payload("appr@test.com", status="pending", fee=12_000),
    )
    code = created.json()["id"]
    assert (await client.patch(f"{API}/students/{code}/approve", headers=headers)).status_code == 200

    rows = (await client.get(f"{API}/students/{code}/activity", headers=headers)).json()
    kinds = [row["kind"] for row in rows]
    assert "approved" in kinds


async def test_add_enrollment_logs_activity(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    code = (
        await client.post(
            f"{API}/students", headers=headers, json=_student_payload("enr@test.com")
        )
    ).json()["id"]
    term_id = await _create_term(client, headers)
    added = await client.post(
        f"{API}/students/{code}/enrollments",
        headers=headers,
        json={
            "termId": term_id,
            "lang": "İngilizce",
            "level": "B1 — Orta",
            "course": "Hafta Sonu Yoğun",
            "plan": "Peşin",
            "fee": 8_000,
            "start": "2026-09-01",
        },
    )
    assert added.status_code == 201

    rows = (await client.get(f"{API}/students/{code}/activity", headers=headers)).json()
    enrolled = [row for row in rows if row["kind"] == "enrolled"]
    assert len(enrolled) == 1
    assert "B1" in enrolled[0]["message"]
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `pytest tests/test_activity.py -k "approve_logs or add_enrollment_logs" -v`
Expected: FAIL — no `approved` / `enrolled` rows exist yet.

- [ ] **Step 3: Log the `approved` event**

In `app/apps/students/service.py`, inside `approve_student`, immediately before `await self._session.commit()`:
```python
        log_activity(self._session, student, ActivityKind.approved, "Kayıt onaylandı")
```

- [ ] **Step 4: Log the `enrolled` event**

In `app/apps/students/service.py`, inside `add_enrollment`, immediately before `await self._session.commit()`:
```python
        term_label = enrollment.term.name if enrollment.term else "dönem atanmadı"
        log_activity(
            self._session,
            student,
            ActivityKind.enrolled,
            f"Yeni dönem kaydı: {payload.level} — {term_label}",
        )
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_activity.py -v`
Expected: PASS (all activity tests).

- [ ] **Step 6: Commit**

```bash
git add app/apps/students/service.py tests/test_activity.py
git commit -m "feat(students): record activity on approval and new term enrollment"
```

---

### Task 3: Log `payment_recorded` event (api)

**Files:**
- Modify: `app/apps/payments/service.py` (`record_payment`)
- Test: `tests/test_activity.py` (add one test)

**Interfaces:**
- Consumes: `log_activity`, `ActivityKind` (from Task 1). `record_payment` already has the `student` object via `self._resolve(code)`.
- Produces: `record_payment` emits `ActivityKind.payment_recorded` with `meta={"amount": <int>}`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_activity.py`:
```python
async def test_record_payment_logs_activity(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    code = (
        await client.post(
            f"{API}/students",
            headers=headers,
            json=_student_payload("pay@test.com", fee=10_000),
        )
    ).json()["id"]

    pay = await client.post(
        f"{API}/students/{code}/payments",
        headers=headers,
        json={"amount": 500, "paidAt": "2026-03-01", "method": "Nakit"},
    )
    assert pay.status_code == 201

    rows = (await client.get(f"{API}/students/{code}/activity", headers=headers)).json()
    payment_rows = [row for row in rows if row["kind"] == "payment_recorded"]
    assert len(payment_rows) == 1
    assert payment_rows[0]["meta"]["amount"] == 500
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_activity.py::test_record_payment_logs_activity -v`
Expected: FAIL — no `payment_recorded` row.

- [ ] **Step 3: Log the payment event**

In `app/apps/payments/service.py`, add the imports near the existing students imports:
```python
from app.apps.students.activity import log_activity
from app.apps.students.models import ActivityKind, Enrollment, Student
```
(`Enrollment` and `Student` are already imported on that line — extend it rather than duplicating; add `ActivityKind` and the `log_activity` import.)

In `record_payment`, immediately before `await self._session.commit()`:
```python
        log_activity(
            self._session,
            student,
            ActivityKind.payment_recorded,
            f"Ödeme alındı (₺{payload.amount})",
            {"amount": payload.amount},
        )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_activity.py::test_record_payment_logs_activity -v`
Expected: PASS.

- [ ] **Step 5: Run the full api suite**

Run: `pytest -q`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add app/apps/payments/service.py tests/test_activity.py
git commit -m "feat(payments): record activity when a payment is taken"
```

---

### Task 4: Activity timeline on the student detail page (web)

Work in the **web** repo: `/Users/selametsamli/projects/power-campus-web`. First create the branch:

```bash
git checkout -b feat/student-activity-log
```

**Files:**
- Modify: `src/types/domain.ts` (add `StudentActivityKind`, `StudentActivity`)
- Modify: `src/features/students/studentsApi.ts` (add `activity`)
- Modify: `src/features/students/StudentDetailPage.tsx` (load + render the timeline)

**Interfaces:**
- Consumes: `GET /students/{id}/activity` → `StudentActivity[]` (from Tasks 1–3).
- Produces: `studentsApi.activity(id: string): Promise<StudentActivity[]>`; an internal `ActivityTimeline` component on the detail page.

- [ ] **Step 1: Add the domain types**

In `src/types/domain.ts`, append:
```ts
export type StudentActivityKind =
  | 'created'
  | 'approved'
  | 'enrolled'
  | 'payment_recorded'
  | 'status_changed'
  | 'note_added';

/** One entry in a student's activity log. */
export interface StudentActivity {
  id: number;
  kind: StudentActivityKind;
  message: string;
  meta?: Record<string, unknown> | null;
  actorName?: string | null;
  createdAt: string;
}
```

- [ ] **Step 2: Add the API client method**

In `src/features/students/studentsApi.ts`:

Add `StudentActivity` to the domain type import:
```ts
import type { NewStudentInput, Student, StudentActivity, StudentStatus } from '@/types/domain';
```

Add the method inside the `studentsApi` object (after `enrollments`):
```ts
  async activity(id: string): Promise<StudentActivity[]> {
    const { data } = await axiosClient.get<StudentActivity[]>(`/students/${id}/activity`);
    return data;
  },
```

- [ ] **Step 3: Load the activity in the detail page**

In `src/features/students/StudentDetailPage.tsx`:

Add `StudentActivity` to the domain type import (the line importing `Student, Term`):
```ts
import type { Student, StudentActivity, Term } from '@/types/domain';
```

Near the other detail state (where `installments` / `payments` state lives, ~line 235), add:
```ts
  const [activity, setActivity] = useState<StudentActivity[]>([]);
```

Add a load effect next to the existing installments/payments effect (~line 251):
```ts
  useEffect(() => {
    if (!student) return;
    let active = true;
    studentsApi
      .activity(student.id)
      .then((rows) => {
        if (active) setActivity(rows);
      })
      .catch(() => {
        if (active) setActivity([]);
      });
    return () => {
      active = false;
    };
  }, [student?.id]);
```

- [ ] **Step 4: Render the timeline**

In `src/features/students/StudentDetailPage.tsx`, render the timeline in the read-only column, right after `<EnrollmentHistory items={history} />` (~line 594):
```tsx
              <EnrollmentHistory items={history} />
              <ActivityTimeline items={activity} />
```

Add the component near `EnrollmentHistory` (after its closing brace, ~line 1014):
```tsx
const ACTIVITY_ICON: Record<StudentActivity['kind'], string> = {
  created: 'plus',
  approved: 'check',
  enrolled: 'layers',
  payment_recorded: 'wallet',
  status_changed: 'trend',
  note_added: 'clipboard',
};

function ActivityTimeline({ items }: { items: StudentActivity[] }) {
  if (items.length === 0) return null;
  return (
    <Section icon="clock" title="Aktivite" subtitle="Öğrenci kaydındaki son işlemler">
      {items.map((item) => (
        <div
          key={item.id}
          className="flex items-start gap-3 border-b border-line py-2.5 last:border-0"
        >
          <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent">
            <Icon name={ACTIVITY_ICON[item.kind] ?? 'info'} size={13} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="m-0 text-[13.5px] font-medium">{item.message}</p>
            <p className="m-0 text-[12px] text-ink-3">
              {item.actorName ?? 'Sistem'} · {formatDate(item.createdAt)}
            </p>
          </div>
        </div>
      ))}
    </Section>
  );
}
```

(`Icon`, `Section`, and `formatDate` are already imported in this file; the icon names `plus`, `check`, `layers`, `wallet`, `trend`, `clipboard`, `clock`, `info` all exist in `src/components/ui/icons.ts`.)

- [ ] **Step 5: Verify lint and types**

Run from the web repo root:
```bash
npm run lint && npm run typecheck
```
Expected: both pass with no errors.

- [ ] **Step 6: Commit**

```bash
git add src/types/domain.ts src/features/students/studentsApi.ts \
  src/features/students/StudentDetailPage.tsx
git commit -m "feat(students): show student activity timeline on detail page"
```

---

## Self-Review

**Spec coverage:**
- Persisted per-student activity table → Task 1 (`StudentActivity` + migration). ✅
- `log_activity` helper reused across apps → Task 1 (helper in `activity.py`), used in Tasks 2–3. ✅
- Events: created (Task 1), approved + enrolled (Task 2), payment_recorded (Task 3). ✅
- `GET /students/{code}/activity`, newest-first, with `actorName`, `students:read` → Task 1 (endpoint + ordering + permission test). ✅
- `status_changed` / `note_added` reserved but not emitted → enum members defined in Task 1, no emit. ✅
- Web types + client + read-only timeline → Task 4. ✅
- Tests: create/approve/enroll/payment produce rows; feed newest-first; actorName present; permission enforced → Tasks 1–3. ✅
- **Spec deviation (documented):** `rejected` event dropped — `reject_student` hard-deletes the student and cascade-removes activities, making the event dead data. Noted in Global Constraints.
- **Spec deviation (documented):** activity `message` strings are Turkish (not the spec's English examples), matching existing persisted strings like `"Açılış tahsilatı"`.

**Placeholder scan:** No TBD/TODO; every code step shows complete code. ✅

**Type consistency:** `ActivityKind` members match between model (Task 1), emitters (Tasks 2–3), schema, and the web `StudentActivityKind` union (Task 4). `log_activity` signature is identical at definition (Task 1) and every call site (Tasks 1–3). `ActivityOut.actor_name`/`created_at` serialize to `actorName`/`createdAt`, consumed by the web `StudentActivity` interface. ✅
