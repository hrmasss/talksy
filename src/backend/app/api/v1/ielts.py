"""IELTS preparation platform API endpoints.

Provides onboarding (placement test), daily study plans, mock tests,
and progress tracking for the IELTS preparation system.
"""

from uuid import UUID

from app.schemas.ielts import (
    DailyStudyPlanResponse,
    DailyStudyHistoryResponse,
    IELTSProfileResponse,
    IELTSProfileUpdate,
    MockExamSessionListResponse,
    MockExamSessionResponse,
    MockTestAnswerRequest,
    MockTestQuestionResponse,
    MockTestReportResponse,
    MockTestStartRequest,
    PlacementAnswerRequest,
    PlacementQuestionResponse,
    PlacementResultResponse,
    PlacementStartRequest,
    ProgressOverviewResponse,
    StudyActivityFeedbackResponse,
    StudyActivitySubmitRequest,
    TestHistoryResponse,
)
from app.core.exceptions import AIServiceException
from app.core.logging import logger
from app.services.ielts import ielts_service
from litestar import Controller, get, post, put
from litestar.background_tasks import BackgroundTask
from litestar.exceptions import NotFoundException
from litestar.response import Response
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED


def _normalize_mock_question_text(question: object) -> str:
    """Coerce nullable question payloads to a clean display string."""
    if isinstance(question, dict):
        value = question.get("text")
    else:
        value = question

    if value is None:
        return ""

    text = str(value).strip()
    return "" if text.lower() == "none" else text


def _normalize_mock_question_type(question: object) -> str:
    """Extract the question type from a mock-test payload."""
    if isinstance(question, dict):
        value = question.get("type")
        if isinstance(value, str) and value.strip():
            return value
    return "discussion"


def _normalize_mock_question_passage(question: object) -> str | None:
    """Extract optional support material from a mock-test payload."""
    if isinstance(question, dict):
        value = question.get("passage")
        if isinstance(value, str):
            text = value.strip()
            if text and text.lower() != "none":
                return text
    return None


async def _store_exam_result_background(
    *,
    thread_id: str,
    section: str | None,
    overall_band: float | None,
    strengths: list[str] | None,
    weaknesses: list[str] | None,
    recommendations: list[str] | None,
    report_md: str | None,
) -> None:
    if not section or overall_band is None:
        return

    from app.db.tables import MockExamSession
    from app.memory.service import memory_service
    from app.services.ai import ai_service

    session = await (
        MockExamSession.select(
            MockExamSession.user,
            MockExamSession.difficulty,
            MockExamSession.target_band,
            MockExamSession.total_questions,
        )
        .where(MockExamSession.thread_id == thread_id)
        .first()
    )
    if not session:
        return

    user_id = str(session["user"])
    try:
        summary_for_memory = await ai_service.summarize_exam_result(
            section=section,
            overall_band=overall_band,
            strengths=strengths or [],
            weaknesses=weaknesses or [],
            recommendations=recommendations or [],
            report_markdown=report_md,
        )

        await memory_service.store_exam_result(
            user_id=user_id,
            section=section,
            band_score=overall_band,
            strengths=strengths or [],
            weaknesses=weaknesses or [],
            recommendations=recommendations or [],
            report_summary=summary_for_memory,
            extra_metadata={
                "difficulty": session.get("difficulty"),
                "target_band": session.get("target_band"),
                "total_questions": session.get("total_questions"),
                "thread_id": thread_id,
            },
        )
    except Exception as exc:
        logger.opt(exception=exc).warning("Background memory store failed")


