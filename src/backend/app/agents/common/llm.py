"""Centralised LLM factory.

Every agent in the project resolves its model through this module so that
API keys, base URLs and default models are configured once.
"""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.config import settings


def _resolve_model(model: str | None) -> str:
    """Pick the first non-empty model identifier."""
    if model and model.strip():
        return model
    if settings.openrouter_model and settings.openrouter_model.strip():
        return settings.openrouter_model
    if settings.llm_model and settings.llm_model.strip():
        return settings.llm_model
    return "openai/gpt-4.1-mini"


def get_llm(
    model: str | None = None,
    temperature: float | None = 0.7,
    api_key: str | None = None,
) -> ChatOpenAI:
    """Return a *ChatOpenAI* instance pointed at OpenRouter (or any
    OpenAI-compatible endpoint).

    Parameters
    ----------
    model:
        Model identifier, e.g. ``"openai/gpt-4.1-mini"``.  Falls back to
        the configured default when ``None``.
    temperature:
        Sampling temperature.  ``None`` lets the API decide.
    api_key:
        Override the API key from settings.
    """
    resolved_api_key = api_key or settings.openrouter_api_key
    resolved_model = _resolve_model(model)

    if not resolved_api_key:
        raise ValueError(
            "OPENROUTER_API_KEY is not configured – set it in your .env file"
        )

    kwargs: dict = {
        "model": resolved_model,
        "openai_api_key": resolved_api_key,
        "openai_api_base": settings.openrouter_api_base,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature

    return ChatOpenAI(**kwargs)
