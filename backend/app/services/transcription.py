from __future__ import annotations

from dataclasses import dataclass
from app.config import settings


@dataclass
class TranscriptionSegment:
    start_ms: int | None
    end_ms: int | None
    text: str
    confidence: float | None = None


@dataclass
class TranscriptionResult:
    segments: list[TranscriptionSegment]
    language: str
    duration_ms: int
    model_name: str


class GroqTranscriber:
    def transcribe(self, audio_path: str) -> TranscriptionResult:
        try:
            from groq import Groq
        except ImportError as exc:
            raise RuntimeError(
                "The Groq SDK is not installed. Install backend/requirements.txt dependencies."
            ) from exc

        if not settings.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not configured. Add it to backend/.env before uploading audio."
            )

        model_name = settings.team_a_transcription_model
        client = Groq(api_key=settings.groq_api_key)
        transcribed: list[TranscriptionSegment] = []
        try:
            with open(audio_path, "rb") as audio_file:
                response = client.audio.transcriptions.create(
                    file=audio_file,
                    model=model_name,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                    temperature=0,
                )
        except Exception as exc:
            name = exc.__class__.__name__
            status_code = getattr(exc, "status_code", None)
            if status_code in (401, 403):
                raise RuntimeError("Groq authentication failed. Verify GROQ_API_KEY.") from exc
            if status_code == 429:
                raise RuntimeError("Groq transcription rate limit reached. Try again later.") from exc
            if status_code and 400 <= int(status_code) < 500:
                raise RuntimeError(f"Groq rejected the audio ({name}). Verify its format and size.") from exc
            if status_code and 500 <= int(status_code) < 600:
                raise RuntimeError("Groq transcription service is temporarily unavailable. Try again.") from exc
            raise RuntimeError(f"Groq transcription failed ({name}).") from exc

        segments = getattr(response, "segments", None) or []
        if isinstance(response, dict):
            segments = response.get("segments", [])
        for segment in segments:
            if isinstance(segment, dict):
                start = segment.get("start")
                end = segment.get("end")
                text = segment.get("text", "")
                confidence = segment.get("confidence")
                if confidence is None:
                    confidence = segment.get("avg_confidence")
            else:
                start = getattr(segment, "start", None)
                end = getattr(segment, "end", None)
                text = getattr(segment, "text", "")
                confidence = getattr(segment, "confidence", None)
                if confidence is None:
                    confidence = getattr(segment, "avg_confidence", None)
            start_ms = max(0, int(float(start) * 1000)) if isinstance(start, (int, float, str)) and str(start) else None
            end_ms = max(0, int(float(end) * 1000)) if isinstance(end, (int, float, str)) and str(end) else None
            if isinstance(confidence, bool):
                confidence = None
            elif isinstance(confidence, (int, float)):
                value = float(confidence)
                if 0.0 <= value <= 1.0:
                    confidence = value
                elif 1.0 < value <= 100.0:
                    confidence = value / 100.0
                else:
                    confidence = None
            else:
                confidence = None
            transcribed.append(TranscriptionSegment(
                start_ms=start_ms,
                end_ms=end_ms,
                text=str(text).strip(),
                confidence=confidence,
            ))
        duration_ms = max(
            (segment.end_ms for segment in transcribed if segment.end_ms is not None),
            default=0,
        )
        language = getattr(response, "language", None)
        if isinstance(response, dict):
            language = response.get("language")
        return TranscriptionResult(
            segments=transcribed,
            language=language or "en-US",
            duration_ms=duration_ms,
            model_name=model_name,
        )


def format_timestamp(offset_ms: int | None) -> str:
    if offset_ms is None:
        return "unknown"
    total_seconds = offset_ms // 1000
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
