"""AI-powered practice session endpoints.

These routes use the LangGraph agents for interactive IELTS practice,
as opposed to the DB-backed ExamController for static exam CRUD.
"""

from litestar import Controller, get, post
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED

from app.schemas.practice import (
    TopicGenerateRequest,
    TopicGenerateResponse,
    PracticeExamStartRequest,
    PracticeExamAnswerRequest,
    PracticeExamStateRequest,
    PracticeExamQuestionResponse,
    PracticeExamReportResponse,
)
from app.agents.services.topic_service import topic_generator_service
from app.agents.services.exam_service import exam_service as practice_exam_service


class PracticeController(Controller):
    """AI-powered IELTS practice sessions."""

    path = "/practice"
    tags = ["Practice"]

    # ── Topic Generation ──────────────────────────────────────

    @post(
        "/topics",
        summary="Generate Practice Topics",
        description=(
            "Use the AI topic-generator to assess the user's level and "
            "produce tailored IELTS practice topics across all four sections."
        ),
        status_code=HTTP_201_CREATED,
    )
    async def generate_topics(self, data: TopicGenerateRequest) -> TopicGenerateResponse:
        """Generate personalised IELTS practice topics."""
        # TODO: Get user_id from authentication
        from uuid import uuid4
        user_id = str(uuid4())

        result = await topic_generator_service.generate_topics(
            user_id=user_id,
            target_exam=data.target_exam,
            target_score=data.target_score,
            current_level_description=data.current_level_description,
            section_focus=data.section_focus,
            preferences=data.preferences,
        )

        return TopicGenerateResponse(**result)

    # ── Practice Exam Sessions ────────────────────────────────

    @post(
        "/exams/start",
        summary="Start Practice Exam",
        description=(
            "Start an AI-powered, interactive IELTS practice exam. "
            "Returns the first question. Use the thread_id in subsequent "
            "requests to continue the session."
        ),
        status_code=HTTP_201_CREATED,
    )
    async def start_practice_exam(
        self, data: PracticeExamStartRequest
    ) -> PracticeExamQuestionResponse:
        """Kick off a new IELTS practice exam session."""
        # TODO: Get user_id from authentication
        from uuid import uuid4
        user_id = str(uuid4())

        result = await practice_exam_service.create_exam_session(
            user_id=user_id,
            exam_type=data.exam_type,
            section=data.section,
            difficulty=data.difficulty,
            target_band=data.target_band,
            topic=data.topic,
        )

        return PracticeExamQuestionResponse(**result)

    @post(
        "/exams/answer",
        summary="Submit Answer",
        description=(
            "Submit an answer for the current question. Returns either "
            "the next question or the final report if the exam is done."
        ),
        status_code=HTTP_200_OK,
    )
    async def submit_practice_answer(
        self, data: PracticeExamAnswerRequest
    ) -> PracticeExamQuestionResponse | PracticeExamReportResponse:
        """Submit an answer and advance the exam."""
        result = await practice_exam_service.answer_question(
            thread_id=data.thread_id,
            answer=data.answer,
        )

        if result.get("status") == "completed":
            return PracticeExamReportResponse(**result)
        return PracticeExamQuestionResponse(**result)

    @get(
        "/exams/state",
        summary="Get Exam State",
        description="Retrieve the current state of a practice exam session.",
        status_code=HTTP_200_OK,
    )
    async def get_practice_exam_state(
        self, thread_id: str
    ) -> PracticeExamQuestionResponse | PracticeExamReportResponse:
        """Get current session state."""
        result = await practice_exam_service.get_session_state(thread_id=thread_id)

        if result.get("error"):
            from litestar.exceptions import NotFoundException
            raise NotFoundException(detail="Practice session not found")

        if result.get("status") == "completed":
            return PracticeExamReportResponse(**result)
        return PracticeExamQuestionResponse(**result)
