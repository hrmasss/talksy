from __future__ import annotations

import re

from litestar.connection import Request
from litestar.response import Response
from litestar.status_codes import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from app.core.logging import logger

# Pattern to strip the leading "Value error, " prefix from Pydantic messages.
_VALUE_ERROR_RE = re.compile(r"^Value error,\s*", re.IGNORECASE)


def extract_validation_details(exc: Exception) -> list[dict[str, object]]:
    """Normalise a Litestar or Pydantic validation error into a flat list.

    Returns ``[{"loc": [...], "msg": "...", "type": "..."}]``.
    """
    # Pydantic ValidationError
    if hasattr(exc, "errors") and callable(exc.errors):
        raw_errors = exc.errors()
        return [
            {
                "loc": list(e.get("loc", [])),
                "msg": _VALUE_ERROR_RE.sub("", e.get("msg", str(e))),
                "type": e.get("type", "validation_error"),
            }
            for e in raw_errors
        ]

    # Litestar wrapped validation (extra=[{message, key}])
    extra: list[dict[str, object]] | None = getattr(exc, "extra", None)
    if extra and isinstance(extra, list):
        out: list[dict[str, object]] = []
        for item in extra:
            msg = str(item.get("message", ""))
            msg = _VALUE_ERROR_RE.sub("", msg)
            key = item.get("key", "")
            loc = [key] if key else []
            out.append({"loc": loc, "msg": msg, "type": "value_error"})
        return out

    return [{"loc": [], "msg": str(exc), "type": "validation_error"}]


def validation_exception_handler(request: Request, exc: Exception) -> Response:
    """Return a small custom response for validation failures."""
    errors = extract_validation_details(exc)
    return Response(
        content={"detail": "Validation error", "errors": errors},
        status_code=HTTP_400_BAD_REQUEST,
    )


def internal_error_handler(request: Request, exc: Exception) -> Response:
    """Handle uncaught internal errors transparently."""
    logger.opt(exception=exc).error("Internal Server Error: {}", str(exc))
    return Response(
        content={"detail": "Internal server error"},
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
    )
