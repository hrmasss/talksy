"""Script to create database tables."""

import asyncio

from app.db.tables import (
    Answer,
    ConversationMessage,
    ConversationSession,
    DailyStudyPlan,
    Exam,
    ExamAttempt,
    PlacementResponse,
    PlacementTest,
    ProgressSnapshot,
    Question,
    StudyActivity,
    User,
)


async def create_tables():
    """Create all database tables."""
    tables = [
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
    ]
    
    for table in tables:
        await table.create_table(if_not_exists=True)
        print(f"Created table: {table._meta.tablename}")
    
    print("\nAll tables created successfully!")


if __name__ == "__main__":
    asyncio.run(create_tables())
