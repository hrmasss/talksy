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
from app.services.speech import generate_text_and_audio, cache_audio_file
from app.agents.common.llm import next_api_key


class ConversationService(BaseService[ConversationSession]):
    """Service for conversation operations."""

    model = ConversationSession

    async def start_session(
        self, user_id: UUID, data: ConversationStart
    ) -> dict[str, Any]:
        """Start a new conversation session.
        
        Returns: dict with session info including initial_message and audio_url
        """
        session_data = {
            "id": uuid4(),
            "user": user_id,
            "topic": data.topic,
            "scenario": data.scenario,
            "difficulty_level": data.difficulty_level,
        }

        session = ConversationSession(**session_data)
        await session.save()

        # Generate initial AI message (text + audio in parallel)
        initial_message, audio_url = await self._generate_initial_message(session, data)
        
        logger.info(f"Started conversation session {session.id} for user {user_id}")
        
        return {
            "id": str(session.id),
            "user": str(user_id),
            "topic": session.topic,
            "scenario": session.scenario,
            "difficulty_level": session.difficulty_level,
            "initial_message": {
                "id": str(initial_message.id),
                "content": initial_message.content,
                "audio_url": audio_url,
            }
        }

    async def _generate_initial_message(
        self, session: ConversationSession, data: ConversationStart
    ) -> tuple[ConversationMessage, str | None]:
        """Generate initial AI message for the conversation.
        
        Returns: (message, audio_url)
        Generates both text and audio in parallel for faster response.
        """
        prompt = f"""You are a friendly English conversation partner helping someone practice their English skills.
        
Topic: {data.topic}
Scenario: {data.scenario or 'General conversation practice'}
Difficulty Level: {data.difficulty_level}/5

Start a natural conversation about this topic. Be engaging, ask questions, and help them practice.
Keep your response appropriate for the difficulty level - simpler vocabulary and shorter sentences for lower levels.
"""

        audio_url = None
        try:
            # Generate text and audio in parallel for faster response
            ai_response, audio_bytes = await generate_text_and_audio(
                prompt, 
                api_key=next_api_key(),
                parallel_mode=True
            )
            # Cache the audio and get URL
            audio_url = await cache_audio_file(ai_response, audio_bytes)
            logger.info("Generated initial message with audio for conversation {}", session.id)
        except Exception as exc:
            # Fallback to text-only if audio generation fails
            logger.warning("Parallel text+audio generation failed, falling back to text only: {}", exc)
            ai_response = await ai_service.generate_response(prompt)
        
        message = ConversationMessage(
            id=uuid4(),
            session=session.id,
            role="assistant",
            content=ai_response,
            audio_url=audio_url,
        )
        await message.save()

        # Update message count
        await ConversationSession.update({"message_count": 1}).where(
            ConversationSession.id == session.id
        )

        return message, audio_url

    async def send_message(
        self,
        session_id: UUID,
        user_id: UUID,
        data: ConversationMessageSchema,
    ) -> dict[str, Any]:
        """Send a message and get AI response.
        
        Optimized to generate AI response text + audio in parallel.
        """
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

        # Analyze user's message (parallel with AI response generation)
        analysis = await ai_service.analyze_language(data.content)

        # Generate AI response (text + audio in parallel)
        ai_response_data = await self._generate_response(session, history, data.content)
        ai_response_text = ai_response_data["content"]
        audio_url = ai_response_data.get("audio_url")

        # Save AI message
        ai_message = ConversationMessage(
            id=uuid4(),
            session=session_id,
            role="assistant",
            content=ai_response_text,
            analysis=analysis,
            audio_url=audio_url,
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
                "content": ai_response_text,
                "audio_url": audio_url,
            },
            "suggestions": ai_response_data.get("suggestions", []),
            "vocabulary_tips": ai_response_data.get("vocabulary_tips", []),
            "grammar_notes": ai_response_data.get("grammar_notes", []),
        }

    async def _generate_response(
        self,
        session: dict,
        history: list[ConversationMessage],
        user_message: str,
    ) -> dict[str, Any]:
        """Generate AI response based on conversation history.
        
        Generates text and audio in parallel for optimal performance.
        Returns: dict with 'content', 'audio_url', and metadata
        """
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

Respond naturally to continue the conversation. Be encouraging and engaging.
Keep your response concise (2-3 sentences) and appropriate for the difficulty level.
"""

        audio_url = None
        ai_text = ""
        
        try:
            # Generate text and audio in parallel for faster response
            ai_text, audio_bytes = await generate_text_and_audio(
                prompt, 
                api_key=next_api_key(),
                parallel_mode=True
            )
            # Cache the audio and get URL
            audio_url = await cache_audio_file(ai_text, audio_bytes)
            logger.debug("Generated response with audio for conversation {}", session['id'])
        except Exception as exc:
            # Fallback to text-only if audio generation fails
            logger.warning("Parallel text+audio generation failed, falling back to text only: {}", exc)
            ai_text = await ai_service.generate_response(prompt)
        
        # Parse response for metadata (if formatted with markers)
        return {
            "content": ai_text,
            "audio_url": audio_url,
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
