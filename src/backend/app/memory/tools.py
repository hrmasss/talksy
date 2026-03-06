"""LangChain @tool wrappers around the memory service.

These tools can be bound to any LangGraph agent so the LLM can
autonomously store and recall long-term user memories.
"""

from __future__ import annotations

import json

from langchain_core.tools import tool

from .service import memory_service

# ── store ────────────────────────────────────────────────────────

@tool
async def store_user_memory(
    user_id: str,
    category: str,
    content: str,
    importance: float = 0.5,
    metadata_json: str = "{}",
) -> str:
    """Store a piece of information in the user's long-term memory.

    Use this whenever you learn something noteworthy about the user —
    their strengths, weaknesses, goals, exam results, study preferences,
    or any observation worth remembering for future sessions.

    Args:
        user_id:       The user's unique identifier.
        category:      One of: writing, speaking, reading, listening,
                       vocabulary, grammar, pronunciation, user_activity,
                       exam_result, study_preference, strength, weakness,
                       goal, feedback.
        content:       The textual content to remember (will be embedded).
        importance:    0.0 (trivial) to 1.0 (critical). Default 0.5.
        metadata_json: Optional JSON string with extra structured data.
    """
    try:
        meta = json.loads(metadata_json) if metadata_json else {}
    except json.JSONDecodeError:
        meta = {}

    entry = await memory_service.store(
        user_id=user_id,
        category=category,
        content=content,
        importance=importance,
        metadata=meta,
    )
    return f"Memory stored (id={entry.id}, category={entry.category.value})."


# ── recall ───────────────────────────────────────────────────────

@tool
async def recall_user_memory(
    user_id: str,
    query: str,
    category: str | None = None,
    top_k: int = 5,
) -> str:
    """Search the user's long-term memory for relevant information.

    Use this to recall prior exam results, known weaknesses, preferred
    topics, or anything previously stored about the user.

    Args:
        user_id:  The user's unique identifier.
        query:    A natural-language query describing what to look for.
        category: Optional filter - one of the memory categories.
        top_k:    Maximum number of results. Default 5.
    """
    results = await memory_service.search(
        user_id=user_id,
        query=query,
        category=category,
        top_k=top_k,
    )
    if not results:
        return "No relevant memories found."

    lines = []
    for r in results:
        lines.append(
            f"[{r.entry.category.value}] (relevance={r.score:.2f}): {r.entry.content}"
        )
    return "\n".join(lines)


# ── progress summary ────────────────────────────────────────────

@tool
async def get_user_progress_summary(user_id: str) -> str:
    """Get an aggregated overview of the user's learning progress.

    Returns memory counts per category, recent exam scores, known
    strengths / weaknesses, and goals.  Use this at the start of a
    session to understand where the user currently stands.

    Args:
        user_id: The user's unique identifier.
    """
    summary = await memory_service.get_progress_summary(user_id=user_id)

    parts = [f"## Progress Summary for user {user_id}"]
    parts.append(f"Total memories: {summary.total_memories}")

    if summary.categories:
        parts.append("### Categories")
        for cat, count in summary.categories.items():
            parts.append(f"  - {cat}: {count}")

    if summary.recent_exam_results:
        parts.append("### Recent Exam Results")
        for r in summary.recent_exam_results:
            parts.append(f"  - {r}")

    if summary.strengths:
        parts.append("### Strengths")
        for s in summary.strengths:
            parts.append(f"  - {s}")

    if summary.weaknesses:
        parts.append("### Weaknesses")
        for w in summary.weaknesses:
            parts.append(f"  - {w}")

    if summary.goals:
        parts.append("### Goals")
        for g in summary.goals:
            parts.append(f"  - {g}")

    if summary.latest_activity:
        parts.append(f"### Latest Activity\n{summary.latest_activity}")

    return "\n".join(parts)


# ── delete ───────────────────────────────────────────────────────

@tool
async def delete_user_memories(
    user_id: str,
    category: str | None = None,
) -> str:
    """Delete a user's stored memories, optionally filtered by category.

    Args:
        user_id:  The user's unique identifier.
        category: Optional category filter. If omitted, ALL memories for
                  the user are removed.
    """
    count = await memory_service.delete_user_memories(
        user_id=user_id,
        category=category,
    )
    scope = f" in category '{category}'" if category else ""
    return f"Deleted {count} memories for user {user_id}{scope}."