class IELTSController(Controller):
    """IELTS preparation platform endpoints."""

    path = "/ielts"
    tags = ["IELTS"]

    # ── Profile ───────────────────────────────────────────────

    @get(
        "/profile/{user_id:uuid}",
        summary="Get IELTS Profile",
        description="Get the user's IELTS-specific profile including band scores, "
                    "skill profile, and onboarding status.",
        status_code=HTTP_200_OK,
    )
    async def get_profile(self, user_id: UUID) -> IELTSProfileResponse:
        result = await ielts_service.get_ielts_profile(user_id)
        if not result:
            raise NotFoundException(detail="User not found")
        return IELTSProfileResponse(**result)

    @put(
        "/profile/{user_id:uuid}",
        summary="Update IELTS Profile",
        description="Update target band score, exam date, and practice preferences.",
        status_code=HTTP_200_OK,
    )
    async def update_profile(self, user_id: UUID, data: IELTSProfileUpdate) -> IELTSProfileResponse:
        result = await ielts_service.update_ielts_profile(
            user_id, data.model_dump(exclude_unset=True)
        )
        return IELTSProfileResponse(**result)

    # ── Placement Test (Onboarding) ───────────────────────────

    @post(
        "/placement/start/{user_id:uuid}",
        summary="Start Placement Test",
        description="Start the initial diagnostic placement test. Required before "
                    "accessing the platform if onboarding_completed is false.",
        status_code=HTTP_201_CREATED,
    )
    async def start_placement(
        self, user_id: UUID, data: PlacementStartRequest
    ) -> PlacementQuestionResponse:
        result = await ielts_service.start_placement_test(
            user_id=user_id,
            target_band_score=data.target_band_score,
            exam_date=data.exam_date,
        )
        return PlacementQuestionResponse(**result)

    @post(
        "/placement/answer",
        summary="Submit Placement Answer",
        description="Submit an answer during the placement test. Returns the next "
                    "question or final results if the test is complete.",
        status_code=HTTP_200_OK,
    )
    async def submit_placement_answer(
        self, data: PlacementAnswerRequest
    ) -> PlacementQuestionResponse | PlacementResultResponse:
        result = await ielts_service.submit_placement_answer(
            thread_id=data.thread_id,
            answer=data.answer,
            audio_base64=data.audio_base64,
        )
        if result.get("status") == "completed":
            return PlacementResultResponse(**result)
        return PlacementQuestionResponse(**result)

    @get(
        "/placement/status",
        summary="Get Placement Status",
        description="Check current status of a placement test.",
        status_code=HTTP_200_OK,
    )
    async def get_placement_status(
        self, thread_id: str
    ) -> PlacementQuestionResponse | PlacementResultResponse:
        result = await ielts_service.get_placement_status(thread_id)
        if result.get("error"):
            raise NotFoundException(detail="Placement test not found")
        if result.get("status") == "completed":
            return PlacementResultResponse(**result)
        return PlacementQuestionResponse(**result)

    @get(
        "/placement/active/{user_id:uuid}",
        summary="Get Active Placement Test",
        description="Get the user's currently in-progress placement test, if any.",
        status_code=HTTP_200_OK,
    )
    async def get_active_placement_test(
        self, user_id: UUID
    ) -> PlacementQuestionResponse | PlacementResultResponse | None:
        result = await ielts_service.get_active_placement_test(user_id)
        if not result:
            return None
        if result.get("status") == "completed":
            return PlacementResultResponse(**result)
        return PlacementQuestionResponse(**result)

    # ── Mock Test ─────────────────────────────────────────────

    @post(
        "/mock-test/start/{user_id:uuid}",
        summary="Start Mock Test",
        description="Start an AI-powered IELTS mock test. Can be a full test "
                    "or section-specific. Difficulty adapts to user's level.",
        status_code=HTTP_201_CREATED,
    )
    async def start_mock_test(
        self, user_id: UUID, data: MockTestStartRequest
    ) -> MockTestQuestionResponse:
        from app.agents.services.exam_service import exam_service

        # Get user context for adaptive difficulty
        profile = await ielts_service.get_ielts_profile(user_id)
        current_band = profile.get("current_estimated_band") or 5.0
        target_band = profile.get("target_band_score") or 7.0

        # Map adaptive difficulty
        difficulty = data.difficulty
        if difficulty == "adaptive":
            if current_band < 5.0:
                difficulty = "beginner"
            elif current_band < 6.5:
                difficulty = "intermediate"
            elif current_band < 7.5:
                difficulty = "advanced"
            else:
                difficulty = "expert"

        section = data.section or "speaking"

        try:
            result = await exam_service.create_exam_session(
                user_id=str(user_id),
                exam_type="ielts_academic",
                section=section,
                difficulty=difficulty,
                target_band=target_band,
            )
        except Exception as exc:
            logger.opt(exception=exc).error(
                "Failed to start mock test for user={} section={}",
                user_id, section,
            )
            raise AIServiceException(detail=f"Failed to start mock test: {exc}")

        return MockTestQuestionResponse(
            thread_id=result["thread_id"],
            status=result.get("status", "awaiting_answer"),
            section=section,
            current_part=result.get("current_part", 1),
            question_index=result.get("question_index", 0),
            total_questions=result.get("total_questions", 0),
            question_text=_normalize_mock_question_text(result.get("current_question")),
            question_type=_normalize_mock_question_type(result.get("current_question")),
            options=[],
            passage=_normalize_mock_question_passage(result.get("current_question")),
            audio_url=result.get("audio_url"),
        )

    @post(
        "/mock-test/answer",
        summary="Submit Mock Test Answer",
        description="Submit an answer in a mock test session.",
        status_code=HTTP_200_OK,
    )
    async def submit_mock_answer(
        self, data: MockTestAnswerRequest
    ) -> MockTestQuestionResponse | MockTestReportResponse:
        from app.agents.services.exam_service import exam_service

        try:
            result = await exam_service.answer_question(
                thread_id=data.thread_id,
                answer=data.answer,
            )
        except Exception as exc:
            logger.opt(exception=exc).error(
                "Failed to process mock test answer for thread={}",
                data.thread_id,
            )
            raise AIServiceException(detail=f"Failed to process answer: {exc}")

        if result.get("status") == "completed":
            report = MockTestReportResponse(
                thread_id=data.thread_id,
                status="completed",
                section=result.get("section"),
                overall_band=result.get("overall_band"),
                section_scores=result.get("section_scores", []),
                evaluations=result.get("evaluations", []),
                strengths=result.get("strengths", []),
                weaknesses=result.get("weaknesses", []),
                recommendations=result.get("recommendations", []),
                final_report_markdown=result.get("final_report_markdown"),
            )
            background = BackgroundTask(
                _store_exam_result_background,
                thread_id=data.thread_id,
                section=report.section,
                overall_band=report.overall_band,
                strengths=report.strengths,
                weaknesses=report.weaknesses,
                recommendations=report.recommendations,
                report_md=report.final_report_markdown,
            )
            return Response(report, background=background, status_code=HTTP_200_OK)

        return MockTestQuestionResponse(
            thread_id=data.thread_id,
            status=result.get("status", "awaiting_answer"),
            section=result.get("section", ""),
            current_part=result.get("current_part", 1),
            question_index=result.get("question_index", 0),
            total_questions=result.get("total_questions", 0),
            question_text=_normalize_mock_question_text(result.get("current_question")),
            question_type=_normalize_mock_question_type(result.get("current_question")),
            options=[],
            passage=_normalize_mock_question_passage(result.get("current_question")),
            audio_url=result.get("audio_url"),
        )

    # ── Mock Exam Sessions ────────────────────────────────────

    @get(
        "/mock-test/sessions/{user_id:uuid}",
        summary="List Mock Test Sessions",
        description="Get all mock test sessions for a user (active and completed).",
        status_code=HTTP_200_OK,
    )
    async def list_sessions(
        self, user_id: UUID, status: str | None = None, limit: int = 20, offset: int = 0
    ) -> MockExamSessionListResponse:
        from app.agents.services.exam_service import exam_service

        sessions = await exam_service.list_sessions(
            str(user_id), status=status, limit=limit, offset=offset
        )
        return MockExamSessionListResponse(
            items=[MockExamSessionResponse(**s) for s in sessions]
        )

    @get(
        "/mock-test/active/{user_id:uuid}",
        summary="Get Active Mock Test",
        description="Get the user's currently in-progress mock test, if any.",
        status_code=HTTP_200_OK,
    )
    async def get_active_session(self, user_id: UUID) -> MockExamSessionResponse | None:
        from app.agents.services.exam_service import exam_service

        active = await exam_service.get_active_session(str(user_id))
        if not active:
            return None
        return MockExamSessionResponse(
            status="in_progress",
            difficulty=active.get("difficulty", "intermediate"),
            **{k: v for k, v in active.items() if k != "difficulty"},
        )

    @get(
        "/mock-test/resume",
        summary="Resume Mock Test",
        description="Get current state to resume an in-progress mock test.",
        status_code=HTTP_200_OK,
    )
    async def resume_mock_test(self, thread_id: str) -> MockTestQuestionResponse | MockTestReportResponse:
        from app.agents.services.exam_service import exam_service

        result = await exam_service.get_session_state(thread_id=thread_id)
        if result.get("error"):
            raise NotFoundException(detail="Mock test session not found")

        if result.get("status") == "completed":
            return MockTestReportResponse(
                thread_id=thread_id,
                status="completed",
                section=result.get("section"),
                overall_band=result.get("overall_band"),
                section_scores=result.get("section_scores", []),
                evaluations=result.get("evaluations", []),
                strengths=result.get("strengths", []),
                weaknesses=result.get("weaknesses", []),
                recommendations=result.get("recommendations", []),
                final_report_markdown=result.get("final_report_markdown"),
            )

        return MockTestQuestionResponse(
            thread_id=thread_id,
            status=result.get("status", "awaiting_answer"),
            section=result.get("section", ""),
            current_part=result.get("current_part", 1),
            question_index=result.get("question_index", 0),
            total_questions=result.get("total_questions", 0),
            question_text=_normalize_mock_question_text(result.get("current_question")),
            question_type=_normalize_mock_question_type(result.get("current_question")),
            options=[],
            passage=_normalize_mock_question_passage(result.get("current_question")),
            audio_url=result.get("audio_url"),
        )

    # ── Daily Study ───────────────────────────────────────────

    @get(
        "/study/daily/{user_id:uuid}",
        summary="Get Daily Study Plan",
        description="Get today's personalized study plan. Returns 404 if no plan "
                    "has been generated yet. Use the generate endpoint to create one.",
        status_code=HTTP_200_OK,
    )
    async def get_daily_plan(self, user_id: UUID) -> DailyStudyPlanResponse:
        result = await ielts_service.get_today_plan(user_id)
        if result.get("error"):
            if result["error"] == "no_plan_today":
                raise NotFoundException(detail="No study plan for today. Use the generate endpoint to create one.")
            raise NotFoundException(detail=result["error"])
        return DailyStudyPlanResponse(**result)

    @get(
        "/study/daily/history/{user_id:uuid}",
        summary="Get Recent Daily Study Plans",
        description="Get the most recent daily study plans (default last 7 days).",
        status_code=HTTP_200_OK,
    )
    async def get_daily_plan_history(self, user_id: UUID, days: int = 7) -> DailyStudyHistoryResponse:
        result = await ielts_service.list_recent_daily_plans(user_id, days=days)
        return DailyStudyHistoryResponse(**result)

    @get(
        "/study/daily/plan/{plan_id:uuid}",
        summary="Get Daily Study Plan By Id",
        description="Get a specific daily study plan with its activities.",
        status_code=HTTP_200_OK,
    )
    async def get_daily_plan_by_id(self, plan_id: UUID, user_id: UUID) -> DailyStudyPlanResponse:
        result = await ielts_service.get_daily_plan_by_id(user_id, plan_id)
        if result.get("error"):
            raise NotFoundException(detail="Daily plan not found")
        return DailyStudyPlanResponse(**result)

    @post(
        "/study/daily/generate/{user_id:uuid}",
        summary="Generate Daily Study Plan",
        description="Generate today's daily study plan if it doesn't exist.",
        status_code=HTTP_200_OK,
    )
    async def generate_daily_plan(self, user_id: UUID) -> DailyStudyPlanResponse:
        result = await ielts_service.get_or_generate_daily_plan(user_id)
        if result.get("error"):
            if result["error"] == "user_not_found":
                raise NotFoundException(detail="User not found")
            raise AIServiceException(detail=result["error"])
        return DailyStudyPlanResponse(**result)

    @post(
        "/study/submit",
        summary="Submit Activity Response",
        description="Submit a response to a study activity and receive AI feedback.",
        status_code=HTTP_200_OK,
    )
    async def submit_activity(
        self, data: StudyActivitySubmitRequest
    ) -> StudyActivityFeedbackResponse:
        result = await ielts_service.submit_activity_response(
            activity_id=data.activity_id,
            user_response=data.response,
            time_spent_seconds=data.time_spent_seconds,
        )
        if result.get("error"):
            raise NotFoundException(detail=result["error"])
        return StudyActivityFeedbackResponse(**result)

    # ── Progress Tracking ─────────────────────────────────────

    @get(
        "/progress/{user_id:uuid}",
        summary="Get Progress Overview",
        description="Get comprehensive progress including band score history, "
                    "section trends, strengths, weaknesses, and recommendations.",
        status_code=HTTP_200_OK,
    )
    async def get_progress(self, user_id: UUID) -> ProgressOverviewResponse:
        result = await ielts_service.get_progress_overview(user_id)
        if not result:
            raise NotFoundException(detail="User not found")
        return ProgressOverviewResponse(**result)

    @get(
        "/history/{user_id:uuid}",
        summary="Get Test History",
        description="Get paginated list of past test results.",
        status_code=HTTP_200_OK,
    )
    async def get_history(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> TestHistoryResponse:
        result = await ielts_service.get_test_history(user_id, limit, offset)
        return TestHistoryResponse(**result)
