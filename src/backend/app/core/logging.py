"""Logging configuration using Loguru."""

import sys
from typing import Any

from app.config import settings
from loguru import logger


def setup_logging() -> None:
    """Configure loguru for the application."""
    # Remove default handler
    logger.remove()

    # Log format
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # Console handler
    logger.add(
        sys.stdout,
        format=log_format,
        level="DEBUG" if settings.debug else "INFO",
        colorize=True,
        backtrace=True,
        diagnose=settings.debug,
    )

    # File handler for production
    if settings.is_production:
        logger.add(
            "logs/talksy_{time:YYYY-MM-DD}.log",
            format=log_format,
            level="INFO",
            rotation="10 MB",
            retention="30 days",
            compression="gz",
            backtrace=True,
            diagnose=False,
        )

        # Separate error log
        logger.add(
            "logs/talksy_errors_{time:YYYY-MM-DD}.log",
            format=log_format,
            level="ERROR",
            rotation="10 MB",
            retention="60 days",
            compression="gz",
            backtrace=True,
            diagnose=True,
        )

    logger.info(f"Logging configured for {settings.environment} environment")


def log_request(request_data: dict[str, Any]) -> None:
    """Log incoming request details."""
    logger.info(
        f"Request: {request_data.get('method', 'UNKNOWN')} {request_data.get('path', '/')}"
    )


def log_response(status_code: int, duration_ms: float) -> None:
    """Log response details."""
    level = "INFO" if status_code < 400 else "WARNING" if status_code < 500 else "ERROR"
    getattr(logger, level.lower())(f"Response: {status_code} ({duration_ms:.2f}ms)")


__all__ = ["log_request", "log_response", "logger", "setup_logging"]
