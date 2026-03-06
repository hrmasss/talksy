"""Conversation service for practice sessions."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from app.core.exceptions import NotFoundException
from app.core.logging import logger
from app.db.tables import ConversationMessage, ConversationSession
from app.schemas.conversation import ConversationMessage as ConversationMessageSchema
from app.schemas.conversation import ConversationStart
from app.services.ai import ai_service
from app.services.base import BaseService


class ConversationService(BaseService[ConversationSession]):
    """Service for conversation operations."""

    model = ConversationSession

    async def start_session(
        self, user_id: UUID, data: ConversationStart
    ) -> ConversationSession:
        """Start a new conversation session."""
        session_data = {
            "id": uuid4(),
            "user": user_id,
            "topic": data.topic,
            "scenario": data.scenario,
            "difficulty_level": data.difficulty_level,
        }

        session = ConversationSession(**session_data)
        await session.save()

        # Generate initial AI message
        initial_message = await self._generate_initial_message(session, data)
        
        logger.info(f"Started conversation session {session.id} for user {user_id}")
        return session

    async def _generate_initial_message(
        self, session: ConversationSession, data: ConversationStart
    ) -> ConversationMessage:
        """Generate initial AI message for the conversation."""
        prompt = f"""You are a friendly English conversation partner helping someone practice their English skills.
        
Topic: {data.topic}
Scenario: {data.scenario or 'General conversation practice'}
Difficulty Level: {data.difficulty_level}/5

Start a natural conversation about this topic. Be engaging, ask questions, and help them practice.
Keep your response appropriate for the difficulty level - simpler vocabulary and shorter sentences for lower levels.
"""

        ai_response = await ai_service.generate_response(prompt)
        
        message = ConversationMessage(
            id=uuid4(),
            session=session.id,
            role="assistant",
            content=ai_response,
        )
        await message.save()

        # Update message count
        await ConversationSession.update({"message_count": 1}).where(
            ConversationSession.id == session.id
        )

        return message

    async def send_message(
        self,
        session_id: UUID,
        user_id: UUID,
        data: ConversationMessageSchema,
    ) -> dict[str, Any]:
        """Send a message and get AI response."""
        # Verify session belongs to user
        session = await ConversationSession.select().where(
            (ConversationSession.id == session_id)
            & (ConversationSession.user == user_id)
        ).first()

        if not session:
            raise NotFoundException(detail="Session not found")

        if session["ended_at"]:
            raise NotFoundException(detail="Session has ended")

        # Save user message
        user_message = ConversationMessage(
            id=uuid4(),
            session=session_id,
            role="user",
            content=data.content,
            audio_url=data.audio_url,
        )
        await user_message.save()

        # Get conversation history
        history = await ConversationMessage.select().where(
            ConversationMessage.session == session_id
        ).order_by(ConversationMessage.timestamp)

        # Analyze user's message
        analysis = await ai_service.analyze_language(data.content)

        # Generate AI response
        ai_response = await self._generate_response(session, history, data.content)

        # Save AI message
        ai_message = ConversationMessage(
            id=uuid4(),
            session=session_id,
            role="assistant",
            content=ai_response["content"],
            analysis=analysis,
        )
        await ai_message.save()

        # Update session stats
        await ConversationSession.update({
            "message_count": session["message_count"] + 2,
        }).where(ConversationSession.id == session_id)

        return {
            "user_message": {
                "id": str(user_message.id),
                "content": data.content,
                "analysis": analysis,
            },
            "ai_message": {
                "id": str(ai_message.id),
                "content": ai_response["content"],
            },
            "suggestions": ai_response.get("suggestions", []),
            "vocabulary_tips": ai_response.get("vocabulary_tips", []),
            "grammar_notes": ai_response.get("grammar_notes", []),
        }

    async def _generate_response(
        self,
        session: dict,
        history: list[ConversationMessage],
        user_message: str,
    ) -> dict[str, Any]:
        """Generate AI response based on conversation history."""
        history_text = "\n".join([
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in history[-10:]  # Last 10 messages for context
        ])

        prompt = f"""You are a friendly English conversation partner.

Topic: {session['topic']}
Difficulty Level: {session['difficulty_level']}/5

Conversation so far:
{history_text}

User's latest message: {user_message}

Respond naturally to continue the conversation. Also provide:
1. Any suggestions for improving their English
2. Vocabulary tips related to the conversation
3. Any grammar corrections (if needed, be gentle)

Format your response as:
RESPONSE: [your conversational response]
SUGGESTIONS: [comma-separated suggestions, or "none"]
VOCABULARY: [word - definition, or "none"]
GRAMMAR: [gentle correction, or "none"]
"""

        ai_text = await ai_service.generate_response(prompt)
        
        # Parse response (simplified - production would use structured output)
        return {
            "content": ai_text.split("RESPONSE:")[-1].split("SUGGESTIONS:")[0].strip() if "RESPONSE:" in ai_text else ai_text,
            "suggestions": [],
            "vocabulary_tips": [],
            "grammar_notes": [],
        }

    async def end_session(self, session_id: UUID, user_id: UUID) -> ConversationSession:
        """End a conversation session and generate summary."""
        session = await ConversationSession.select().where(
            (ConversationSession.id == session_id)
            & (ConversationSession.user == user_id)
        ).first()

        if not session:
            raise NotFoundException(detail="Session not found")

        if session["ended_at"]:
            return session

        # Get all messages
        messages = await ConversationMessage.select().where(
            ConversationMessage.session == session_id
        )

        # Calculate duration
        duration = int((datetime.now() - session["started_at"]).total_seconds())

        # Generate analysis
        analysis = await self._analyze_session(session, messages)

        await ConversationSession.update({
            "ended_at": datetime.now(),
            "duration_seconds": duration,
            "grammar_score": analysis.get("grammar_score"),
            "fluency_score": analysis.get("fluency_score"),
            "coherence_score": analysis.get("coherence_score"),
            "overall_score": analysis.get("overall_score"),
            "ai_summary": analysis.get("summary"),
            "ai_suggestions": analysis.get("suggestions", []),
            "vocabulary_used": analysis.get("vocabulary", []),
        }).where(ConversationSession.id == session_id)

        logger.info(f"Ended conversation session {session_id}")
        return await ConversationSession.select().where(
            ConversationSession.id == session_id
        ).first()

    async def _analyze_session(
        self, session: dict, messages: list
    ) -> dict[str, Any]:
        """Analyze the conversation session."""
        user_messages = [m["content"] for m in messages if m["role"] == "user"]
        
        if not user_messages:
            return {
                "grammar_score": 0,
                "fluency_score": 0,
                "coherence_score": 0,
                "overall_score": 0,
                "summary": "No messages to analyze",
                "suggestions": [],
                "vocabulary": [],
            }

        # Use AI service to analyze
        return await ai_service.analyze_conversation(user_messages, session["topic"])

    async def get_user_sessions(
        self,
        user_id: UUID,
        offset: int = 0,
        limit: int = 20,
    ) -> list[ConversationSession]:
        """Get user's conversation sessions."""
        return await ConversationSession.select().where(
            ConversationSession.user == user_id
        ).order_by(
            ConversationSession.created_at, ascending=False
        ).offset(offset).limit(limit)


# Singleton instance
conversation_service = ConversationService()
