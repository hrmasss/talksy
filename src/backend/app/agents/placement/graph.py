"""LangGraph workflow for IELTS placement test.

Flow:
    initialise → generate_question → [INTERRUPT] →
    process_answer → (next_question | evaluate) → END
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from ..common.checkpointer import get_checkpointer
from .nodes import (
    evaluate_placement_node,
    generate_placement_question_node,
    initialise_placement_node,
    process_placement_answer_node,
    route_after_placement_answer,
)
from .state import PlacementState

# ───────────────────────────────────────────────────────────────────

def _build_placement_graph() -> StateGraph:
    builder = StateGraph(PlacementState)

    builder.add_node("initialise", initialise_placement_node)
    builder.add_node("generate_question", generate_placement_question_node)
    builder.add_node("process_answer", process_placement_answer_node)
    builder.add_node("evaluate", evaluate_placement_node)

    builder.add_edge(START, "initialise")
    builder.add_edge("initialise", "generate_question")
    builder.add_edge("generate_question", "process_answer")  # INTERRUPT before this

    builder.add_conditional_edges(
        "process_answer",
        route_after_placement_answer,
        {"next_question": "generate_question", "evaluate": "evaluate"},
    )

    builder.add_edge("evaluate", END)

    return builder


_graph = None


async def _ensure_graph():
    global _graph
    if _graph is None:
        cp = await get_checkpointer()
        builder = _build_placement_graph()
        _graph = builder.compile(
            checkpointer=cp,
            interrupt_before=["process_answer"],
        )
    return _graph


def _config(thread_id: str) -> dict[str, Any]:
    return {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 60,
    }


# ───────────────────────────────────────────────────────────────────
# Public API
# ───────────────────────────────────────────────────────────────────

async def start_placement(
    initial_state: dict[str, Any],
    thread_id: str,
) -> dict[str, Any]:
    """Start the placement test. Returns state after first question."""
    g = await _ensure_graph()
    result = await g.ainvoke(initial_state, _config(thread_id))
    return result


async def submit_placement_answer(
    answer: str,
    thread_id: str,
) -> dict[str, Any]:
    """Submit an answer and continue the placement test."""
    g = await _ensure_graph()
    config = _config(thread_id)
    await g.aupdate_state(config, {"current_answer": answer})
    result = await g.ainvoke(None, config)
    return result


async def get_placement_state(thread_id: str) -> dict[str, Any] | None:
    """Get current placement test state."""
    g = await _ensure_graph()
    config = _config(thread_id)
    snapshot = await g.aget_state(config)
    return snapshot.values if snapshot and snapshot.values else None
