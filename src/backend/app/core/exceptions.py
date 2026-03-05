"""Custom application exceptions."""

from litestar.exceptions import HTTPException
from litestar.status_codes import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)


class TalksyException(HTTPException):
    """Base exception for Talksy application."""

    status_code = HTTP_500_INTERNAL_SERVER_ERROR
    detail = "An unexpected error occurred"


class BadRequestException(TalksyException):
    """Bad request exception."""

    status_code = HTTP_400_BAD_REQUEST
    detail = "Bad request"


class UnauthorizedException(TalksyException):
    """Unauthorized access exception."""

    status_code = HTTP_401_UNAUTHORIZED
    detail = "Authentication required"


class ForbiddenException(TalksyException):
    """Forbidden access exception."""

    status_code = HTTP_403_FORBIDDEN
    detail = "Access forbidden"


class NotFoundException(TalksyException):
    """Resource not found exception."""

    status_code = HTTP_404_NOT_FOUND
    detail = "Resource not found"


class ConflictException(TalksyException):
    """Resource conflict exception."""

    status_code = HTTP_409_CONFLICT
    detail = "Resource conflict"


class ValidationException(TalksyException):
    """Validation error exception."""

    status_code = HTTP_422_UNPROCESSABLE_ENTITY
    detail = "Validation error"


class AIServiceException(TalksyException):
    """AI service error exception."""

    status_code = HTTP_500_INTERNAL_SERVER_ERROR
    detail = "AI service error"
