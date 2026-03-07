from collections.abc import Iterable

from litestar.connection import Request
from litestar.response import Response
from litestar.status_codes import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
from pydantic import ValidationError

from app.core.logging import logger


def _clean_validation_message(message: object) -> str:
    text = str(message or "").strip()
    if text.startswith("Value error, "):
        return text.removeprefix("Value error, ")
    return text


def _normalise_validation_error(error: object) -> dict[str, object]:
    if not isinstance(error, dict):
        return {"msg": _clean_validation_message(error)}

    loc = error.get("loc") or error.get("key") or []
    if isinstance(loc, tuple):
        loc = list(loc)
    elif isinstance(loc, str):
        loc = [loc]
    elif not isinstance(loc, list):
        loc = []

    msg = error.get("msg") or error.get("message") or error.get("detail") or ""
    normalised = {
        "loc": loc,
        "msg": _clean_validation_message(msg),
        "type": error.get("type", "value_error"),
    }
    if error.get("input") is not None:
        normalised["input"] = error["input"]
    return normalised


def extract_validation_details(exc: Exception) -> list[dict[str, object]]:
    details: list[dict[str, object]] = []

    if isinstance(exc, ValidationError):
        for error in exc.errors():
            details.append(_normalise_validation_error(error))
        return details

    extra = getattr(exc, "extra", None)
    if isinstance(extra, Iterable) and not isinstance(extra, (str, bytes, dict)):
        for error in extra:
            details.append(_normalise_validation_error(error))

    if not details:
        msg = getattr(exc, "detail", str(exc))
        details.append({"msg": _clean_validation_message(msg)})

    return details

def validation_exception_handler(request: Request, exc: Exception) -> Response:
    """Handle validation exceptions dynamically to show Pydantic field errors."""
    details = extract_validation_details(exc)

    return Response(
        content={
            "detail": "Validation error",
            "errors": details
        },
        status_code=HTTP_400_BAD_REQUEST,
    )

def internal_error_handler(request: Request, exc: Exception) -> Response:
    """Handle uncaught internal errors transparently."""
    logger.error("Internal Server Error: %s", str(exc), exc_info=exc)
    return Response(
        content={"detail": "Internal server error"},
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
    )
