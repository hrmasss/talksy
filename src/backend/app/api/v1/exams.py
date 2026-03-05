"""Exam API endpoints."""

from uuid import UUID

from litestar import Controller, get, post
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED

from app.schemas.exam import (
    ExamResponse,
    ExamListResponse,
    ExamAttemptCreate,
    ExamAttemptResponse,
    AnswerSubmit,
    AnswerResponse,
    QuestionResponse,
)
from app.services.exam import exam_service


class ExamController(Controller):
    """Exam management controller."""

    path = "/exams"
    tags = ["Exams"]

    @get(
        "/",
        summary="List Exams",
        description="Get list of available exams.",
        status_code=HTTP_200_OK,
    )
    async def list_exams(
        self,
        exam_type: str | None = None,
        section: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ExamListResponse:
        """List available exams."""
        filters = {}
        if exam_type:
            filters["exam_type"] = exam_type
        if section:
            filters["section"] = section
        filters["is_active"] = True

        offset = (page - 1) * page_size
        exams = await exam_service.get_all(offset=offset, limit=page_size, filters=filters)
        total = await exam_service.count(filters=filters)

        return ExamListResponse(
            items=[
                ExamResponse(
                    id=e["id"],
                    exam_type=e["exam_type"],
                    title=e["title"],
                    description=e.get("description"),
                    section=e["section"],
                    duration_minutes=e["duration_minutes"],
                    total_questions=e["total_questions"],
                    instructions=e.get("instructions"),
                    difficulty_level=e["difficulty_level"],
                    is_active=e["is_active"],
                    is_free=e["is_free"],
                    metadata=e.get("metadata", {}),
                    created_at=e["created_at"],
                    updated_at=e.get("updated_at"),
                )
                for e in exams
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    @get(
        "/{exam_id:uuid}",
        summary="Get Exam",
        description="Get exam details by ID.",
        status_code=HTTP_200_OK,
    )
    async def get_exam(self, exam_id: UUID) -> ExamResponse:
        """Get exam by ID."""
        exam = await exam_service.get_by_id(exam_id)
        if not exam:
            from litestar.exceptions import NotFoundException
            raise NotFoundException(detail="Exam not found")

        return ExamResponse(
            id=exam["id"],
            exam_type=exam["exam_type"],
            title=exam["title"],
            description=exam.get("description"),
            section=exam["section"],
            duration_minutes=exam["duration_minutes"],
            total_questions=exam["total_questions"],
            instructions=exam.get("instructions"),
            difficulty_level=exam["difficulty_level"],
            is_active=exam["is_active"],
            is_free=exam["is_free"],
            metadata=exam.get("metadata", {}),
            created_at=exam["created_at"],
            updated_at=exam.get("updated_at"),
        )

    @get(
        "/{exam_id:uuid}/questions",
        summary="Get Exam Questions",
        description="Get all questions for an exam.",
        status_code=HTTP_200_OK,
    )
    async def get_questions(self, exam_id: UUID) -> list[QuestionResponse]:
        """Get exam questions."""
        questions = await exam_service.get_questions(exam_id)
        return [
            QuestionResponse(
                id=q["id"],
                question_type=q["question_type"],
                question_number=q["question_number"],
                question_text=q["question_text"],
                question_audio_url=q.get("question_audio_url"),
                question_image_url=q.get("question_image_url"),
                options=q.get("options", []),
                points=q["points"],
                time_limit_seconds=q.get("time_limit_seconds"),
                hints=q.get("hints", []),
            )
            for q in questions
        ]

    @post(
        "/attempts",
        summary="Start Exam Attempt",
        description="Start a new exam attempt.",
        status_code=HTTP_201_CREATED,
    )
    async def start_attempt(self, data: ExamAttemptCreate) -> ExamAttemptResponse:
        """Start an exam attempt."""
        # TODO: Get user_id from authentication
        from uuid import uuid4
        user_id = uuid4()  # Placeholder
        
        attempt = await exam_service.start_attempt(user_id, data.exam_id)
        return ExamAttemptResponse(
            id=attempt["id"],
            user_id=attempt["user"],
            exam_id=attempt["exam"],
            started_at=attempt["started_at"],
            completed_at=attempt.get("completed_at"),
            time_spent_seconds=attempt["time_spent_seconds"],
            score=attempt.get("score"),
            max_score=attempt.get("max_score"),
            band_score=attempt.get("band_score"),
            status=attempt["status"],
            feedback=attempt.get("feedback", {}),
            ai_analysis=attempt.get("ai_analysis", {}),
        )

    @post(
        "/attempts/{attempt_id:uuid}/answers",
        summary="Submit Answer",
        description="Submit an answer for a question.",
        status_code=HTTP_201_CREATED,
    )
    async def submit_answer(
        self, attempt_id: UUID, data: AnswerSubmit
    ) -> AnswerResponse:
        """Submit an answer."""
        # TODO: Get user_id from authentication
        from uuid import uuid4
        user_id = uuid4()  # Placeholder
        
        answer = await exam_service.submit_answer(attempt_id, user_id, data)
        return AnswerResponse(
            id=answer["id"],
            question_id=answer["question"],
            user_answer=answer["user_answer"],
            is_correct=answer.get("is_correct"),
            points_earned=answer["points_earned"],
            ai_feedback=answer.get("ai_feedback", {}),
        )

    @post(
        "/attempts/{attempt_id:uuid}/complete",
        summary="Complete Exam",
        description="Complete an exam attempt and get results.",
        status_code=HTTP_200_OK,
    )
    async def complete_attempt(self, attempt_id: UUID) -> ExamAttemptResponse:
        """Complete an exam attempt."""
        # TODO: Get user_id from authentication
        from uuid import uuid4
        user_id = uuid4()  # Placeholder
        
        attempt = await exam_service.complete_attempt(attempt_id, user_id)
        return ExamAttemptResponse(
            id=attempt["id"],
            user_id=attempt["user"],
            exam_id=attempt["exam"],
            started_at=attempt["started_at"],
            completed_at=attempt.get("completed_at"),
            time_spent_seconds=attempt["time_spent_seconds"],
            score=attempt.get("score"),
            max_score=attempt.get("max_score"),
            band_score=attempt.get("band_score"),
            status=attempt["status"],
            feedback=attempt.get("feedback", {}),
            ai_analysis=attempt.get("ai_analysis", {}),
        )
