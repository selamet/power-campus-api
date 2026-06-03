"""Request-scoped context used to attribute audit columns to the acting user."""

from contextvars import ContextVar

# Set per request (see the auth dependency); read by the audit flush hook so
# that `createdBy` / `updatedBy` are populated without threading the user
# through every service call.
current_user_id: ContextVar[int | None] = ContextVar("current_user_id", default=None)
