"""Service layer for the IELTS exam agent.

Bridges the LangGraph exam workflow with the HTTP API and Piccolo ORM.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from app.core.logging import logger
from ..exam.graph import start_exam, submit_answer, get_exam_state
from ..exam.state import DIFFICULTY_PRESETS


class ExamService:
    """Manage IELTS practice exam sessions backed by the exam LangGraph."""

    # ── exam lifecycle ────────────────────────────────────────────

    async def create_exam_session(
        self,
        *,
        user_id: str,
        exam_type: str = "ielts_academic",
        section: str = "speaking",
        difficulty: str = "intermediate",
        target_band: float | None = None,
        topic: str | None = None,
    ) -> Dict[str, Any]:
        """Kick off a new exam session and return the first question.

        Parameters
        ----------
        user_id:     The user taking the exam.
        exam_type:   ``ielts_academic`` or ``ielts_general``.
        section:     ``speaking``, ``writing``, ``reading``, ``listening``.
        difficulty:  A key from ``DIFFICULTY_PRESETS`` (beginner / intermediate / advanced / expert)
                     – or supply a custom ``target_band``.
        target_band: Overrides the preset target band if given.
        topic:       Optional topic hint (e.g. "tourism", "environment").

        Returns
        -------
        Dict with ``thread_id``, ``current_question``, ``section``, ``part``,
        ``question_index``, ``total_questions``, ``status``.
        """
        preset = DIFFICULTY_PRESETS.get(difficulty, DIFFICULTY_PRESETS["intermediate"])
        band = target_band or preset["target_band"]
        total = preset.get("total_questions", 12)

        thread_id = f"exam_{user_id}_{uuid.uuid4().hex[:8]}"

        initial_state: Dict[str, Any] = {
            "user_id": user_id,
            "exam_type": exam_type,
            "section": section,
            "difficulty": difficulty,
            "target_band": band,
            "topic": topic or "",
            "total_questions": total,
            "current_question_index": 0,
            "current_part": 1,
            "questions": [],
            "answers": [],
            "evaluations": [],
            "section_scores": [],
            "overall_band": None,
            "final_report_markdown": None,
            "messages": [],
            "status": "initialising",
        }

        logger.info(
            f"Starting exam session thread={thread_id} user={user_id} "
            f"section={section} difficulty={difficulty} band={band}"
        )
        result = await start_exam(initial_state, thread_id=thread_id)

        return self._format_question_response(result, thread_id)

    async def answer_question(
        self,
        *,
        thread_id: str,
        answer: str,
    ) -> Dict[str, Any]:
        """Submit the candidate's answer and get the next question (or final report).

        Returns a dict whose ``status`` field is one of:
        ``awaiting_answer`` · ``evaluating`` · ``completed``.
        """
        logger.info(f"Answer submitted for thread={thread_id}")
        result = await submit_answer(answer, thread_id=thread_id)

        status = result.get("status", "unknown")
        if status == "completed":
            return self._format_final_report(result, thread_id)
        return self._format_question_response(result, thread_id)

    async def get_session_state(self, *, thread_id: str) -> Dict[str, Any]:
        """Return the current public state of an exam session."""
        state = await get_exam_state(thread_id=thread_id)
        if state is None:
            return {"error": "session_not_found", "thread_id": thread_id}

        status = state.get("status", "unknown")
        if status == "completed":
            return self._format_final_report(state, thread_id)
        return self._format_question_response(state, thread_id)

    # ── private helpers ───────────────────────────────────────────

    @staticmethod
    def _format_question_response(state: Dict[str, Any], thread_id: str) -> Dict[str, Any]:
        questions = state.get("questions", [])
        idx = state.get("current_question_index", 0)
        current_q = questions[idx] if idx < len(questions) else None

        return {
            "thread_id": thread_id,
            "status": state.get("status", "awaiting_answer"),
            "section": state.get("section"),
            "current_part": state.get("current_part", 1),
            "question_index": idx,
            "total_questions": state.get("total_questions", 0),
            "current_question": current_q,
        }

    @staticmethod
    def _format_final_report(state: Dict[str, Any], thread_id: str) -> Dict[str, Any]:
        return {
            "thread_id": thread_id,
            "status": "completed",
            "section": state.get("section"),
            "overall_band": state.get("overall_band"),
            "section_scores": state.get("section_scores", []),
            "evaluations": state.get("evaluations", []),
            "final_report_markdown": state.get("final_report_markdown"),
        }


# Module-level singleton
exam_service = ExamService()
