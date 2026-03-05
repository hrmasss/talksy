"""Base schema classes and mixins."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        },
    )


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""

    created_at: datetime | None = None
    updated_at: datetime | None = None


class IDMixin(BaseModel):
    """Mixin for ID field."""

    id: UUID


class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = 1
    page_size: int = 20
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseSchema):
    """Paginated response wrapper."""

    items: list[Any]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def create(cls, items: list, total: int, page: int, page_size: int):
        pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
