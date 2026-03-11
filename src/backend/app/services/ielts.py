"""Service layer for the IELTS preparation platform.

Bridges placement tests, daily study, mock tests, and progress tracking
with the database and AI agents.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from app.config import settings
from app.core.logging import logger
from app.db.tables import (
    DailyStudyPlan,
    ExamAttempt,
    PlacementResponse,
    PlacementTest,
    ProgressSnapshot,
    StudyActivity,
    User,
)

from ..agents.common.llm import get_llm
from ..agents.daily_study.prompts import (
    get_activity_evaluation_prompt,
    get_daily_study_plan_prompt,
)
from ..agents.placement.graph import (
    get_placement_state,
    start_placement,
    submit_placement_answer,
)
from ..agents.placement.state import TOTAL_PLACEMENT_QUESTIONS


def _normalize_skill_profile(value: Any) -> dict[str, list[str]]:
    """Return a safe skill profile mapping from DB JSON or stringified JSON."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return {"strengths": [], "weaknesses": [], "focus_areas": []}

    if not isinstance(value, dict):
        return {"strengths": [], "weaknesses": [], "focus_areas": []}

    normalized: dict[str, list[str]] = {}
    for key in ("strengths", "weaknesses", "focus_areas"):
        raw = value.get(key, [])
        if isinstance(raw, list):
            normalized[key] = [str(item) for item in raw if item is not None]
        else:
            normalized[key] = []
    return normalized


def _normalize_json_list(value: Any) -> list[Any]:
    """Return a safe list from DB JSON or stringified JSON."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []

    return value if isinstance(value, list) else []


def _normalize_section_scores(value: Any) -> dict[str, float]:
    """Return a safe section score mapping from DB JSON or stringified JSON."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return {}

    if not isinstance(value, dict):
        return {}

    normalized: dict[str, float] = {}
    for key in ("listening", "reading", "writing", "speaking"):
        raw = value.get(key)
        if raw is None:
            continue
        try:
            normalized[key] = float(raw)
        except (TypeError, ValueError):
            continue

    return normalized


