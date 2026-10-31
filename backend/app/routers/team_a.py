import os
import tempfile
import uuid
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.schemas import SpeakerMappingRequest, Transcript
from app.services.store import Store, get_store
from app.services.transcription import GroqTranscriber, format_timestamp
from app.services.diarization import (
    DiarizationResult,
    diarize_audio,
    greatest_overlap_segment,
    speaker_display_name,
)

router = APIRouter(prefix="/api/team-a", tags=["team-a"])

ALLOWED_EXTENSIONS = {".flac", ".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".ogg", ".wav", ".webm"}
ALLOWED_CONTENT_TYPES = {
    "audio/flac", "audio/mpeg", "audio/mp4", "audio/x-m4a", "audio/mpga",
    "audio/ogg", "audio/wav", "audio/x-wav", "video/mp4", "video/mpeg",
    "audio/webm", "video/webm", "application/octet-stream",
}
GROQ_FREE_TIER_MAX_BYTES = 25 * 1024 * 1024
logger = logging.getLogger("clinical_scribe.team_a")


def _safe_worker_error(exc: Exception) -> str:
    if isinstance(exc, RuntimeError):
        return str(exc)[:500]
    return "Database persistence failed while saving transcription."


def _build_transcript_entries(result, turns) -> list[dict]:
    entries = []
    for segment in result.segments:
        if not segment.text:
            continue
        speaker_id = None
        speaker_role = "unknown"
        speaker = "Unknown speaker"
        speaker_display_name_value = speaker
        if segment.start_ms is not None and segment.end_ms is not None and turns:
            turn = greatest_overlap_segment(
                segment.start_ms,
                segment.end_ms,
                turns,
            )
            if turn is not None:
                speaker_id = turn.speaker_id
                speaker = speaker_display_name(turn.speaker_id)
                speaker_role = "unknown"
                speaker_display_name_value = speaker
        entries.append({
            "timestamp": format_timestamp(segment.start_ms),
            "offset_ms": segment.start_ms or 0,
            "speaker": speaker,
            "speaker_role": speaker_role,
            "speaker_id": speaker_id,
            "speaker_display_name": speaker_display_name_value,
            "start_time_ms": segment.start_ms,
            "end_time_ms": segment.end_ms,
            "text": segment.text,
            "confidence": segment.confidence,
        })
    return entries


def _background_transcribe(consultation_id: str, audio_path: str) -> None:
    store = Store()
    phase = "starting"
    try:
        logger.info("Team A transcription task started for consultation %s", consultation_id)
        phase = "processing-status"
        store.set_transcript_processing_status(
            consultation_id,
            "processing",
            model_name=settings.team_a_transcription_model,
        )
        logger.info("Team A Groq request started for consultation %s", consultation_id)
        phase = "groq"
        result = GroqTranscriber().transcribe(audio_path)
        logger.info("Team A Groq request completed for consultation %s", consultation_id)
        phase = "persistence"
        unknown_entries = _build_transcript_entries(result, [])
        store.replace_transcript_entries(
            consultation_id,
            unknown_entries,
            language=result.language,
            duration_ms=result.duration_ms,
            model_name=result.model_name,
        )
        logger.info("Team A transcription persistence completed before optional diarization")

        phase = "diarization"
        try:
            diarization_result = diarize_audio(audio_path)
        except Exception as exc:
            diarization_result = DiarizationResult(
                "failed",
                [],
                "Speaker diarization failed. The text transcription remains available.",
            )
            logger.warning(
                "Team A diarization call raised unexpectedly for consultation %s: exception=%s",
                consultation_id,
                exc.__class__.__name__,
            )
        if isinstance(diarization_result, list):
            diarization_result = DiarizationResult("completed", diarization_result, None)

        try:
            if hasattr(store, "set_transcript_diarization_status"):
                store.set_transcript_diarization_status(
                    consultation_id,
                    diarization_result.status,
                    error=diarization_result.error,
                )
        except Exception:
            logger.exception(
                "Team A diarization-status persistence failed for consultation %s",
                consultation_id,
            )

        if diarization_result.turns:
            mapped_entries = _build_transcript_entries(result, diarization_result.turns)
            try:
                store.replace_transcript_entries(
                    consultation_id,
                    mapped_entries,
                    language=result.language,
                    duration_ms=result.duration_ms,
                    model_name=result.model_name,
                )
            except Exception:
                logger.exception(
                    "Team A speaker-mapping persistence failed after transcription for consultation %s",
                    consultation_id,
                )
    except Exception as exc:
        safe_error = (
            "Database persistence failed while saving transcription."
            if phase in {"starting", "processing-status", "persistence"}
            else _safe_worker_error(exc)
        )
        logger.warning(
            "Team A transcription task failed for consultation %s: %s",
            consultation_id,
            exc.__class__.__name__,
        )
        try:
            store.set_transcript_processing_status(
                consultation_id,
                "failed",
                error=safe_error,
                processed_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception:
            logger.exception(
                "Team A failed-status persistence failed for consultation %s",
                consultation_id,
            )
    finally:
        if os.path.exists(audio_path):
            os.unlink(audio_path)


@router.post("/transcriptions/{consultation_id}", response_model=Transcript, status_code=status.HTTP_202_ACCEPTED)
async def upload_audio(
    consultation_id: str,
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Transcript:
    original_name = Path(audio.filename or "audio")
    extension = original_name.suffix.lower()
    content_type = (audio.content_type or "").lower().split(";")[0]
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported audio format. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=422, detail="Unsupported audio content type.")

    total = 0
    fd, temp_path = tempfile.mkstemp(prefix="clinical-scribe-", suffix=extension)
    try:
        with os.fdopen(fd, "wb") as destination:
            while chunk := await audio.read(1024 * 1024):
                total += len(chunk)
                if total > min(settings.team_a_max_audio_bytes, GROQ_FREE_TIER_MAX_BYTES):
                    raise HTTPException(
                        status_code=413,
                        detail="Audio file exceeds the Groq 25 MB upload limit.",
                    )
                destination.write(chunk)
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise

    if total == 0:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise HTTPException(status_code=422, detail="The uploaded audio file is empty.")

    logger.info(
        "Team A audio upload saved for consultation %s: size=%d bytes, extension=%s, content_type=%s",
        consultation_id,
        total,
        extension,
        content_type or "not-provided",
    )

    store = get_store(db)
    try:
        transcript = store.set_transcript_processing_status(
            consultation_id,
            "processing",
            model_name=settings.team_a_transcription_model,
        )
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise

    try:
        background_tasks.add_task(_background_transcribe, consultation_id, temp_path)
        logger.info("Team A transcription task scheduled for consultation %s", consultation_id)
    except Exception as exc:
        try:
            store.set_transcript_processing_status(
                consultation_id,
                "failed",
                error="Transcription task could not be scheduled.",
                processed_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception:
            logger.exception(
                "Team A scheduling-failure status persistence failed for consultation %s",
                consultation_id,
            )
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        logger.warning(
            "Team A transcription task scheduling failed for consultation %s: %s",
            consultation_id,
            exc.__class__.__name__,
        )
        raise HTTPException(status_code=500, detail="Transcription task could not be scheduled.")
    return transcript


@router.get("/transcriptions/{consultation_id}", response_model=Transcript | None)
def get_transcription_status(
    consultation_id: str,
    db: Session = Depends(get_db),
) -> Transcript | None:
    store = get_store(db)
    transcript = store.get_transcript_by_consultation(consultation_id)
    if transcript and transcript.processing_status == "processing" and transcript.recorded_at:
        try:
            started = datetime.fromisoformat(transcript.recorded_at.replace("Z", "+00:00"))
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - started > timedelta(minutes=30):
                return store.set_transcript_processing_status(
                    consultation_id,
                    "failed",
                    error="Transcription timed out while processing.",
                    processed_at=datetime.now(timezone.utc).isoformat(),
                )
        except (TypeError, ValueError):
            pass
    return transcript


@router.patch(
    "/transcriptions/{consultation_id}/speaker-mapping/{speaker_id}",
    response_model=Transcript,
)
def map_speaker(
    consultation_id: str,
    speaker_id: str,
    payload: SpeakerMappingRequest,
    db: Session = Depends(get_db),
) -> Transcript:
    return get_store(db).set_speaker_mapping(
        consultation_id,
        speaker_id,
        payload.speaker_role,
        payload.speaker_display_name,
    )
