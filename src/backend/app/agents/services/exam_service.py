"""Service layer for the IELTS exam agent.

Bridges the LangGraph exam workflow with the HTTP API and Piccolo ORM.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import settings
from app.core.logging import logger
from app.db.tables import MockExamSession
from app.services.speech import cache_audio_file

from ..exam.graph import get_exam_state, start_exam, submit_answer
from ..exam.state import DIFFICULTY_PRESETS

# Directory where cached question audio files are stored
AUDIO_CACHE_DIR = Path(settings.static_dir) / "audio"


def _audio_path(thread_id: str, question_number: int) -> Path:
    """Return the on-disk path for a cached question audio file."""
    safe_id = hashlib.sha256(thread_id.encode()).hexdigest()[:16]
    return AUDIO_CACHE_DIR / safe_id / f"q{question_number}.wav"


async def _generate_question_audio(
    text: str, thread_id: str, question_number: int
) -> str | None:
    """Generate TTS audio for a question and cache it on disk.
    
    Optimized to use cached audio when available and Gemini TTS.
    Returns the URL path to the audio file, or None on failure.
    """
    if not text or not text.strip():
        return None

    path = _audio_path(thread_id, question_number)
    if path.exists():
        safe_id = hashlib.sha256(thread_id.encode()).hexdigest()[:16]
        return f"/static/audio/{safe_id}/q{question_number}.wav"

    try:
        from app.agents.common.llm import next_api_key
        from app.services.speech import text_to_speech

        audio_bytes = await text_to_speech(text, api_key=next_api_key())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(audio_bytes)
        safe_id = hashlib.sha256(thread_id.encode()).hexdigest()[:16]
        logger.info("Generated audio for exam question: {}", f"/static/audio/{safe_id}/q{question_number}.wav")
        return f"/static/audio/{safe_id}/q{question_number}.wav"
    except Exception as exc:
        logger.warning("Question audio generation failed: {}", exc)
        return None


class ExamService:
    """Manage IELTS practice exam sessions backed by the exam LangGraph."""

    # ── session persistence helpers ───────────────────────────────

    @staticmethod
    async def _create_session_record(
        user_id: str,
        thread_id: str,
        section: str,
        difficulty: str,
        target_band: str | float | None,
        total_questions: int,
    ) -> None:
        """Persist a new mock-exam session row."""
        try:
            await MockExamSession.insert(
                MockExamSession(
                    user=user_id,
                    thread_id=thread_id,
                    section=section,
                    difficulty=difficulty,
                    target_band=str(target_band) if target_band else None,
                    total_questions=total_questions,
                    status="in_progress",
                )
            )
        except Exception as exc:
            logger.warning("Could not save session record: {}", exc)

    @staticmethod
    async def _update_session_progress(
        thread_id: str,
        question_index: int,
    ) -> None:
        """Update the question index on an existing session row."""
        try:
            await (
                MockExamSession.update({
                    MockExamSession.question_index: question_index,
                    MockExamSession.updated_at: datetime.now(),
                })
                .where(MockExamSession.thread_id == thread_id)
            )
        except Exception as exc:
            logger.warning("Could not update session progress: {}", exc)

    @staticmethod
    async def _complete_session(
        thread_id: str,
        band_score: float | None,
        section_scores: list | None,
        strengths: list | None,
        weaknesses: list | None,
        recommendations: list | None,
        report_markdown: str | None,
    ) -> None:
        """Mark a session as completed and store final results."""
        try:
            await (
                MockExamSession.update({
                    MockExamSession.status: "completed",
                    MockExamSession.band_score: band_score,
                    MockExamSession.section_scores: section_scores or [],
                    MockExamSession.strengths: strengths or [],
                    MockExamSession.weaknesses: weaknesses or [],
                    MockExamSession.recommendations: recommendations or [],
                    MockExamSession.report_markdown: report_markdown,
                    MockExamSession.completed_at: datetime.now(),
                    MockExamSession.updated_at: datetime.now(),
                })
                .where(MockExamSession.thread_id == thread_id)
            )
        except Exception as exc:
            logger.warning("Could not complete session record: {}", exc)

    # ── public queries ────────────────────────────────────────────

    @staticmethod
    async def get_active_session(user_id: str) -> dict[str, Any] | None:
        """Return the most recent in-progress session for a user, if any."""
        rows = await (
            MockExamSession.select(
                MockExamSession.thread_id,
                MockExamSession.section,
                MockExamSession.difficulty,
                MockExamSession.question_index,
                MockExamSession.total_questions,
                MockExamSession.started_at,
            )
            .where(MockExamSession.user == user_id)
            .where(MockExamSession.status == "in_progress")
            .order_by(MockExamSession.started_at, ascending=False)
            .limit(1)
            .output()
        )
        if not rows:
            return None
        row = rows[0]
        return {
            "thread_id": row["thread_id"],
            "section": row["section"],
            "difficulty": row["difficulty"],
            "question_index": row["question_index"],
            "total_questions": row["total_questions"],
            "started_at": row["started_at"].isoformat() if row.get("started_at") else None,
        }

    @staticmethod
    async def list_sessions(
        user_id: str,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Return a page of mock-exam sessions for a user."""
        q = (
            MockExamSession.select(
                MockExamSession.thread_id,
                MockExamSession.section,
                MockExamSession.difficulty,
                MockExamSession.status,
                MockExamSession.question_index,
                MockExamSession.total_questions,
                MockExamSession.band_score,
                MockExamSession.section_scores,
                MockExamSession.strengths,
                MockExamSession.weaknesses,
                MockExamSession.recommendations,
                MockExamSession.report_markdown,
                MockExamSession.started_at,
                MockExamSession.completed_at,
            )
            .where(MockExamSession.user == user_id)
            .order_by(MockExamSession.started_at, ascending=False)
            .limit(limit)
            .offset(offset)
        )
        if status:
            q = q.where(MockExamSession.status == status)
        rows = await q.output()
        return [
            {
                "thread_id": r["thread_id"],
                "section": r["section"],
                "difficulty": r["difficulty"],
                "status": r["status"],
                "question_index": r["question_index"],
                "total_questions": r["total_questions"],
                "band_score": r["band_score"],
                "section_scores": r["section_scores"],
                "strengths": r["strengths"],
                "weaknesses": r["weaknesses"],
                "recommendations": r["recommendations"],
                "report_markdown": r["report_markdown"],
                "started_at": r["started_at"].isoformat() if r.get("started_at") else None,
                "completed_at": r["completed_at"].isoformat() if r.get("completed_at") else None,
            }
            for r in rows
        ]

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
    ) -> dict[str, Any]:
        """Kick off a new exam session and return the first question."""
        preset = DIFFICULTY_PRESETS.get(difficulty, DIFFICULTY_PRESETS["intermediate"])
        band = target_band or preset["target_band"]
        total = preset.get("total_questions", 12)

        thread_id = f"exam_{user_id}_{uuid.uuid4().hex[:8]}"

        initial_state: dict[str, Any] = {
            "user_id": user_id,
            "exam_variant": "general" if "general" in exam_type else "academic",
            "exam_section": section,
            "difficulty_level": difficulty,
            "target_band": band,
            "topic": topic or "",
            "total_questions": total,
            "question_number": 0,
            "current_part": 1,
            "questions_asked": [],
            "candidate_answers": [],
            "performance_scores": [],
            "evaluations": [],
            "section_scores": [],
            "final_band_score": None,
            "final_report_markdown": None,
            "messages": [],
            "status": "initialising",
        }

        logger.info(
            f"Starting exam session thread={thread_id} user={user_id} "
            f"section={section} difficulty={difficulty} band={band}"
        )
        result = await start_exam(initial_state, thread_id=thread_id)

        # Persist session for resume / history
        await self._create_session_record(
            user_id=user_id,
            thread_id=thread_id,
            section=section,
            difficulty=difficulty,
            target_band=band,
            total_questions=total,
        )

        return await self._format_question_response(result, thread_id, section)

    async def answer_question(
        self,
        *,
        thread_id: str,
        answer: str,
    ) -> dict[str, Any]:
        """Submit the candidate's answer and get the next question (or final report)."""
        logger.info(f"Answer submitted for thread={thread_id}")
        result = await submit_answer(answer, thread_id=thread_id)

        status = result.get("status", "unknown")
        section = result.get("exam_section") or result.get("section", "")

        if status == "completed":
            report = self._format_final_report(result, thread_id)
            await self._complete_session(
                thread_id=thread_id,
                band_score=report.get("overall_band"),
                section_scores=report.get("section_scores"),
                strengths=report.get("strengths"),
                weaknesses=report.get("weaknesses"),
                recommendations=report.get("recommendations"),
                report_markdown=report.get("final_report_markdown"),
            )
            return report

        resp = await self._format_question_response(result, thread_id, section)
        await self._update_session_progress(thread_id, resp.get("question_index", 0))
        return resp

    async def get_session_state(self, *, thread_id: str) -> dict[str, Any]:
        """Return the current public state of an exam session."""
        state = await get_exam_state(thread_id=thread_id)
        if state is None:
            return {"error": "session_not_found", "thread_id": thread_id}

        status = state.get("status", "unknown")
        section = state.get("exam_section") or state.get("section", "")
        if status == "completed":
            return self._format_final_report(state, thread_id)
        return await self._format_question_response(state, thread_id, section)

    # ── private helpers ───────────────────────────────────────────

    @staticmethod
    async def _format_question_response(
        state: dict[str, Any], thread_id: str, section: str = ""
    ) -> dict[str, Any]:
        idx = state.get("question_number", 0)
        current_text = state.get("current_question")
        current_type = state.get("current_question_type")
        current_passage = state.get("current_question_passage")

        if not current_text:
            questions_asked = state.get("questions_asked", [])
            if questions_asked:
                latest_question = questions_asked[-1]
                current_text = latest_question.get("text")
                current_type = current_type or latest_question.get("type")
                current_passage = current_passage or latest_question.get("passage")

        current_q = {
            "text": current_text or "",
            "type": current_type or "discussion",
            "passage": current_passage,
        }

        section = section or state.get("exam_section") or state.get("section", "")

        # Generate and cache audio for listening/speaking questions
        audio_url: str | None = None
        if section in ("listening", "speaking") and current_text:
            audio_url = await _generate_question_audio(
                current_text, thread_id, idx
            )

        return {
            "thread_id": thread_id,
            "status": state.get("status", "awaiting_answer"),
            "section": section,
            "current_part": state.get("current_part", 1),
            "question_index": idx,
            "total_questions": state.get("total_questions", 0),
            "current_question": current_q,
            "audio_url": audio_url,
        }

    @staticmethod
    def _format_final_report(state: dict[str, Any], thread_id: str) -> dict[str, Any]:
        return {
            "thread_id": thread_id,
            "status": "completed",
            "section": state.get("exam_section") or state.get("section"),
            "overall_band": state.get("overall_band") or state.get("final_band_score"),
            "section_scores": state.get("section_scores", []),
            "evaluations": state.get("evaluations", []),
            "strengths": state.get("strengths", []),
            "weaknesses": state.get("weaknesses", []),
            "recommendations": state.get("recommendations", []),
            "final_report_markdown": state.get("final_report_markdown"),
        }


# Module-level singleton
exam_service = ExamService()