class IELTSService:
    """Manages the full IELTS preparation lifecycle."""

    # ── User Profile ─────────────────────────────────────────────

    async def get_ielts_profile(self, user_id: UUID) -> dict[str, Any]:
        """Get IELTS-specific user profile."""
        user = await User.select().where(User.id == user_id).first()
        if not user:
            return {}
        return {
            "target_band_score": user.get("target_band_score"),
            "exam_date": str(user["exam_date"]) if user.get("exam_date") else None,
            "preferred_daily_practice_time": user.get("preferred_daily_practice_time"),
            "current_estimated_band": user.get("current_estimated_band"),
            "skill_profile": _normalize_skill_profile(user.get("skill_profile", {})),
            "section_scores": _normalize_section_scores(user.get("section_scores", {})),
            "onboarding_completed": user.get("onboarding_completed", False),
        }

    async def update_ielts_profile(self, user_id: UUID, data: dict[str, Any]) -> dict[str, Any]:
        """Update IELTS-specific fields on the user."""
        update = {k: v for k, v in data.items() if v is not None}
        if update:
            await User.update(update).where(User.id == user_id)
        return await self.get_ielts_profile(user_id)

    # ── Placement Test ────────────────────────────────────────────

    async def start_placement_test(
        self,
        user_id: UUID,
        target_band_score: float | None = None,
        exam_date: date | None = None,
    ) -> dict[str, Any]:
        """Start the initial placement/diagnostic test."""
        thread_id = f"placement_{user_id}_{uuid.uuid4().hex[:8]}"

        # Save profile preferences
        profile_update: dict[str, Any] = {}
        if target_band_score:
            profile_update["target_band_score"] = target_band_score
            profile_update["target_score"] = target_band_score
        if exam_date:
            profile_update["exam_date"] = exam_date
        if profile_update:
            await User.update(profile_update).where(User.id == user_id)

        # Create placement test record
        pt = PlacementTest(
            id=uuid.uuid4(),
            user=user_id,
            status="in_progress",
            thread_id=thread_id,
        )
        await pt.save()

        # Start the LangGraph placement workflow
        initial_state = {
            "user_id": str(user_id),
            "target_band_score": target_band_score,
            "messages": [],
        }

        result = await start_placement(initial_state, thread_id=thread_id)

        return self._format_placement_question(result, thread_id)

    async def submit_placement_answer(
        self,
        thread_id: str,
        answer: str,
    ) -> dict[str, Any]:
        """Submit an answer during the placement test."""
        result = await submit_placement_answer(answer, thread_id=thread_id)

        status = result.get("status", "in_progress")

        if status == "completed":
            # Save results to DB and update user profile
            await self._save_placement_results(thread_id, result)
            return self._format_placement_result(result, thread_id)

        return self._format_placement_question(result, thread_id)

    async def get_placement_status(self, thread_id: str) -> dict[str, Any]:
        """Get current placement test status."""
        state = await get_placement_state(thread_id)
        if not state:
            return {"error": "not_found"}

        if state.get("status") == "completed":
            return self._format_placement_result(state, thread_id)
        return self._format_placement_question(state, thread_id)

    async def _save_placement_results(self, thread_id: str, result: dict[str, Any]) -> None:
        """Persist placement results to DB and update user profile."""
        # Find the placement test record
        pt = await PlacementTest.select().where(
            PlacementTest.thread_id == thread_id
        ).first()
        if not pt:
            return

        section_scores = _normalize_section_scores(result.get("section_scores", {}))

        # Update placement test record
        await PlacementTest.update({
            "status": "completed",
            "completed_at": datetime.now(),
            "listening_band": section_scores.get("listening"),
            "reading_band": section_scores.get("reading"),
            "writing_band": section_scores.get("writing"),
            "speaking_band": section_scores.get("speaking"),
            "overall_band": result.get("overall_band"),
            "skill_profile": {
                "strengths": result.get("strengths", []),
                "weaknesses": result.get("weaknesses", []),
                "focus_areas": result.get("focus_areas", []),
            },
            "ai_analysis": {
                "feedback": result.get("feedback_markdown", ""),
            },
        }).where(PlacementTest.id == pt["id"])

        # Save individual responses
        for resp in result.get("responses", []):
            pr = PlacementResponse(
                id=uuid.uuid4(),
                placement_test=pt["id"],
                section=resp.get("section", ""),
                question_text=resp.get("question", ""),
                question_type=resp.get("question_type", ""),
                user_answer=resp.get("answer", ""),
            )
            await pr.save()

        # Update user profile
        user_id = pt["user"]
        await User.update({
            "onboarding_completed": True,
            "current_estimated_band": result.get("overall_band"),
            "section_scores": section_scores,
            "skill_profile": {
                "strengths": result.get("strengths", []),
                "weaknesses": result.get("weaknesses", []),
                "focus_areas": result.get("focus_areas", []),
            },
        }).where(User.id == user_id)

        # Create initial progress snapshot
        snap = ProgressSnapshot(
            id=uuid.uuid4(),
            user=user_id,
            snapshot_date=date.today(),
            overall_band=result.get("overall_band"),
            listening_band=section_scores.get("listening"),
            reading_band=section_scores.get("reading"),
            writing_band=section_scores.get("writing"),
            speaking_band=section_scores.get("speaking"),
            strengths=result.get("strengths", []),
            weaknesses=result.get("weaknesses", []),
            ai_recommendations=result.get("focus_areas", []),
        )
        await snap.save()

    def _format_placement_question(self, state: dict[str, Any], thread_id: str) -> dict[str, Any]:
        return {
            "thread_id": thread_id,
            "status": state.get("status", "in_progress"),
            "section": state.get("current_section", "listening"),
            "question_index": state.get("question_number", 0),
            "total_questions": state.get("total_questions", TOTAL_PLACEMENT_QUESTIONS),
            "question_text": state.get("current_question", ""),
            "question_type": state.get("current_question_type", "multiple_choice"),
            "options": state.get("current_options", []),
            "time_limit_seconds": None,
        }

    def _format_placement_result(self, state: dict[str, Any], thread_id: str) -> dict[str, Any]:
        section_scores = _normalize_section_scores(state.get("section_scores", {}))
        return {
            "thread_id": thread_id,
            "status": "completed",
            "overall_band": state.get("overall_band", 5.0),
            "listening_band": section_scores.get("listening", 5.0),
            "reading_band": section_scores.get("reading", 5.0),
            "writing_band": section_scores.get("writing", 5.0),
            "speaking_band": section_scores.get("speaking", 5.0),
            "skill_profile": {
                "strengths": state.get("strengths", []),
                "weaknesses": state.get("weaknesses", []),
                "focus_areas": state.get("focus_areas", []),
            },
            "strengths": state.get("strengths", []),
            "weaknesses": state.get("weaknesses", []),
            "focus_areas": state.get("focus_areas", []),
            "feedback_markdown": state.get("feedback_markdown", ""),
        }

    # ── Daily Study Plan ──────────────────────────────────────────

    async def get_or_generate_daily_plan(self, user_id: UUID) -> dict[str, Any]:
        """Get today's study plan, generating one if it doesn't exist."""
        today = date.today()

        # Check for existing plan
        existing = await DailyStudyPlan.select().where(
            (DailyStudyPlan.user == user_id) &
            (DailyStudyPlan.study_date == today)
        ).first()

        if existing:
            activities = await StudyActivity.select().where(
                StudyActivity.daily_plan == existing["id"]
            ).order_by(StudyActivity.created_at)
            return self._format_daily_plan(existing, activities)

        # Generate new plan
        return await self._generate_daily_plan(user_id, today)

    async def get_daily_plan_by_id(self, user_id: UUID, plan_id: UUID) -> dict[str, Any]:
        """Return a specific daily plan by id."""
        plan = await DailyStudyPlan.select().where(
            (DailyStudyPlan.id == plan_id) &
            (DailyStudyPlan.user == user_id)
        ).first()
        if not plan:
            return {"error": "daily_plan_not_found"}

        activities = await StudyActivity.select().where(
            StudyActivity.daily_plan == plan_id
        ).order_by(StudyActivity.created_at)
        return self._format_daily_plan(plan, activities)

    async def list_recent_daily_plans(self, user_id: UUID, days: int = 7) -> dict[str, Any]:
        """Return the most recent daily plans within the last N days."""
        days = max(1, min(days, 365))
        today = date.today()
        start_date = today - timedelta(days=days - 1)

        plans = await DailyStudyPlan.select().where(
            (DailyStudyPlan.user == user_id) &
            (DailyStudyPlan.study_date >= start_date)
        ).order_by(DailyStudyPlan.study_date, ascending=False)

        items: list[dict[str, Any]] = []
        for plan in plans:
            activities = await StudyActivity.select().where(
                StudyActivity.daily_plan == plan["id"]
            ).order_by(StudyActivity.created_at)
            items.append(self._format_daily_plan(plan, activities))

        return {"items": items}

    async def _generate_daily_plan(self, user_id: UUID, study_date: date) -> dict[str, Any]:
        """Generate a new AI-powered daily study plan."""
        user = await User.select().where(User.id == user_id).first()
        if not user:
            return {"error": "user_not_found"}

        current_band = user.get("current_estimated_band") or 5.0
        target_band = user.get("target_band_score") or 7.0
        practice_time = user.get("preferred_daily_practice_time") or 30
        skill_profile = _normalize_skill_profile(user.get("skill_profile", {}))
        section_scores = _normalize_section_scores(user.get("section_scores", {}))

        # Get recent test history
        recent = await ExamAttempt.select().where(
            ExamAttempt.user == user_id
        ).order_by(ExamAttempt.created_at, ascending=False).limit(10)

        recent_history = [
            {
                "section": r.get("section", ""),
                "band_score": r.get("band_score"),
                "date": str(r.get("created_at", "")),
            }
            for r in recent
        ]

        prompt = get_daily_study_plan_prompt(
            current_band=current_band,
            target_band=target_band,
            strengths=skill_profile.get("strengths", []),
            weaknesses=skill_profile.get("weaknesses", []),
            focus_areas=skill_profile.get("focus_areas", []),
            section_scores=section_scores,
            recent_history=recent_history,
            practice_time_minutes=practice_time,
        )

        if not prompt or not prompt.strip():
            logger.error("Daily study plan prompt unexpectedly empty (user_id={})", str(user_id))
            return {"error": "daily_plan_prompt_empty"}

        llm = get_llm(model=settings.gemini_model, temperature=0.7)
        try:
            raw = await llm.ainvoke([{"role": "user", "content": prompt}])
        except Exception as exc:
            logger.opt(exception=exc).error(
                "Daily study plan LLM call failed (user_id={})",
                str(user_id),
            )
            return {"error": "daily_plan_generation_failed"}

        try:
            match = re.search(r"\{.*\}", raw.content, re.DOTALL)
            plan_data = json.loads(match.group()) if match else {}
        except Exception:
            plan_data = {"activities": [], "rationale": "Failed to generate plan"}

        activities_data = plan_data.get("activities", [])

        # Save plan to DB
        plan_id = uuid.uuid4()
        plan = DailyStudyPlan(
            id=plan_id,
            user=user_id,
            study_date=study_date,
            activities=[a.get("title", "") for a in activities_data],
            total_count=len(activities_data),
            ai_rationale=plan_data.get("rationale", ""),
        )
        await plan.save()

        # Save individual activities
        saved_activities = []
        for a in activities_data:
            act = StudyActivity(
                id=uuid.uuid4(),
                daily_plan=plan_id,
                user=user_id,
                section=a.get("section", "vocabulary"),
                activity_type=a.get("activity_type", "vocabulary_practice"),
                title=a.get("title", "Practice Activity"),
                content=a.get("content", {}),
                difficulty_level=a.get("difficulty_level", 1),
            )
            await act.save()
            saved_activities.append(act)

        result = await DailyStudyPlan.select().where(DailyStudyPlan.id == plan_id).first()
        acts = await StudyActivity.select().where(StudyActivity.daily_plan == plan_id)
        return self._format_daily_plan(result, acts)

    async def submit_activity_response(
        self,
        activity_id: UUID,
        user_response: str,
        time_spent_seconds: int = 0,
    ) -> dict[str, Any]:
        """Submit a response to a study activity and get AI feedback."""
        activity = await StudyActivity.select().where(StudyActivity.id == activity_id).first()
        if not activity:
            return {"error": "activity_not_found"}

        # AI evaluation
        prompt = get_activity_evaluation_prompt(
            section=activity["section"],
            activity_type=activity["activity_type"],
            content=activity.get("content", {}),
            user_response=user_response,
        )

        llm = get_llm(model=settings.gemini_model, temperature=0.3)
        raw = await llm.ainvoke([{"role": "user", "content": prompt}])

        try:
            match = re.search(r"\{.*\}", raw.content, re.DOTALL)
            feedback = json.loads(match.group()) if match else {}
        except Exception:
            feedback = {"band_score": 5.0, "feedback": "Evaluation completed.", "suggestions": []}

        # Save to DB
        await StudyActivity.update({
            "is_completed": True,
            "user_response": {"text": user_response},
            "ai_feedback": feedback,
            "band_score": feedback.get("band_score"),
            "time_spent_seconds": time_spent_seconds,
            "completed_at": datetime.now(),
        }).where(StudyActivity.id == activity_id)

        # Update plan completion count
        plan_id = activity["daily_plan"]
        completed = await StudyActivity.count().where(
            (StudyActivity.daily_plan == plan_id) &
            (StudyActivity.is_completed == True)
        )
        total = await StudyActivity.count().where(StudyActivity.daily_plan == plan_id)
        await DailyStudyPlan.update({
            "completed_count": completed,
            "is_completed": completed >= total,
        }).where(DailyStudyPlan.id == plan_id)

        return {
            "activity_id": str(activity_id),
            "band_score": feedback.get("band_score"),
            "feedback": feedback,
            "is_correct": feedback.get("is_correct"),
            "suggestions": feedback.get("suggestions", []),
        }

    def _format_daily_plan(self, plan: dict, activities: list) -> dict[str, Any]:
        return {
            "id": str(plan["id"]),
            "study_date": str(plan["study_date"]),
            "activities": [
                {
                    "id": str(a["id"]),
                    "section": a["section"],
                    "activity_type": a["activity_type"],
                    "title": a["title"],
                    "content": a.get("content", {}),
                    "difficulty_level": a.get("difficulty_level", 1),
                    "is_completed": a.get("is_completed", False),
                    "ai_feedback": a.get("ai_feedback", {}),
                    "band_score": a.get("band_score"),
                }
                for a in activities
            ],
            "completed_count": plan.get("completed_count", 0),
            "total_count": plan.get("total_count", 0),
            "is_completed": plan.get("is_completed", False),
            "ai_rationale": plan.get("ai_rationale", ""),
        }

    # ── Progress Tracking ─────────────────────────────────────────

    async def get_progress_overview(self, user_id: UUID) -> dict[str, Any]:
        """Get comprehensive progress overview."""
        user = await User.select().where(User.id == user_id).first()
        if not user:
            return {}

        # Score history
        snapshots = await ProgressSnapshot.select().where(
            ProgressSnapshot.user == user_id
        ).order_by(ProgressSnapshot.snapshot_date)

        score_history = [
            {
                "date": str(s["snapshot_date"]),
                "overall_band": s.get("overall_band"),
                "listening": s.get("listening_band"),
                "reading": s.get("reading_band"),
                "writing": s.get("writing_band"),
                "speaking": s.get("speaking_band"),
            }
            for s in snapshots
        ]

        # Recent test results
        recent_attempts = await ExamAttempt.select().where(
            (ExamAttempt.user == user_id) & (ExamAttempt.status == "completed")
        ).order_by(ExamAttempt.created_at, ascending=False).limit(10)

        recent_scores = [
            {
                "date": str(a.get("created_at", "")),
                "band_score": a.get("band_score"),
                "section": a.get("feedback", {}).get("section", ""),
            }
            for a in recent_attempts
        ]

        # Stats
        total_tests = await ExamAttempt.count().where(
            (ExamAttempt.user == user_id) & (ExamAttempt.status == "completed")
        )
        total_activities = await StudyActivity.count().where(
            (StudyActivity.user == user_id) & (StudyActivity.is_completed == True)
        )

        skill_profile = _normalize_skill_profile(user.get("skill_profile", {}))
        section_scores = _normalize_section_scores(user.get("section_scores", {}))
        exam_date = user.get("exam_date")
        days_until_exam = (exam_date - date.today()).days if exam_date else None

        return {
            "current_estimated_band": user.get("current_estimated_band"),
            "target_band_score": user.get("target_band_score"),
            "days_until_exam": days_until_exam,
            "total_tests_taken": total_tests,
            "total_activities_completed": total_activities,
            "section_scores": section_scores,
            "skill_profile": skill_profile,
            "recent_scores": _normalize_json_list(recent_scores),
            "score_history": _normalize_json_list(score_history),
            "strengths": skill_profile.get("strengths", []),
            "weaknesses": skill_profile.get("weaknesses", []),
            "recommendations": skill_profile.get("focus_areas", []),
        }

    async def get_test_history(self, user_id: UUID, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        """Get paginated test history."""
        total = await ExamAttempt.count().where(
            (ExamAttempt.user == user_id) & (ExamAttempt.status == "completed")
        )

        attempts = await ExamAttempt.select().where(
            (ExamAttempt.user == user_id) & (ExamAttempt.status == "completed")
        ).order_by(ExamAttempt.created_at, ascending=False).limit(limit).offset(offset)

        items = [
            {
                "id": str(a["id"]),
                "date": str(a.get("created_at", "")),
                "band_score": a.get("band_score"),
                "section": a.get("feedback", {}).get("section", ""),
                "feedback": a.get("feedback", {}),
                "ai_analysis": a.get("ai_analysis", {}),
            }
            for a in attempts
        ]

        return {"items": items, "total": total}

    async def save_test_result_snapshot(
        self,
        user_id: UUID,
        section: str | None,
        band_score: float,
        section_scores: dict[str, float] | None = None,
    ) -> None:
        """Save a progress snapshot after completing a test."""
        user = await User.select().where(User.id == user_id).first()
        if not user:
            return

        current_scores = _normalize_section_scores(user.get("section_scores", {}))
        if section and band_score:
            current_scores[section] = band_score

        if section_scores:
            current_scores.update(section_scores)

        overall = (
            sum(current_scores.values()) / len(current_scores)
            if current_scores else band_score
        )
        # Round to nearest 0.5
        overall = round(overall * 2) / 2

        # Update user
        await User.update({
            "current_estimated_band": overall,
            "section_scores": current_scores,
        }).where(User.id == user_id)

        # Save snapshot
        snap = ProgressSnapshot(
            id=uuid.uuid4(),
            user=user_id,
            snapshot_date=date.today(),
            overall_band=overall,
            listening_band=current_scores.get("listening"),
            reading_band=current_scores.get("reading"),
            writing_band=current_scores.get("writing"),
            speaking_band=current_scores.get("speaking"),
        )
        await snap.save()


# Singleton
ielts_service = IELTSService()
