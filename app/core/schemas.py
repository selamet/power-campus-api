"""Shared Pydantic base schema.

All API schemas serialize to ``camelCase`` (matching the frontend) while
accepting both ``camelCase`` and ``snake_case`` on input.
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base schema with camelCase aliasing and ORM attribute reading."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
