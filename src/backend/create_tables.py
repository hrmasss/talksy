"""Script to create database tables."""

import asyncio
from app.db.tables import (
    User,
    Exam,
    Question,
    ExamAttempt,
    Answer,
    ConversationSession,
    ConversationMessage,
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
    ]
    
    for table in tables:
        await table.create_table(if_not_exists=True)
        print(f"Created table: {table._meta.tablename}")
    
    print("\nAll tables created successfully!")


if __name__ == "__main__":
    asyncio.run(create_tables())
