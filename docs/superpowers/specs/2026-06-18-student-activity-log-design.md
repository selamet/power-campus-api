# Student Activity Log — Design

**Date:** 2026-06-18
**Repos:** `power-campus-api` (FastAPI) + `power-campus-web` (Vite/React)
**Status:** Approved, ready for planning

This is the **first** of three sub-projects in the student CRM/operations track.
The other two — **lifecycle status** and **interaction notes** — get their own
specs and build after this one. The shared `log_activity` helper introduced here
is what lets those later features record their events with a single call.

## Goal

Give each student a **persisted, chronological activity log** so staff can see
"what happened, when, and by whom" on a student's record: registration, approval/
rejection, new enrollment, and payments. The feed is read-only in the UI; entries
are written automatically by the service layer as those events occur.

## Non-goals

- No `status_changed` or `note_added` events yet — those arrive with their own
  sub-projects (the helper is built to accept them).
- No editing/deleting of activity entries (immutable log).
- Not replacing the dashboard's existing **derived** global activity feed
  (`app/apps/dashboard/service.py::activity`). That stays as-is. This new table
  could power it later, but that is out of scope here.
- No backfill of historical events for existing students; the log starts empty
  and fills as new events occur (demo seed may add a few sample rows).

## Background / current state

- Student status lives on `Enrollment` (`active/pending/inactive`), not on the
  student. Irrelevant to this spec but noted for context.
- `AuditedBase` already provides `id`, `createdAt`, **`createdBy`** (filled
  automatically from the request user by the session audit hook in
  `app/core/db`), `updatedAt`, `updatedBy`. We reuse `createdBy` as the **actor**,
  so no separate actor column is needed.
- The dashboard has a *derived* activity feed (computed from current student
  state). Ours is a *persisted* per-student log — a different concept; the two
  coexist.
- Apps follow the `app/apps/<feature>/{models,schemas,repository,service,router}.py`
  layout. Enums use the project pattern: `Enum(..., native_enum=False,
  values_callable=lambda c: [m.value for m in c])`.

## API design (`power-campus-api`)

### Model — `app/apps/students/models.py`

New table `student_activities`, extending `AuditedBase`:

| column        | type                              | notes                                            |
|---------------|-----------------------------------|--------------------------------------------------|
| `id`          | int PK                            | from `AuditedBase`                               |
| `student_id`  | FK → `students.id` ON DELETE CASCADE, indexed, not null | the subject student        |
| `kind`        | `ActivityKind` enum (string)      | see kinds below                                  |
| `message`     | `String(255)`, not null           | human-readable summary (e.g. "Enrolled in A1 — Güz 2026") |
| `meta`        | `JSON`, nullable                  | optional structured detail (e.g. `{"amount": 500}`, `{"from": "active", "to": "frozen"}`) |
| `created_at`  | datetime                          | from `AuditedBase` (event time)                  |
| `created_by`  | FK → `users.id`, nullable         | from `AuditedBase` = **actor**, auto-filled      |

`updated_at` / `updated_by` are inherited but unused (entries are immutable).

`ActivityKind` (`enum.StrEnum`), values for this spec:
`created`, `approved`, `rejected`, `enrolled`, `payment_recorded`.
Reserved for later specs (defined now, emitted later): `status_changed`,
`note_added`, `updated`.

Relationship: `actor: Mapped["User | None"]` via `foreign_keys=[created_by]`,
`lazy="selectin"` (mirrors how `Enrollment.approver` is wired) so the feed can
show the actor's name.

`Student` gets `activities` relationship with
`cascade="all, delete-orphan"`, `order_by="StudentActivity.id"`.

### Logging helper — `app/apps/students/service.py` (or a small `activity.py`)

```python
def log_activity(session, student, kind, message, meta=None):
    session.add(StudentActivity(
        student_id=student.id, kind=kind, message=message, meta=meta,
    ))
```

- Synchronous `session.add` inside the caller's existing transaction; `created_by`
  is set by the audit hook on flush. No separate commit.
- Lives in the students app and is imported where needed (incl. the payments app).

### Hook points (emit events)

