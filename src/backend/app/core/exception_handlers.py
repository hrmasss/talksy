from litestar.connection import Request
from litestar.response import Response
from litestar.status_codes import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from app.core.logging import logger


def validation_exception_handler(request: Request, exc: Exception) -> Response:
    """Return a small custom response for validation failures."""
    return Response(
        content={"detail": "Validation error", "errors": [str(exc)]},
        status_code=HTTP_400_BAD_REQUEST,
    )


def internal_error_handler(request: Request, exc: Exception) -> Response:
    """Handle uncaught internal errors transparently."""
    logger.error("Internal Server Error: %s", str(exc), exc_info=exc)
    return Response(
        content={"detail": "Internal server error"},
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
    )
