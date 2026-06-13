"""Catalog of granular permissions assigned to staff accounts.

Permissions are ``module:action`` strings. The :class:`Permission` enum is the
single source of truth; :data:`PERMISSION_CATALOG` adds the Turkish labels the
admin UI renders as grouped read/write checkboxes.
"""

import enum
from dataclasses import dataclass


class Permission(enum.StrEnum):
    """Every fine-grained capability that can be granted to a user."""

    dashboard_read = "dashboard:read"
    students_read = "students:read"
    students_write = "students:write"
    finance_read = "finance:read"
    finance_write = "finance:write"
    invites_write = "invites:write"
    terms_read = "terms:read"
    terms_write = "terms:write"
    users_read = "users:read"
    users_write = "users:write"


#: All permission keys; ``admin`` accounts implicitly hold every one of these.
ALL_PERMISSIONS: frozenset[str] = frozenset(p.value for p in Permission)


@dataclass(frozen=True)
class PermissionItem:
    """A single grantable permission with its display label."""

    key: str
    action: str
    label: str


@dataclass(frozen=True)
class PermissionGroup:
    """A module grouping the permissions the admin toggles together."""

    module: str
    label: str
    permissions: tuple[PermissionItem, ...]


def _read(perm: Permission) -> PermissionItem:
    return PermissionItem(key=perm.value, action="read", label="Görüntüleme")


def _write(perm: Permission) -> PermissionItem:
    return PermissionItem(key=perm.value, action="write", label="Düzenleme")


#: UI-facing catalog: ordered modules, each with its read/write permissions.
PERMISSION_CATALOG: tuple[PermissionGroup, ...] = (
    PermissionGroup(
        module="dashboard",
        label="Genel Bakış",
        permissions=(_read(Permission.dashboard_read),),
    ),
    PermissionGroup(
        module="students",
        label="Öğrenciler",
        permissions=(_read(Permission.students_read), _write(Permission.students_write)),
    ),
    PermissionGroup(
        module="finance",
        label="Finans / Ödemeler",
        permissions=(_read(Permission.finance_read), _write(Permission.finance_write)),
    ),
    PermissionGroup(
        module="invites",
        label="Davetler",
        permissions=(
            PermissionItem(
                key=Permission.invites_write.value, action="write", label="Davet gönderme"
            ),
        ),
    ),
    PermissionGroup(
        module="terms",
        label="Dönemler",
        permissions=(_read(Permission.terms_read), _write(Permission.terms_write)),
    ),
    PermissionGroup(
        module="users",
        label="Yetkililer",
        permissions=(_read(Permission.users_read), _write(Permission.users_write)),
    ),
)
