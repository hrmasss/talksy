import json
from datetime import datetime
from typing import Any, Annotated
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict


def parse_json_dict_field(v: Any) -> dict[str, Any]:
    """Parse and normalize dict-shaped JSON fields."""
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except (json.JSONDecodeError, TypeError):
            return {}
    return v if isinstance(v, dict) else {}


def parse_json_list_field(v: Any) -> list[Any]:
    """Parse and normalize list-shaped JSON fields."""
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except (json.JSONDecodeError, TypeError):
            return []
    return v if isinstance(v, list) else []


JsonDict = Annotated[dict[str, Any], BeforeValidator(parse_json_dict_field)]
JsonList = Annotated[list[Any], BeforeValidator(parse_json_list_field)]


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

    @staticmethod
    def parse_json(v: Any) -> Any:
        """Parse a JSON string if necessary."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return v
        return v


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
