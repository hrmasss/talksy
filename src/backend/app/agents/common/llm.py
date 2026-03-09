"""Centralised LLM factory.

Every agent in the project resolves its model through this module so that
API keys, models and defaults are configured once.  Uses Google Gemini
via ``langchain-google-genai``.
"""

from __future__ import annotations

import itertools
import threading

from app.config import settings
from langchain_google_genai import ChatGoogleGenerativeAI

# ── Round-robin key pool ──────────────────────────────────────────
_lock = threading.Lock()
_key_cycle: itertools.cycle | None = None


def _get_key_pool() -> itertools.cycle:
    """Lazily build a round-robin cycle from configured keys."""
    global _key_cycle
    if _key_cycle is None:
        with _lock:
            if _key_cycle is None:
                raw = settings.gemini_api_keys or ""
                keys = [k.strip() for k in raw.split(",") if k.strip()]
                if not keys:
                    raise ValueError(
                        "No Gemini API keys configured – set GEMINI_API_KEYS "
                        "in your .env file (comma-separated for multiple keys)"
                    )
                _key_cycle = itertools.cycle(keys)
    return _key_cycle


def next_api_key() -> str:
    """Return the next API key from the round-robin pool."""
    return next(_get_key_pool())


def _resolve_model(model: str | None) -> str:
    """Pick the first non-empty model identifier."""
    if model and model.strip():
        return model
    if settings.gemini_model and settings.gemini_model.strip():
        return settings.gemini_model
    return "gemini-2.5-flash"


def get_llm(
    model: str | None = None,
    temperature: float | None = 0.7,
    api_key: str | None = None,
) -> ChatGoogleGenerativeAI:
    """Return a *ChatGoogleGenerativeAI* instance.

    Parameters
    ----------
    model:
        Model identifier, e.g. ``"gemini-2.5-flash"``.  Falls back to
        the configured default when ``None``.
    temperature:
        Sampling temperature.  ``None`` lets the API decide.
    api_key:
        Override the API key (e.g. a user-provided key).
        When ``None`` the next key from the env pool is used.
    """
    resolved_api_key = api_key or next_api_key()
    resolved_model = _resolve_model(model)

    kwargs: dict = {
        "model": resolved_model,
        "google_api_key": resolved_api_key,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature

    return ChatGoogleGenerativeAI(**kwargs)


async def get_user_api_key(user_id: str) -> str | None:
    """Return the first Gemini API key stored in the user's preferences,
    or ``None`` so the caller falls back to the env pool.
    """
    from app.db.tables import User

    try:
        row = await User.select(User.preferences).where(
            User.id == user_id
        ).first()
        if row:
            keys = (row.get("preferences") or {}).get("gemini_api_keys", [])
            if keys:
                return keys[0]
    except Exception:
        pass
    return None
