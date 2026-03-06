"""LangGraph workflow for IELTS exam practice.

Flow (with interrupt for candidate input):
    initialise → generate_question → [INTERRUPT – wait for answer] →
    process_answer → evaluate_answer → generate_question → … →
    final_evaluation → END
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from langgraph.graph import END, START, StateGraph

from ..common.checkpointer import get_checkpointer
from .nodes import (
    initialise_exam_node,
    generate_question_node,
    process_answer_node,
    evaluate_answer_node,
    final_evaluation_node,
    route_after_answer,
    route_after_evaluation,
)
from .state import ExamState


# ---------------------------------------------------------------------------
# Graph definition
# ---------------------------------------------------------------------------

def _build_exam_graph() -> StateGraph:
    builder = StateGraph(ExamState)

    # Nodes
    builder.add_node("initialise", initialise_exam_node)
    builder.add_node("generate_question", generate_question_node)
    builder.add_node("process_answer", process_answer_node)
    builder.add_node("evaluate_answer", evaluate_answer_node)
    builder.add_node("final_evaluation", final_evaluation_node)

    # Edges
    builder.add_edge(START, "initialise")
    builder.add_edge("initialise", "generate_question")

    # After generating a question we INTERRUPT so the API can return it
    # to the client.  The client sends the answer, the API resumes the
    # graph via ``process_answer``.
    builder.add_edge("generate_question", "process_answer")

    builder.add_conditional_edges(
        "process_answer",
        route_after_answer,
        {"evaluate": "evaluate_answer", "final": "final_evaluation"},
    )

    builder.add_conditional_edges(
        "evaluate_answer",
        route_after_evaluation,
        {"next_question": "generate_question", "final": "final_evaluation"},
    )

    builder.add_edge("final_evaluation", END)

    return builder


_graph = None


async def _ensure_graph():
    global _graph
    if _graph is None:
        cp = await get_checkpointer()
        builder = _build_exam_graph()
        _graph = builder.compile(
            checkpointer=cp,
            interrupt_before=["process_answer"],  # pause before processing answer
        )
    return _graph


def _config(thread_id: str) -> Dict[str, Any]:
    return {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 80,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def start_exam(
    initial_state: Dict[str, Any],
    thread_id: str,
) -> Dict[str, Any]:
    """Start a new exam session.  Returns state after the first question
    is generated (graph pauses at ``process_answer``)."""
    g = await _ensure_graph()
    result = await g.ainvoke(initial_state, _config(thread_id))
    return result


async def submit_answer(
    answer: str,
    thread_id: str,
) -> Dict[str, Any]:
    """Resume the graph with the candidate's answer.

    The graph was paused at ``process_answer``.  We update state with
    the answer, then let it continue to evaluate and (maybe) ask the
    next question.
    """
    g = await _ensure_graph()
    config = _config(thread_id)

    # Update the pending state with the candidate's answer
    await g.aupdate_state(config, {"current_answer": answer})

    # Resume – runs process_answer → evaluate → generate_question (or final)
    result = await g.ainvoke(None, config)
    return result


async def get_exam_state(thread_id: str) -> Dict[str, Any] | None:
    """Retrieve the current state snapshot for a given exam thread."""
    g = await _ensure_graph()
    config = _config(thread_id)
    snapshot = await g.aget_state(config)
    return snapshot.values if snapshot and snapshot.values else None
