"""Text-to-Speech and Speech-to-Text service using Google Gemini.

TTS: Uses the google-genai SDK to generate spoken audio from text.
STT: Uses Gemini's multimodal capabilities to transcribe audio.
"""

from __future__ import annotations

import base64

from google import genai
from google.genai import types

from app.agents.common.llm import next_api_key
from app.config import settings
from app.core.logging import logger


def _get_client(api_key: str | None = None) -> genai.Client:
    """Create a Google GenAI client with the given or next pooled key."""
    key = api_key or next_api_key()
    return genai.Client(api_key=key)


# ── Text-to-Speech ────────────────────────────────────────────────


async def text_to_speech(
    text: str,
    *,
    voice: str = "Kore",
    api_key: str | None = None,
) -> bytes:
    """Convert *text* to speech audio (WAV) via Gemini's TTS.

    Returns raw WAV bytes.
    """
    client = _get_client(api_key)
    model = settings.gemini_model

    response = client.models.generate_content(
        model=model,
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice,
                    )
                )
            ),
        ),
    )

    # The audio data is returned as inline_data in the first part
    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.data:
            return part.inline_data.data

    raise RuntimeError("Gemini returned no audio data")


# ── Speech-to-Text ────────────────────────────────────────────────


async def speech_to_text(
    audio_bytes: bytes,
    mime_type: str = "audio/webm",
    *,
    api_key: str | None = None,
) -> str:
    """Transcribe *audio_bytes* to text via Gemini's multimodal input.

    Accepts any audio format Gemini supports (webm, mp3, wav, ogg, etc.).
    """
    client = _get_client(api_key)
    model = settings.gemini_model

    response = client.models.generate_content(
        model=model,
        contents=[
            types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
            "Transcribe this audio exactly as spoken. Return only the transcription text, nothing else.",
        ],
    )

    return response.text.strip()
