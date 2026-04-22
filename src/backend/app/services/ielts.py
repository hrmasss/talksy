"""Service layer for the IELTS preparation platform.

Bridges placement tests, daily study, mock tests, and progress tracking
with the database and AI agents.
"""

from __future__ import annotations

import base64
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
from app.services.speech import speech_to_text, text_to_speech
from langchain_core.messages import HumanMessage

from ..agents.common.llm import get_llm
from ..agents.daily_study.models import (
    DailyStudyPlanModel,
    StudyActivityCompletionModel,
)
from ..agents.daily_study.prompts import (
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


def _coerce_daily_content(value: Any) -> dict[str, Any]:
    """Return a safe daily-study content object from DB JSON or stringified JSON."""
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
            return {"material": parsed}
        except json.JSONDecodeError:
            return {"material": value}

    if isinstance(value, dict):
        return dict(value)

    if isinstance(value, list):
        return {"material": value}

    return {}


def _normalize_daily_string_list(value: Any) -> list[str]:
    """Return a clean string list from a daily-study field."""
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []

    if not isinstance(value, list):
        return []

    return [str(item).strip() for item in value if str(item).strip()]


def _normalize_daily_questions(
    questions: Any,
    options: Any,
) -> list[dict[str, Any]]:
    """Coerce old daily-study question payloads to a stable question list."""
    option_entries = list(options.items()) if isinstance(options, dict) else []
    normalized: list[dict[str, Any]] = []

    if isinstance(questions, list):
        for index, item in enumerate(questions):
            entry: dict[str, Any] = {}
            if isinstance(item, dict):
                prompt = item.get("prompt") or item.get("question") or item.get("text")
                if isinstance(prompt, str) and prompt.strip():
                    entry["prompt"] = prompt.strip()
                if isinstance(item.get("options"), list):
                    entry["options"] = [
                        str(choice).strip()
                        for choice in item["options"]
                        if str(choice).strip()
                    ]
            elif isinstance(item, str) and item.strip():
                entry["prompt"] = item.strip()

            if "prompt" not in entry:
                continue

            if "options" not in entry and index < len(option_entries):
                _, option_value = option_entries[index]
                if isinstance(option_value, list):
                    entry["options"] = [
                        str(choice).strip()
                        for choice in option_value
                        if str(choice).strip()
                    ]

            normalized.append(entry)

    return normalized


def _extract_example_text(value: str) -> str:
    """Pull the example utterance from placeholder copy when possible."""
    text = value.strip()
    if not text:
        return ""

    quoted = re.findall(r"[\"']([^\"']{8,})[\"']", text)
    if quoted:
        return quoted[0].strip()

    eg_match = re.search(r"\be\.g\.,?\s*(.+)$", text, flags=re.IGNORECASE)
    if eg_match:
        return eg_match.group(1).strip(" .()")

    return text


def _extract_daily_listening_script(content: dict[str, Any]) -> str:
    """Choose the best available text source for listening TTS."""
    material = content.get("material")
    candidates: list[str] = []

    if isinstance(material, dict):
        for key in ("transcript", "audio_script", "script", "passage", "text", "prompt", "audio"):
            value = material.get(key)
            if isinstance(value, str) and value.strip():
                candidates.append(value.strip())
    elif isinstance(material, str) and material.strip():
        candidates.append(material.strip())

    for key in ("overview", "warm_up"):
        value = content.get(key)
        if isinstance(value, str) and value.strip():
            candidates.append(value.strip())

    for candidate in candidates:
        extracted = _extract_example_text(candidate)
        if extracted:
            return extracted[:1200]

    return ""


def _sanitize_daily_activity_content(section: str, raw_content: Any) -> dict[str, Any]:
    """Normalize old and new daily-study payloads and strip answer leakage."""
    content = _coerce_daily_content(raw_content)

    instructions = _normalize_daily_string_list(content.get("instructions"))
    if instructions:
        content["instructions"] = instructions

    checkpoints = _normalize_daily_string_list(content.get("checkpoints"))
    if checkpoints:
        content["checkpoints"] = checkpoints

    sentence_frames = _normalize_daily_string_list(content.get("sentence_frames"))
    if sentence_frames:
        content["sentence_frames"] = sentence_frames

    if "study_tip" not in content and isinstance(content.get("tips"), str):
        tip = content["tips"].strip()
        if tip:
            content["study_tip"] = tip

    content["questions"] = _normalize_daily_questions(
        content.get("questions"),
        content.get("options"),
    )

    hidden_keys = {
        "correct_answers",
        "answer_key",
        "answers",
        "expected_answer",
        "expected_answers",
        "model_answer",
        "sample_response",
        "solution",
        "solutions",
    }
    sanitized = {
        key: value
        for key, value in content.items()
        if key not in hidden_keys and key != "tips"
    }

    if section == "listening":
        material = sanitized.get("material")
        if isinstance(material, dict):
            sanitized["material"] = {
                key: value
                for key, value in material.items()
                if key != "transcript"
            }

    return sanitized


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


REQUIRED_DAILY_ACTIVITY_ORDER: list[dict[str, str]] = [
    {
        "section": "vocabulary",
        "activity_type": "vocabulary_practice",
        "title": "Vocabulary in Context",
    },
    {
        "section": "listening",
        "activity_type": "mini_listening",
        "title": "Targeted Listening Drill",
    },
    {
        "section": "reading",
        "activity_type": "reading_passage",
        "title": "Analytical Reading Passage",
    },
    {
        "section": "writing",
        "activity_type": "writing_task",
        "title": "Focused Writing Task",
    },
    {
        "section": "speaking",
        "activity_type": "speaking_prompt",
        "title": "Speaking Extension Prompt",
    },
]


def _default_activity_content(title: str, section: str) -> dict[str, Any]:
    """Fallback content when the LLM omits a structured activity payload."""
    return {
        "overview": f"This {section} activity helps you build confidence step by step.",
        "instructions": [
            "Read the task carefully.",
            "Complete it in simple English.",
            "Review your work and note one thing you learned.",
        ],
        "study_goal": f"Build stronger {section} foundations through short daily practice.",
        "material_title": title,
        "material": "Use this space to practise with short, simple answers.",
        "checkpoints": [
            "Use clear and simple ideas.",
            "Focus on understanding before speed.",
        ],
        "study_tip": "Keep your answer simple and accurate.",
        "next_step": "Repeat the activity once more tomorrow with one small improvement.",
    }


def _normalize_daily_activity_plan(
    activities_data: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return the fixed beginner-friendly daily study activity set."""
    normalized: list[dict[str, Any]] = []

    for index, required in enumerate(REQUIRED_DAILY_ACTIVITY_ORDER):
        generated = activities_data[index] if index < len(activities_data) else {}
        content = generated.get("content")
        if not isinstance(content, dict) or not content:
            content = _default_activity_content(required["title"], required["section"])

        difficulty_level = generated.get("difficulty_level", index + 1)
        try:
            difficulty_level = int(difficulty_level)
        except (TypeError, ValueError):
            difficulty_level = min(index + 1, 3)

        normalized.append({
            "section": required["section"],
            "activity_type": required["activity_type"],
            "title": required["title"],
            "difficulty_level": max(1, min(difficulty_level, 5)),
            "content": content,
        })

    return normalized


class IELTSService:
    """Manages the full IELTS preparation lifecycle."""

    async def _resume_placement_test(
        self, thread_id: str
    ) -> dict[str, Any] | None:
        """Return formatted placement state for an existing thread."""
        if not thread_id:
            return None
        state = await get_placement_state(thread_id)
        if not state:
            return None
        if state.get("status") == "completed":
            await self._save_placement_results(thread_id, state)
            return self._format_placement_result(state, thread_id)
        return await self._format_placement_question(state, thread_id)

    async def get_active_placement_test(self, user_id: UUID) -> dict[str, Any] | None:
        """Return the most recent in-progress placement test for a user, if any."""
        pt = await (
            PlacementTest.select()
            .where((PlacementTest.user == user_id) & (PlacementTest.status == "in_progress"))
            .order_by(PlacementTest.started_at, ascending=False)
            .first()
        )
        if not pt:
            return None
        return await self._resume_placement_test(pt.get("thread_id") or "")


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
        active = await self.get_active_placement_test(user_id)
        if active:
            return active

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

        return await self._format_placement_question(result, thread_id)

    async def submit_placement_answer(
        self,
        thread_id: str,
        answer: str | None = None,
        audio_base64: str | None = None,
    ) -> dict[str, Any]:
        """Submit an answer during the placement test."""
        final_answer = answer or ""

        # If audio is provided, use STT
        if audio_base64:
            try:
                audio_bytes = base64.b64decode(audio_base64)
                transcription = await speech_to_text(audio_bytes)
                final_answer = transcription
                logger.info("Transcribed placement answer: {}", final_answer)
            except Exception as exc:
                logger.error("STT failed for placement: {}", exc)
                # Fallback to provided answer if any

        result = await submit_placement_answer(final_answer, thread_id=thread_id)

        status = result.get("status", "in_progress")

        if status == "completed":
            # Save results to DB and update user profile
            await self._save_placement_results(thread_id, result)
            return self._format_placement_result(result, thread_id)

        return await self._format_placement_question(result, thread_id)

    async def get_placement_status(self, thread_id: str) -> dict[str, Any]:
        """Get current placement test status."""
        state = await get_placement_state(thread_id)
        if not state:
            return {"error": "not_found"}

        if state.get("status") == "completed":
            return self._format_placement_result(state, thread_id)
        return await self._format_placement_question(state, thread_id)

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

    async def _format_placement_question(self, state: dict[str, Any], thread_id: str) -> dict[str, Any]:
        section = state.get("current_section", "listening")
        question_text = state.get("current_question", "")
        audio_url = None

        # Generate audio for listening section
        if section == "listening" and question_text:
            try:
                # Use first sentence if it's very long for the voice
                tts_text = question_text
                # Remove [Listening Scenario] tag for cleaner audio
                tts_text = tts_text.replace("[Listening Scenario]", "").strip()

                audio_bytes = await text_to_speech(tts_text)
                filename = f"placement_{thread_id}_{state.get('question_number', 0)}.wav"
                
                # Check if static/audio exists, create if not
                audio_root = settings.static_dir / "audio"
                audio_root.mkdir(parents=True, exist_ok=True)
                
                audio_path = audio_root / filename
                audio_path.write_bytes(audio_bytes)
                audio_url = f"/static/audio/{filename}"
                logger.info("Generated TTS for placement listening: {}", audio_url)
            except Exception as exc:
                logger.error("Failed to generate placement audio: {}", exc)

        return {
            "thread_id": thread_id,
            "status": state.get("status", "in_progress"),
            "section": section,
            "question_index": state.get("question_number", 0),
            "total_questions": state.get("total_questions", TOTAL_PLACEMENT_QUESTIONS),
            "question_text": question_text,
            "question_type": state.get("current_question_type", "multiple_choice"),
            "options": state.get("current_options", []),
            "time_limit_seconds": None,
            "audio_url": audio_url,
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

    async def get_today_plan(self, user_id: UUID) -> dict[str, Any]:
        """Return today's study plan without generating one if it doesn't exist."""
        today = date.today()
        existing = await DailyStudyPlan.select().where(
            (DailyStudyPlan.user == user_id) &
            (DailyStudyPlan.study_date == today)
        ).first()
        if not existing:
            return {"error": "no_plan_today"}
        activities = await StudyActivity.select().where(
            StudyActivity.daily_plan == existing["id"]
        ).order_by(StudyActivity.created_at)
        return await self._format_daily_plan(existing, activities, include_activity_media=True)

    async def get_or_generate_daily_plan(self, user_id: UUID) -> dict[str, Any]:
        """Get today's study plan, generating one if it doesn't exist (idempotent per day)."""
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
            return await self._format_daily_plan(existing, activities, include_activity_media=True)

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
        return await self._format_daily_plan(plan, activities, include_activity_media=True)

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
            items.append(await self._format_daily_plan(plan, activities, include_activity_media=False))

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

        llm = get_llm(model=settings.groq_model, temperature=0.7)
        try:
            structured_llm = llm.with_structured_output(DailyStudyPlanModel)
            plan_output: DailyStudyPlanModel = await structured_llm.ainvoke(
                [HumanMessage(content=prompt)]
            )
        except Exception as exc:
            logger.opt(exception=exc).error(
                "Daily study plan LLM call failed (user_id={})",
                str(user_id),
            )
            return {"error": "daily_plan_generation_failed"}

        activities_data = _normalize_daily_activity_plan(
            [a.model_dump() for a in plan_output.activities]
        )

        # Save plan to DB
        plan_id = uuid.uuid4()
        plan = DailyStudyPlan(
            id=plan_id,
            user=user_id,
            study_date=study_date,
            activities=[a.get("title", "") for a in activities_data],
            total_count=len(activities_data),
            ai_rationale=plan_output.rationale,
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
        return await self._format_daily_plan(result, acts, include_activity_media=True)

    async def submit_activity_response(
        self,
        activity_id: UUID,
        user_response: str,
        time_spent_seconds: int = 0,
    ) -> dict[str, Any]:
        """Submit a response to a study activity and mark it as completed."""
        activity = await StudyActivity.select().where(StudyActivity.id == activity_id).first()
        if not activity:
            return {"error": "activity_not_found"}

        content = activity.get("content", {})
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                content = {}

        next_steps: list[str] = []
        if isinstance(content, dict):
            for key in ("next_step", "study_tip"):
                value = content.get(key)
                if isinstance(value, str) and value.strip():
                    next_steps.append(value.strip())

            checkpoints = content.get("checkpoints")
            if isinstance(checkpoints, list):
                for item in checkpoints[:2]:
                    if isinstance(item, str) and item.strip():
                        next_steps.append(item.strip())

        section_label = str(activity.get("section", "study")).replace("_", " ")
        completion = StudyActivityCompletionModel(
            message=f"Your {section_label} practice has been saved and marked as complete.",
            next_steps=next_steps[:3],
            saved_response=True,
        ).model_dump()

        # Save to DB
        await StudyActivity.update({
            "is_completed": True,
            "user_response": {"text": user_response},
            "ai_feedback": completion,
            "band_score": None,
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
            "message": completion.get("message"),
            "next_steps": completion.get("next_steps", []),
            "saved_response": completion.get("saved_response", True),
        }

    async def _ensure_daily_activity_audio_url(
        self,
        *,
        activity_id: UUID,
        section: str,
        raw_content: Any,
    ) -> str | None:
        """Return a cached audio URL for listening activities when possible."""
        if section != "listening":
            return None

        content = _coerce_daily_content(raw_content)
        script = _extract_daily_listening_script(content)
        if not script:
            return None

        filename = f"daily_study_{activity_id}.wav"
        audio_root = settings.static_dir / "audio"
        audio_root.mkdir(parents=True, exist_ok=True)
        audio_path = audio_root / filename

        if not audio_path.exists():
            try:
                audio_bytes = await text_to_speech(script)
                audio_path.write_bytes(audio_bytes)
                logger.info("Generated TTS for daily study listening activity {}", activity_id)
            except Exception as exc:
                logger.warning(
                    "Failed to generate daily-study listening audio for {}: {}",
                    activity_id,
                    exc,
                )
                return None

        return f"/static/audio/{filename}"

    async def _format_daily_plan(
        self,
        plan: dict,
        activities: list,
        *,
        include_activity_media: bool,
    ) -> dict[str, Any]:
        formatted_activities: list[dict[str, Any]] = []
        for activity in activities:
            section = str(activity.get("section", "vocabulary"))
            raw_content = activity.get("content", {})
            formatted = {
                "id": str(activity["id"]),
                "section": section,
                "activity_type": activity["activity_type"],
                "title": activity["title"],
                "content": _sanitize_daily_activity_content(section, raw_content),
                "difficulty_level": activity.get("difficulty_level", 1),
                "is_completed": activity.get("is_completed", False),
                "ai_feedback": activity.get("ai_feedback", {}),
                "band_score": activity.get("band_score"),
            }
            if include_activity_media:
                formatted["audio_url"] = await self._ensure_daily_activity_audio_url(
                    activity_id=activity["id"],
                    section=section,
                    raw_content=raw_content,
                )
            formatted_activities.append(formatted)

        return {
            "id": str(plan["id"]),
            "study_date": str(plan["study_date"]),
            "activities": formatted_activities,
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
