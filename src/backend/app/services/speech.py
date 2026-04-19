"""Text-to-Speech and Speech-to-Text service using Groq.

TTS: Uses Groq Orpheus text-to-speech.
STT: Uses Groq Whisper transcription models.
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import re
import tempfile
import wave
from collections.abc import AsyncIterator
from pathlib import Path

from groq import Groq

from app.agents.common.llm import next_api_key
from app.config import settings
from app.core.logging import logger


def _get_client(api_key: str | None = None) -> Groq:
    """Create a Groq client with the given or next pooled key."""
    key = api_key or next_api_key()
    return Groq(api_key=key)


def _get_audio_cache_dir() -> Path:
    """Get the audio cache directory, creating it if needed."""
    cache_dir = Path(settings.static_dir) / "audio" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _get_cached_audio_path(text_hash: str) -> Path:
    """Return the path for a cached audio file based on text hash."""
    import hashlib

    safe_hash = hashlib.sha256(text_hash.encode()).hexdigest()[:16]
    return _get_audio_cache_dir() / f"{safe_hash}.wav"


async def cache_audio_file(text: str, audio_bytes: bytes) -> str:
    """Cache audio bytes to disk and return the relative URL path."""
    import hashlib

    text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
    path = _get_cached_audio_path(text_hash)

    if not path.exists():
        path.write_bytes(audio_bytes)
        logger.info("Cached audio file: {}", path.relative_to(settings.static_dir))

    return f"/static/audio/cache/{text_hash}.wav"


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


def _extract_wav_frames(audio_bytes: bytes) -> bytes:
    """Extract raw PCM frames from a WAV file."""
    with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
        return wav_file.readframes(wav_file.getnframes())


def _transcription_to_text(transcription: object) -> str:
    """Extract transcription text from a Groq SDK response object."""
    text = getattr(transcription, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    if isinstance(transcription, dict):
        raw = transcription.get("text")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()

    raise RuntimeError("Groq returned no transcription text")


def _chunk_tts_text(text: str, max_chars: int = 200) -> list[str]:
    """Split text into TTS-safe chunks.

    Groq Orpheus currently supports a maximum 200-character input per request.
    """
    normalized = " ".join(text.split()).strip()
    if not normalized:
        return []
    if len(normalized) <= max_chars:
        return [normalized]

    sentences = re.split(r"(?<=[.!?])\s+", normalized)
    chunks: list[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        if current:
            chunks.append(current)
            current = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if len(sentence) > max_chars:
            flush()
            words = sentence.split()
            part = ""
            for word in words:
                candidate = f"{part} {word}".strip()
                if len(candidate) <= max_chars:
                    part = candidate
                else:
                    if part:
                        chunks.append(part)
                    part = word[:max_chars]
            if part:
                chunks.append(part)
            continue

        candidate = f"{current} {sentence}".strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            flush()
            current = sentence

    flush()
    return chunks


def _sync_tts_request(
    text: str,
    *,
    voice: str,
    api_key: str | None,
) -> bytes:
    """Run a blocking Groq TTS request and return WAV bytes."""
    client = _get_client(api_key)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
        temp_path = Path(temp_file.name)

    try:
        response = client.audio.speech.create(
            model=settings.groq_tts_model,
            voice=voice,
            input=text,
            response_format="wav",
        )
        response.write_to_file(str(temp_path))
        return temp_path.read_bytes()
    except Exception as exc:
        logger.warning("Groq TTS request failed: {}", exc)
        raise RuntimeError("Text-to-speech generation failed") from exc
    finally:
        with contextlib.suppress(FileNotFoundError):
            temp_path.unlink()


def _sync_stt_request(
    audio_bytes: bytes,
    *,
    mime_type: str,
    api_key: str | None,
) -> str:
    """Run a blocking Groq STT request and return the transcribed text."""
    client = _get_client(api_key)

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=_file_suffix_for_mime_type(mime_type),
    ) as temp_file:
        temp_file.write(audio_bytes)
        temp_path = Path(temp_file.name)

    try:
        with temp_path.open("rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=audio_file,
                model=settings.groq_stt_model,
                prompt="Transcribe this audio accurately. Return only the spoken words.",
                response_format="verbose_json",
                timestamp_granularities=["word", "segment"],
                language="en",
                temperature=0.0,
            )
        return _transcription_to_text(transcription)
    except Exception as exc:
        logger.warning("Groq STT request failed: {}", exc)
        raise RuntimeError("Speech-to-text transcription failed") from exc
    finally:
        with contextlib.suppress(FileNotFoundError):
            temp_path.unlink()


# ── Text-to-Speech ────────────────────────────────────────────────


async def text_to_speech(
    text: str,
    *,
    voice: str | None = None,
    api_key: str | None = None,
) -> bytes:
    """Convert *text* to speech audio (WAV) via Groq Orpheus."""
    resolved_voice = voice or settings.groq_tts_voice
    parts = _chunk_tts_text(text)
    if not parts:
        raise RuntimeError("Text-to-speech requires non-empty text")

    wav_chunks: list[bytes] = []
    for part in parts:
        wav_chunks.append(
            await asyncio.to_thread(
                _sync_tts_request,
                part,
                voice=resolved_voice,
                api_key=api_key,
            )
        )

    if len(wav_chunks) == 1:
        return wav_chunks[0]

    pcm_frames = b"".join(_extract_wav_frames(chunk) for chunk in wav_chunks)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(settings.groq_tts_sample_rate)
        wav_file.writeframes(pcm_frames)
    return buffer.getvalue()


async def stream_text_to_speech(
    text: str,
    *,
    voice: str | None = None,
    api_key: str | None = None,
) -> AsyncIterator[bytes]:
    """Stream TTS audio as raw PCM chunks assembled from Groq TTS requests."""
    resolved_voice = voice or settings.groq_tts_voice
    parts = _chunk_tts_text(text)
    if not parts:
        raise RuntimeError("Text-to-speech requires non-empty text")

    for part in parts:
        wav_bytes = await asyncio.to_thread(
            _sync_tts_request,
            part,
            voice=resolved_voice,
            api_key=api_key,
        )
        pcm_bytes = _extract_wav_frames(wav_bytes)
        if pcm_bytes:
            yield pcm_bytes


# ── Speech-to-Text ────────────────────────────────────────────────


async def speech_to_text(
    audio_bytes: bytes,
    mime_type: str = "audio/webm",
    *,
    api_key: str | None = None,
) -> str:
    """Transcribe *audio_bytes* to text via Groq Whisper."""
    return await asyncio.to_thread(
        _sync_stt_request,
        audio_bytes,
        mime_type=mime_type,
        api_key=api_key,
    )


# ── Text + Audio Generation ──────────────────────────────────────


async def generate_text_and_audio(
    prompt: str,
    *,
    voice: str | None = None,
    api_key: str | None = None,
    parallel_mode: bool = True,
) -> tuple[str, bytes]:
    """Generate text with the main LLM, then synthesize that exact text to audio.

    The ``parallel_mode`` argument is retained for compatibility with callers.
    """
    from app.services.ai import ai_service

    del parallel_mode

    text = await ai_service.generate_response(prompt)
    audio_bytes = await text_to_speech(text, voice=voice, api_key=api_key)
    return text, audio_bytes
