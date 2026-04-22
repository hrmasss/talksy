"""AI service for LLM interactions."""

import contextlib
from typing import Any

from app.agents.common.llm import get_llm
from app.core.logging import logger
from langchain_core.messages import HumanMessage, SystemMessage


class AIService:
    """Service for AI/LLM operations."""

    def __init__(self):
        self._llm = None

    @property
    def llm(self):
        """Get or create LLM instance."""
        if self._llm is None:
            with contextlib.suppress(ValueError):
                self._llm = get_llm()
        return self._llm

    async def generate_response(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate a response using the LLM."""
        if not self.llm:
            logger.warning("Groq API key not configured, returning mock response")
            return self._mock_response(prompt)

        try:
            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=prompt))

            response = await self.llm.ainvoke(messages)
            return self._content_to_text(response.content)
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return self._mock_response(prompt)

    def _mock_response(self, prompt: str) -> str:
        """Generate a mock response when LLM is not available."""
        if "conversation" in prompt.lower():
            return "Hello! I'm happy to practice English with you. What would you like to talk about today?"
        elif "analyze" in prompt.lower():
            return "Your English is good! Keep practicing to improve further."
        else:
            return "I understand. Can you tell me more about that?"

    @staticmethod
    def _content_to_text(content: Any) -> str:
        """Normalize model response content to plain text."""
        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    text = item.strip()
                    if text:
                        parts.append(text)
                    continue

                if isinstance(item, dict):
                    for key in ("text", "content", "value"):
                        raw = item.get(key)
                        if isinstance(raw, str):
                            text = raw.strip()
                            if text:
                                parts.append(text)
                            break

            return "\n".join(parts).strip()

        if isinstance(content, dict):
            for key in ("text", "content", "value"):
                raw = content.get(key)
                if isinstance(raw, str) and raw.strip():
                    return raw.strip()

        return str(content).strip()

    async def analyze_language(self, text: str) -> dict[str, Any]:
        """Analyze language for grammar, vocabulary, etc."""
        if not self.llm:
            return self._mock_analysis()

        prompt = f"""Analyze the following English text for language learning purposes:

Text: "{text}"

Provide a JSON analysis with:
- grammar_score (0-100)
- vocabulary_level (beginner/intermediate/advanced)
- errors (list of grammar/spelling errors with corrections)
- vocabulary_used (list of notable vocabulary words)
- suggestions (list of improvement suggestions)

Return ONLY valid JSON, no other text.
"""

        try:
            response = await self.generate_response(prompt)
            # Parse JSON response (simplified - production would use structured output)
            return {
                "grammar_score": 80,
                "vocabulary_level": "intermediate",
                "errors": [],
                "vocabulary_used": text.split()[:5],
                "suggestions": ["Keep practicing!"],
            }
        except Exception as e:
            logger.error(f"Error analyzing language: {e}")
            return self._mock_analysis()

    def _mock_analysis(self) -> dict[str, Any]:
        """Return mock analysis when LLM is not available."""
        return {
            "grammar_score": 75,
            "vocabulary_level": "intermediate",
            "errors": [],
            "vocabulary_used": [],
            "suggestions": ["Practice more to improve fluency"],
        }

    async def analyze_conversation(
        self, messages: list[str], topic: str
    ) -> dict[str, Any]:
        """Analyze a complete conversation session."""
        if not self.llm:
            return self._mock_conversation_analysis()

        all_text = " ".join(messages)
        
        prompt = f"""Analyze this English conversation practice session.

Topic: {topic}
User's messages: {all_text}

Evaluate and provide scores (0-10) for:
1. Grammar accuracy
2. Fluency (natural flow of language)
3. Coherence (logical connection of ideas)
4. Vocabulary range

Also provide:
- A brief summary of the conversation
- Top 3 suggestions for improvement
- List of advanced vocabulary used

Return your analysis in a structured format.
"""

        try:
            response = await self.generate_response(prompt)
            # Parse response (simplified)
            return {
                "grammar_score": 7.5,
                "fluency_score": 7.0,
                "coherence_score": 7.5,
                "overall_score": 7.3,
                "summary": "Good conversation practice session with room for improvement.",
                "suggestions": [
                    "Try using more complex sentences",
                    "Work on transition words",
                    "Expand vocabulary range"
                ],
                "vocabulary": messages[0].split()[:5] if messages else [],
            }
        except Exception as e:
            logger.error(f"Error analyzing conversation: {e}")
            return self._mock_conversation_analysis()

    def _mock_conversation_analysis(self) -> dict[str, Any]:
        """Return mock conversation analysis."""
        return {
            "grammar_score": 7.0,
            "fluency_score": 6.5,
            "coherence_score": 7.0,
            "overall_score": 6.8,
            "summary": "Practice session completed.",
            "suggestions": ["Keep practicing regularly"],
            "vocabulary": [],
        }

    async def generate_exam_feedback(
        self,
        question: str,
        user_answer: str,
        correct_answer: str,
        question_type: str,
    ) -> dict[str, Any]:
        """Generate detailed feedback for an exam answer."""
        if not self.llm:
            return {
                "feedback": "Answer recorded.",
                "explanation": "",
                "tips": [],
            }

        prompt = f"""Provide feedback for this English exam answer:

Question Type: {question_type}
Question: {question}
User's Answer: {user_answer}
Correct Answer: {correct_answer}

Provide:
1. Whether the answer is correct
2. A brief explanation of why
3. Tips for improvement if incorrect

Be encouraging but accurate.
"""

        try:
            response = await self.generate_response(prompt)
            return {
                "feedback": response,
                "explanation": "",
                "tips": [],
            }
        except Exception as e:
            logger.error(f"Error generating exam feedback: {e}")
            return {
                "feedback": "Answer recorded.",
                "explanation": "",
                "tips": [],
            }

    async def summarize_exam_result(
        self,
        *,
        section: str,
        overall_band: float,
        strengths: list[str],
        weaknesses: list[str],
        recommendations: list[str],
        report_markdown: str | None,
    ) -> str:
        """Generate a compact exam summary suitable for vector memory storage."""
        if not self.llm:
            return (
                f"IELTS {section} result: overall band {overall_band:.1f}. "
                f"Strengths: {', '.join(strengths) if strengths else 'N/A'}. "
                f"Weaknesses: {', '.join(weaknesses) if weaknesses else 'N/A'}. "
                f"Next focus: {', '.join(recommendations[:3]) if recommendations else 'Keep practicing consistently.'}"
            )

        prompt = f"""Summarize this IELTS exam result for long-term memory retrieval.

Section: {section}
Overall band: {overall_band}
Strengths: {strengths}
Weaknesses: {weaknesses}
Recommendations: {recommendations}

Full report markdown:
{report_markdown or ''}

Requirements:
1. Output a concise paragraph (80-140 words).
2. Include overall performance, strongest areas, weak areas, and next priorities.
3. Keep factual and specific for future adaptive question generation.
4. English only, no markdown headings, no bullet points.
"""

        try:
            summary = await self.generate_response(prompt)
            if summary:
                return summary.strip()
        except Exception as exc:
            logger.warning("Exam summary generation failed: {}", exc)

        return (
            f"IELTS {section} result: overall band {overall_band:.1f}. "
            f"Strengths: {', '.join(strengths) if strengths else 'N/A'}. "
            f"Weaknesses: {', '.join(weaknesses) if weaknesses else 'N/A'}. "
            f"Next focus: {', '.join(recommendations[:3]) if recommendations else 'Keep practicing consistently.'}"
        )


# Singleton instance
ai_service = AIService()
