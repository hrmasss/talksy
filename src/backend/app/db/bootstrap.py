"""Database bootstrap helpers."""

from app.core.logging import logger
from app.db.tables import (
    Answer,
    ConversationMessage,
    ConversationSession,
    DailyStudyPlan,
    Exam,
    ExamAttempt,
    MockExamSession,
    PlacementResponse,
    PlacementTest,
    ProgressSnapshot,
    Question,
    StudyActivity,
    User,
)


TABLES = [
    User,
    Exam,
    Question,
    ExamAttempt,
    Answer,
    ConversationSession,
    ConversationMessage,
    PlacementTest,
    PlacementResponse,
    DailyStudyPlan,
    StudyActivity,
    ProgressSnapshot,
    MockExamSession,
]


async def ensure_tables_exist() -> None:
    """Create all application tables if they don't already exist."""
    for table in TABLES:
        await table.create_table(if_not_exists=True)

    logger.info("Database tables verified")