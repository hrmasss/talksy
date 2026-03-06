"""Shared LangChain tools available to all agents."""

from __future__ import annotations

from app.config import settings

# Re-export memory tools so agents can bind them alongside other tools
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_core.tools import tool


@tool
def web_search(query: str, num_results: int = 5) -> str:
    """Search the web and return concise results.

    Useful for finding current IELTS trends, sample topics, band-score
    criteria or any other up-to-date information.

    Args:
        query: A search query string.
        num_results: How many results to return (1-10).
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
