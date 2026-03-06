"""Health check endpoint."""

from datetime import UTC, datetime

from app import __version__
from app.config import settings
from app.schemas.health import HealthResponse
from litestar import Controller, get
from litestar.status_codes import HTTP_200_OK


class HealthController(Controller):
    """Health check controller."""

    path = "/health"
    tags = ["Health"]

    @get(
        "/",
        summary="Health Check",
        description="Check the health status of the application and its dependencies.",
        status_code=HTTP_200_OK,
    )
    async def health_check(self) -> HealthResponse:
        """Perform health check."""
        services = {}

        # Check database connection
        try:
            from app.db.tables import User
            await User.select().limit(1)
            services["database"] = {"status": "healthy"}
        except Exception as e:
            services["database"] = {"status": "unhealthy", "error": str(e)}

        # Check Redis connection (if configured)
        if settings.redis_url:
            try:
                import redis.asyncio as redis
                r = redis.from_url(settings.redis_url)
                await r.ping()
                services["redis"] = {"status": "healthy"}
                await r.close()
            except Exception as e:
                services["redis"] = {"status": "unhealthy", "error": str(e)}

        # Check AI service
        if settings.openai_api_key:
            services["ai"] = {"status": "healthy", "provider": "openai"}
        else:
            services["ai"] = {"status": "degraded", "message": "API key not configured"}

        # Determine overall status
        all_healthy = all(
            s.get("status") == "healthy" for s in services.values()
        )
        status = "healthy" if all_healthy else "degraded"

        return HealthResponse(
            status=status,
            version=__version__,
            timestamp=datetime.now(UTC),
            environment=settings.environment,
            services=services,
        )

    @get(
        "/live",
        summary="Liveness Check",
        description="Simple liveness check to verify the application is running.",
        status_code=HTTP_200_OK,
    )
    async def liveness(self) -> dict:
        """Simple liveness check."""
        return {"status": "ok"}

    @get(
        "/ready",
        summary="Readiness Check",
        description="Check if the application is ready to receive traffic.",
        status_code=HTTP_200_OK,
    )
    async def readiness(self) -> dict:
        """Readiness check."""
        try:
            from app.db.tables import User
            await User.select().limit(1)
            return {"status": "ready"}
        except Exception as e:
            return {"status": "not_ready", "error": str(e)}
