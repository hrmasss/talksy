"""LangGraph workflow for IELTS topic generation.

Flow:
    assess_level → generate_topics → END
"""

from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, StateGraph

from ..common.checkpointer import get_checkpointer
from .nodes import assess_level_node, generate_topics_node
from .state import TopicGeneratorState

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

def _route(state: TopicGeneratorState) -> Literal["assess", "generate", "end"]:
    if state.get("status") == "failed":
        return "end"
    if state.get("estimated_band") is None:
        return "assess"
    if not state.get("speaking_topics") and not state.get("writing_topics"):
        return "generate"
    return "end"


# ---------------------------------------------------------------------------
# Graph definition
# ---------------------------------------------------------------------------

_workflow = StateGraph(TopicGeneratorState)

_workflow.add_node("assess_level", assess_level_node)
_workflow.add_node("generate_topics", generate_topics_node)

_workflow.set_entry_point("assess_level")

_workflow.add_conditional_edges(
    "assess_level",
    _route,
    {"assess": "assess_level", "generate": "generate_topics", "end": END},
)
_workflow.add_conditional_edges(
    "generate_topics",
    _route,
    {"assess": "assess_level", "generate": "generate_topics", "end": END},
)

# ---------------------------------------------------------------------------
# Compiled graph (lazy, with checkpointer)
# ---------------------------------------------------------------------------

_graph = None


async def _ensure_graph():
    global _graph
    if _graph is None:
        cp = await get_checkpointer()
        _graph = _workflow.compile(checkpointer=cp)
    return _graph


def _config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}, "recursion_limit": 50}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def run_topic_generator(
    initial_state: dict[str, Any],
    thread_id: str | None = None,
) -> TopicGeneratorState:
    """Run the full topic-generation workflow and return final state."""
    g = await _ensure_graph()
    tid = thread_id or f"topics_{initial_state.get('user_id', 'anon')}"
    return await g.ainvoke(initial_state, _config(tid))


async def stream_topic_generator(
    initial_state: dict[str, Any],
    thread_id: str | None = None,
):
    """Yield intermediate states during topic generation."""
    g = await _ensure_graph()
    tid = thread_id or f"topics_{initial_state.get('user_id', 'anon')}"
    async for state in g.astream(initial_state, _config(tid)):
        yield state
