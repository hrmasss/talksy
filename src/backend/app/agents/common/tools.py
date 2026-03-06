"""Shared LangChain tools available to all agents."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_core.tools import tool
from langchain_community.utilities import GoogleSerperAPIWrapper

from app.config import settings


@tool
def get_current_datetime() -> str:
    """Return the current UTC date-time as ``YYYY-MM-DD HH:MM:SS UTC``."""
    return datetime.now(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M:%S %Z")


@tool
def web_search(query: str, num_results: int = 5) -> str:
    """Search the web and return concise results.

    Useful for finding current IELTS trends, sample topics, band-score
    criteria or any other up-to-date information.

    Args:
        query: A search query string.
        num_results: How many results to return (1–10).
    """
    if not settings.serper_api_key:
        return "SERPER_API_KEY is not configured."
    try:
        num_results = min(max(num_results, 1), 10)
        search = GoogleSerperAPIWrapper(
            serper_api_key=settings.serper_api_key,
            gl="us",
            hl="en",
            k=num_results,
        )
        return search.run(query)
    except Exception as exc:
        return f"Web search error: {exc}"
