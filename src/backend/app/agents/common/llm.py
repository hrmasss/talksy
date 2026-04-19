"""Centralised Groq LLM factory."""

from __future__ import annotations

import itertools
import threading

from app.config import settings
from langchain_groq import ChatGroq

# ── Round-robin key pool ──────────────────────────────────────────
_lock = threading.Lock()
_key_cycle: itertools.cycle | None = None


def _configured_keys() -> list[str]:
    """Return configured Groq API keys from env."""
    raw_values = [settings.groq_api_keys or "", settings.groq_api_key or ""]
    keys: list[str] = []
    for raw in raw_values:
        keys.extend(k.strip() for k in raw.split(",") if k.strip())
    return keys


def _get_key_pool() -> itertools.cycle:
    """Lazily build a round-robin cycle from configured keys."""
    global _key_cycle
    if _key_cycle is None:
        with _lock:
            if _key_cycle is None:
                keys = _configured_keys()
                if not keys:
                    raise ValueError(
                        "No Groq API keys configured – set GROQ_API_KEY or GROQ_API_KEYS "
                        "in your .env file"
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
    if settings.groq_model and settings.groq_model.strip():
        return settings.groq_model
    return "llama-3.3-70b-versatile"


def get_llm(
    model: str | None = None,
    temperature: float | None = 0.7,
    api_key: str | None = None,
) -> ChatGroq:
    """Return a ChatGroq instance."""
    resolved_api_key = api_key or next_api_key()
    resolved_model = _resolve_model(model)

    kwargs: dict = {
        "model": resolved_model,
        "api_key": resolved_api_key,
        "max_retries": 2,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature

    return ChatGroq(**kwargs)


async def get_user_api_key(user_id: str) -> str | None:
    """Return the first Groq API key stored in the user's preferences."""
    from app.db.tables import User

    try:
        row = await User.select(User.preferences).where(User.id == user_id).first()
        if row:
            prefs = row.get("preferences") or {}
            keys = prefs.get("groq_api_keys", []) or prefs.get("gemini_api_keys", [])
            if keys:
                return keys[0]
    except Exception:
        pass
    return None