| Flow                                   | Location                         | kind               | message example |
|----------------------------------------|----------------------------------|--------------------|-----------------|
| `create_student`                       | `students/service.py`            | `created`          | "Student record created (manual)" / "(invite)" |
| `approve_student`                      | `students/service.py`            | `approved`         | "Enrollment approved" |
| `reject_student`                       | `students/service.py`            | `rejected`         | "Enrollment rejected" |
| `add_enrollment`                       | `students/service.py`            | `enrolled`         | "Enrolled in {level} — {termName}" |
| `record_payment`                       | `payments` app service           | `payment_recorded` | "Payment received ₺{amount}", meta `{"amount": n}` |

If wiring the payment hook proves to introduce awkward coupling, it may be
deferred to the end of this sub-project, but it is in scope.

### Schema — `app/apps/students/schemas.py`

`ActivityOut(CamelModel)`: `id: int`, `kind: ActivityKind`, `message: str`,
`meta: dict | None`, `actorName: str | None`, `createdAt: datetime`.
Built from the model (`actorName = activity.actor.name if activity.actor`).

### Endpoint — `app/apps/students/router.py`

`GET /students/{code}/activity` → `list[ActivityOut]`, **newest first**
(`order_by created_at desc, id desc`), guarded by `CanRead` (`students:read`).
Resolves the student via the existing `_get_or_404` identifier logic.

### Repository — `app/apps/students/repository.py`

Add a query returning a student's activities newest-first with `actor` eager-loaded.

### Migration

New Alembic revision adding `student_activities` (table + FKs + index on
`studentId`), following the naming conventions in `app/core/base.py`.

## Web design (`power-campus-web`)

### Types — `src/types/domain.ts`

```ts
export type StudentActivityKind =
  | 'created' | 'approved' | 'rejected' | 'enrolled' | 'payment_recorded'
  | 'status_changed' | 'note_added';

export interface StudentActivity {
  id: number;
  kind: StudentActivityKind;
  message: string;
  meta?: Record<string, unknown> | null;
  actorName?: string | null;
  createdAt: string;
}
```
(Distinct from the dashboard's existing `ActivityItem`.)

### API client — `src/features/students/studentsApi.ts`

`activity(id: string): Promise<StudentActivity[]>` → `GET /students/{id}/activity`.

### UI — `src/features/students/StudentDetailPage.tsx`

New read-only **"Aktivite"** `Section` on the detail page: a timeline list where
each row shows a kind-based icon, the `message`, the actor name, and a relative
timestamp (reuse existing `Icon`, `format`/relative-time, and `Section`
patterns). A small `kind → { icon, tone }` map drives the icons. Loads via the
existing slice/`useEffect` data pattern used for installments/payments/enrollments.

Lifecycle/notes kinds are included in the icon map now so later specs need no UI
change to render them.

## Permissions

- `GET …/activity` → `students:read`.
- Writes happen only as side effects of already-permissioned flows
  (`students:write` actions, payment recording); no new write permission.

## Testing (`power-campus-api`, pytest)

1. Creating a student writes one `created` activity row.
2. Approve / reject write `approved` / `rejected` rows for the right student.
3. `add_enrollment` writes an `enrolled` row with the level/term in the message.
4. Recording a payment writes a `payment_recorded` row with `meta.amount`.
5. `GET …/activity` returns rows **newest-first** and includes `actorName`.
6. The endpoint requires `students:read` (403 without it).

## Commit plan (English, no Claude attribution, stage by stage)

**api**
1. `feat(students): add student activity log model and migration`
2. `feat(students): record activity on create, approve, reject and enroll`
3. `feat(payments): record activity when a payment is taken`
4. `feat(students): expose GET /students/{code}/activity endpoint`
5. `test(students): cover activity logging and feed ordering`

**web**
6. `feat(students): student activity timeline on detail page`

(Each repo is committed on its own branch per the project's branch-per-feature
cadence; exact grouping may merge adjacent steps if small.)

## Open questions

None blocking. Payment-hook coupling is the only soft spot and has a fallback
(defer within this sub-project).
