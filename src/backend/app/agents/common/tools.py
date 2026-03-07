"""Shared LangChain tools available to all agents."""

from __future__ import annotations

from app.config import settings

# Re-export memory tools so agents can bind them alongside other tools
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_core.tools import tool
from tavily import TavilyClient


def _tavily_search(query: str, num_results: int) -> str:
    """Run a search via Tavily and return formatted results."""
    client = TavilyClient(api_key=settings.tavily_api_key)
    response = client.search(
        query=query,
        max_results=num_results,
        search_depth="basic",
    )
    results = response.get("results", [])
    if not results:
        return "No results found."
    parts: list[str] = []
    for r in results:
        title = r.get("title", "")
        url = r.get("url", "")
        content = r.get("content", "")
        parts.append(f"{title}\n{url}\n{content}")
    return "\n\n".join(parts)


def _serper_search(query: str, num_results: int) -> str:
    """Run a search via Google Serper and return results."""
    search = GoogleSerperAPIWrapper(
        serper_api_key=settings.serper_api_key,
        gl="us",
        hl="en",
        k=num_results,
    )
    return search.run(query)


@tool
def web_search(query: str, num_results: int = 5) -> str:
    """Search the web and return concise results.

    Useful for finding current IELTS trends, sample topics, band-score
    criteria or any other up-to-date information.

    Args:
        query: A search query string.
        num_results: How many results to return (1-10).
    """
    num_results = min(max(num_results, 1), 10)

    # Try Tavily first
    if settings.tavily_api_key:
        try:
            return _tavily_search(query, num_results)
        except Exception:
            pass  # fall through to Serper

    # Fallback to Serper
    if settings.serper_api_key:
        try:
            return _serper_search(query, num_results)
        except Exception as exc:
            return f"Web search error: {exc}"

    return "No web search API key is configured (set TAVILY_API_KEY or SERPER_API_KEY)."
