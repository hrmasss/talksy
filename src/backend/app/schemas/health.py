"""Health check schemas."""

from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.base import BaseSchema


class HealthResponse(BaseSchema):
    """Schema for health check response."""

    status: str = Field(description="Overall health status")
    version: str = Field(description="Application version")
    timestamp: datetime = Field(description="Current server timestamp")
    environment: str = Field(description="Current environment")
    services: dict[str, Any] = Field(
        default={}, description="Status of dependent services"
    )


class ServiceHealth(BaseSchema):
    """Schema for individual service health."""

    name: str
    status: str  # healthy, degraded, unhealthy
    latency_ms: float | None = None
    message: str | None = None
