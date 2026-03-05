"""Exam service for exam-related operations."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from app.core.exceptions import NotFoundException, BadRequestException
from app.core.logging import logger
from app.db.tables import Exam, ExamAttempt, Question, Answer
from app.schemas.exam import ExamCreate, ExamUpdate, AnswerSubmit
from app.services.base import BaseService


class ExamService(BaseService[Exam]):
    """Service for exam operations."""

    model = Exam

    async def create_exam(self, data: ExamCreate) -> Exam:
        """Create a new exam."""
        exam_data = {
            "id": uuid4(),
            **data.model_dump(),
        }

        exam = Exam(**exam_data)
        await exam.save()
        logger.info(f"Created exam: {data.title}")
        return exam

    async def update_exam(self, exam_id: UUID, data: ExamUpdate) -> Exam:
        """Update exam information."""
        exam = await self.get_by_id(exam_id)
        if not exam:
            raise NotFoundException(detail="Exam not found")

        update_data = data.model_dump(exclude_unset=True, exclude_none=True)
        
        if update_data:
            await Exam.update(update_data).where(Exam.id == exam_id)
        
        return await self.get_by_id(exam_id)

    async def get_exams_by_type(
        self,
        exam_type: str,
        section: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Exam]:
        """Get exams by type and optionally section."""
        query = Exam.select().where(
            (Exam.exam_type == exam_type) & (Exam.is_active == True)
        )
        
        if section:
            query = query.where(Exam.section == section)
        
        return await query.offset(offset).limit(limit)

    async def get_questions(self, exam_id: UUID) -> list[Question]:
        """Get all questions for an exam."""
        return await Question.select().where(Question.exam == exam_id).order_by(
            Question.question_number
        )

    async def start_attempt(self, user_id: UUID, exam_id: UUID) -> ExamAttempt:
        """Start a new exam attempt."""
        exam = await self.get_by_id(exam_id)
        if not exam:
            raise NotFoundException(detail="Exam not found")

        # Check for existing in-progress attempt
        existing = await ExamAttempt.select().where(
            (ExamAttempt.user == user_id)
            & (ExamAttempt.exam == exam_id)
            & (ExamAttempt.status == "in_progress")
        ).first()

        if existing:
            return existing

        attempt_data = {
            "id": uuid4(),
            "user": user_id,
            "exam": exam_id,
            "status": "in_progress",
            "max_score": exam["total_questions"],
        }

        attempt = ExamAttempt(**attempt_data)
        await attempt.save()
        logger.info(f"Started exam attempt for user {user_id} on exam {exam_id}")
        return attempt

    async def submit_answer(
        self,
        attempt_id: UUID,
        user_id: UUID,
        data: AnswerSubmit,
    ) -> Answer:
        """Submit an answer for a question."""
        # Verify attempt belongs to user and is in progress
        attempt = await ExamAttempt.select().where(
            (ExamAttempt.id == attempt_id)
            & (ExamAttempt.user == user_id)
            & (ExamAttempt.status == "in_progress")
        ).first()

        if not attempt:
            raise BadRequestException(detail="Invalid or completed attempt")

        # Get question
        question = await Question.select().where(Question.id == data.question_id).first()
        if not question:
            raise NotFoundException(detail="Question not found")

        # Check if already answered
        existing = await Answer.select().where(
            (Answer.attempt == attempt_id) & (Answer.question == data.question_id)
        ).first()

        if existing:
            # Update existing answer
            await Answer.update({
                "user_answer": data.user_answer,
                "audio_response_url": data.audio_response_url,
                "time_spent_seconds": data.time_spent_seconds,
            }).where(Answer.id == existing["id"])
            return await Answer.select().where(Answer.id == existing["id"]).first()

        # Evaluate answer (simple comparison, AI evaluation can be added)
        is_correct = self._evaluate_answer(data.user_answer, question["correct_answer"])
        points = question["points"] if is_correct else 0.0

        answer_data = {
            "id": uuid4(),
            "attempt": attempt_id,
            "question": data.question_id,
            "user_answer": data.user_answer,
            "audio_response_url": data.audio_response_url,
            "is_correct": is_correct,
            "points_earned": points,
            "time_spent_seconds": data.time_spent_seconds,
        }

        answer = Answer(**answer_data)
        await answer.save()
        return answer

    def _evaluate_answer(self, user_answer: Any, correct_answer: Any) -> bool:
        """Evaluate if the answer is correct."""
        if isinstance(correct_answer, str) and isinstance(user_answer, str):
            return user_answer.lower().strip() == correct_answer.lower().strip()
        return user_answer == correct_answer

    async def complete_attempt(self, attempt_id: UUID, user_id: UUID) -> ExamAttempt:
        """Complete an exam attempt and calculate score."""
        attempt = await ExamAttempt.select().where(
            (ExamAttempt.id == attempt_id) & (ExamAttempt.user == user_id)
        ).first()

        if not attempt:
            raise NotFoundException(detail="Attempt not found")

        if attempt["status"] == "completed":
            return attempt

        # Calculate score
        answers = await Answer.select().where(Answer.attempt == attempt_id)
        total_points = sum(a["points_earned"] for a in answers)
        total_time = sum(a["time_spent_seconds"] for a in answers)

        # Calculate band score (IELTS style)
        max_score = attempt["max_score"] or 1
        percentage = (total_points / max_score) * 100
        band_score = self._calculate_band_score(percentage)

        await ExamAttempt.update({
            "status": "completed",
            "completed_at": datetime.now(),
            "score": total_points,
            "band_score": band_score,
            "time_spent_seconds": total_time,
        }).where(ExamAttempt.id == attempt_id)

        logger.info(f"Completed exam attempt {attempt_id} with score {total_points}")
        return await ExamAttempt.select().where(ExamAttempt.id == attempt_id).first()

    def _calculate_band_score(self, percentage: float) -> float:
        """Calculate IELTS-style band score from percentage."""
        if percentage >= 90:
            return 9.0
        elif percentage >= 80:
            return 8.0 + (percentage - 80) / 10 * 0.5
        elif percentage >= 70:
            return 7.0 + (percentage - 70) / 10 * 0.5
        elif percentage >= 60:
            return 6.0 + (percentage - 60) / 10 * 0.5
        elif percentage >= 50:
            return 5.0 + (percentage - 50) / 10 * 0.5
        elif percentage >= 40:
            return 4.0 + (percentage - 40) / 10 * 0.5
        else:
            return max(1.0, percentage / 10)

    async def get_user_attempts(
        self,
        user_id: UUID,
        exam_type: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[ExamAttempt]:
        """Get user's exam attempts."""
        query = ExamAttempt.select().where(ExamAttempt.user == user_id)
        
        # TODO: Join with Exam to filter by exam_type
        
        return await query.order_by(ExamAttempt.created_at, ascending=False).offset(offset).limit(limit)


# Singleton instance
exam_service = ExamService()
