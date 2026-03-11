from types import SimpleNamespace

from app.core.exception_handlers import internal_error_handler
from app.core.logging import logger


def test_internal_error_handler_logs_message_with_exception() -> None:
    messages: list[str] = []

    token = logger.add(lambda m: messages.append(m), format="{message}", level="ERROR")
    try:
        internal_error_handler(SimpleNamespace(), ValueError("boom"))
    finally:
        logger.remove(token)

    assert any("Internal Server Error:" in m for m in messages)
    assert not any("%s" in m for m in messages)

