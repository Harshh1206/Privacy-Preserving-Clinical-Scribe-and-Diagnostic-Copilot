from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import logging

from app.config import settings

logger = logging.getLogger("clinical_scribe.team_a")


@dataclass(frozen=True)
class SpeakerTurn:
    speaker_id: str
    start_ms: int
    end_ms: int


@dataclass(frozen=True)
class DiarizationResult:
    status: str
    turns: list[SpeakerTurn]
    error: str | None = None


@lru_cache(maxsize=1)
def _load_pipeline(huggingface_token: str):
    from pyannote.audio import Pipeline

    try:
        return Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            token=huggingface_token,
        )
    except TypeError:
        return Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=huggingface_token,
        )


def speaker_display_name(speaker_id: str) -> str:
    prefix, separator, suffix = speaker_id.rpartition("_")
    if separator and suffix.isdigit():
        return f"Speaker {int(suffix) + 1}"
    return speaker_id.replace("_", " ").strip() or "Unknown speaker"


def greatest_overlap_segment(
    start_ms: int,
    end_ms: int,
    turns: list[SpeakerTurn],
) -> SpeakerTurn | None:
    candidates: list[tuple[int, SpeakerTurn]] = []
    for turn in turns:
        overlap = max(0, min(end_ms, turn.end_ms) - max(start_ms, turn.start_ms))
        if overlap > 0:
            candidates.append((overlap, turn))
    return max(candidates, key=lambda candidate: candidate[0])[1] if candidates else None


def diarize_audio(audio_path: str) -> DiarizationResult:
    if not settings.team_a_diarization_enabled:
        logger.info("Team A diarization skipped: disabled by configuration")
        return DiarizationResult("disabled", [], None)
    if not settings.huggingface_token:
        error = "Local diarization is enabled but HUGGINGFACE_TOKEN is not configured."
        logger.warning("Team A diarization failed before model loading: missing Hugging Face token")
        return DiarizationResult("failed", [], error)
    try:
        import pyannote.audio  # noqa: F401
    except ImportError:
        error = "pyannote.audio is not installed. Install backend/requirements.txt dependencies."
        logger.warning("Team A diarization failed before model loading: %s", error)
        return DiarizationResult("failed", [], error)
    except Exception as exc:
        if exc.__class__.__name__ == "AttributeError" and "AudioMetaData" in str(exc):
            error = "Diarization unavailable: incompatible torch and torchaudio versions."
        else:
            error = "Diarization dependency initialization failed. The text transcription remains available."
        logger.warning(
            "Team A diarization dependency initialization failed: exception=%s",
            exc.__class__.__name__,
        )
        return DiarizationResult("failed", [], error)

    try:
        logger.info("Team A pyannote pipeline loading started")
        pipeline = _load_pipeline(settings.huggingface_token)
        logger.info("Team A pyannote pipeline loading completed")
        logger.info("Team A pyannote inference started")
        annotation = pipeline(audio_path)
        logger.info("Team A pyannote inference completed")
        turns = sorted(
            [
                SpeakerTurn(
                    speaker_id=str(speaker),
                    start_ms=max(0, int(round(turn.start * 1000))),
                    end_ms=max(0, int(round(turn.end * 1000))),
                )
                for turn, _, speaker in annotation.itertracks(yield_label=True)
            ],
            key=lambda item: (item.start_ms, item.end_ms),
        )
        if not turns:
            error = "Diarization completed without returning any speaker segments."
            logger.warning("Team A diarization returned no speaker segments")
            return DiarizationResult("failed", [], error)
        return DiarizationResult("completed", turns, None)
    except Exception as exc:
        error = "Speaker diarization failed. The text transcription remains available."
        logger.warning(
            "Team A pyannote pipeline failed: exception=%s",
            exc.__class__.__name__,
        )
        return DiarizationResult("failed", [], error)
