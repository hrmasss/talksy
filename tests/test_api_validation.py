from __future__ import annotations

from app.core.exception_handlers import extract_validation_details
from app.schemas.user import UserCreate


class _WrappedValidationError(Exception):
	def __init__(self, extra: list[dict[str, object]], detail: str = "Validation failed") -> None:
		super().__init__(detail)
		self.extra = extra
		self.detail = detail


def test_extract_validation_details_from_wrapped_litestar_error() -> None:
	exc = _WrappedValidationError(
		extra=[
			{
				"message": "Value error, Password must contain at least one uppercase letter",
				"key": "password",
			}
		]
	)

	assert extract_validation_details(exc) == [
		{
			"loc": ["password"],
			"msg": "Password must contain at least one uppercase letter",
			"type": "value_error",
		}
	]


def test_extract_validation_details_from_pydantic_error() -> None:
	try:
		UserCreate.model_validate(
			{
				"email": "test@example.com",
				"password": "testappp",
				"full_name": "Test User",
			}
		)
	except Exception as exc:  # pragma: no cover - exercised by assertion below
		details = extract_validation_details(exc)
	else:  # pragma: no cover
		raise AssertionError("Expected password validation to fail")

	assert details[0]["loc"] == ["password"]
	assert details[0]["msg"] == "Password must contain at least one uppercase letter"
