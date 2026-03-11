"""Text-to-Speech and Speech-to-Text service using Google Gemini.

TTS: Uses the google-genai SDK to generate spoken audio from text.
STT: Uses Gemini's multimodal capabilities to transcribe audio.
"""

from __future__ import annotations

import contextlib
import io
import tempfile
import wave
from pathlib import Path

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from app.agents.common.llm import next_api_key
from app.config import settings
from app.core.logging import logger


def _get_client(api_key: str | None = None) -> genai.Client:
    """Create a Google GenAI client with the given or next pooled key."""
    key = api_key or next_api_key()
    return genai.Client(api_key=key)


def _pcm_to_wav(audio_bytes: bytes, sample_rate: int) -> bytes:
    """Wrap raw 16-bit mono PCM bytes in a WAV container."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_bytes)
    return buffer.getvalue()


def _sample_rate_from_mime_type(mime_type: str | None) -> int:
    """Extract the sample rate from a MIME type when it is available."""
    if not mime_type:
        return settings.gemini_tts_sample_rate

    for part in mime_type.split(";"):
        name, _, value = part.strip().partition("=")
        if name.lower() == "rate":
            try:
                return int(value)
            except ValueError:
                break

    return settings.gemini_tts_sample_rate


def _file_suffix_for_mime_type(mime_type: str) -> str:
    """Choose a temporary filename suffix based on the uploaded MIME type."""
    suffix_map = {
        "audio/webm": ".webm",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/ogg": ".ogg",
        "audio/ogg; codecs=opus": ".ogg",
        "audio/mp4": ".m4a",
    }
    return suffix_map.get(mime_type.lower(), ".audio")


# ── Text-to-Speech ────────────────────────────────────────────────


async def text_to_speech(
    text: str,
    *,
    voice: str = "Kore",
    api_key: str | None = None,
) -> bytes:
    """Convert *text* to speech audio (WAV) via Gemini's preview TTS model.

    Returns raw WAV bytes.
    """
    client = _get_client(api_key)
    model = settings.gemini_tts_model

    try:
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
            )
        )
    except genai_errors.APIError as exc:
        logger.warning("Gemini TTS request failed: {}", exc)
        raise RuntimeError("Text-to-speech generation failed") from exc

    if not response.candidates:
        raise RuntimeError("Gemini returned no TTS candidates")

    candidate = response.candidates[0]
    if not candidate.content or not candidate.content.parts:
        raise RuntimeError("Gemini returned no audio content")

    for part in candidate.content.parts:
        if not part.inline_data or not part.inline_data.data:
            continue
        mime_type = part.inline_data.mime_type
        audio_bytes = part.inline_data.data
        if mime_type and mime_type.startswith("audio/wav"):
            return audio_bytes
        return _pcm_to_wav(audio_bytes, _sample_rate_from_mime_type(mime_type))

    raise RuntimeError("Gemini returned no audio data")


# ── Speech-to-Text ────────────────────────────────────────────────


async def speech_to_text(
    audio_bytes: bytes,
    mime_type: str = "audio/webm",
    *,
    api_key: str | None = None,
) -> str:
    """Transcribe *audio_bytes* to text via Gemini's uploaded-file workflow.

    Accepts any audio format Gemini supports (webm, mp3, wav, ogg, etc.).
    """
    client = _get_client(api_key)
    model = settings.gemini_stt_model
    temp_path: Path | None = None
    uploaded_audio = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=_file_suffix_for_mime_type(mime_type),
        ) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = Path(temp_file.name)

        uploaded_audio = client.files.upload(file=str(temp_path))
        response = client.models.generate_content(
            model=model,
            contents=[
                types.Part.from_uri(
                    file_uri=uploaded_audio.uri,
                    mime_type=uploaded_audio.mime_type,
                ),
                (
                    "Transcribe this audio accurately. "
                    "Provide only the transcription without any additional commentary."
                ),
            ],
        )
    except genai_errors.APIError as exc:
        logger.warning("Gemini STT request failed: {}", exc)
        raise RuntimeError("Speech-to-text transcription failed") from exc
    finally:
        if uploaded_audio is not None:
            with contextlib.suppress(Exception):
                client.files.delete(name=uploaded_audio.name)
        if temp_path is not None:
            with contextlib.suppress(FileNotFoundError):
                temp_path.unlink()

    if response.text:
        return response.text.strip()

    if response.candidates:
        candidate = response.candidates[0]
        if candidate.content and candidate.content.parts:
            for part in candidate.content.parts:
                if part.text:
                    return part.text.strip()

    raise RuntimeError("Gemini returned no transcription text")
