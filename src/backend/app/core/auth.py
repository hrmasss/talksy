"""JWT authentication utilities."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from app.config import settings
from app.core.exceptions import UnauthorizedException
from app.core.logging import logger
from litestar.connection import ASGIConnection
from litestar.handlers import BaseRouteHandler

# JWT configuration
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30


def create_access_token(user_id: UUID, email: str) -> str:
    """Create a JWT access token."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "email": email,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: UUID) -> str:
    """Create a JWT refresh token."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedException(detail="Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedException(detail="Invalid token") from exc


def get_user_id_from_token(token: str) -> UUID:
    """Extract user ID from a valid access token."""
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise UnauthorizedException(detail="Invalid token type")
    return UUID(payload["sub"])


def extract_token_from_header(authorization: str | None) -> str:
    """Extract the bearer token from the Authorization header."""
    if not authorization:
        raise UnauthorizedException(detail="Authorization header required")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedException(detail="Invalid authorization header format")
    return parts[1]


async def require_auth(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """Litestar guard that requires a valid JWT access token.

    Sets ``connection.state.user_id`` on success.
    """
    authorization = connection.headers.get("authorization")
    token = extract_token_from_header(authorization)
    user_id = get_user_id_from_token(token)
    connection.state.user_id = user_id
    logger.debug(f"Authenticated request for user {user_id}")
