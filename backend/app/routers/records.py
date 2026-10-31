from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.schemas import Transcript, ValidationResult
from app.services.store import get_store
from app.database import get_db

transcripts_router = APIRouter(prefix="/api/transcripts", tags=["transcripts"])
validations_router = APIRouter(prefix="/api/validations", tags=["validations"])


@transcripts_router.get("/{transcript_id}", response_model=Transcript)
def get_transcript(transcript_id: str, db: Session = Depends(get_db)) -> Transcript:
    return get_store(db).get_transcript(transcript_id)


@validations_router.get("/{validation_id}", response_model=ValidationResult)
def get_validation(validation_id: str, db: Session = Depends(get_db)) -> ValidationResult:
    return get_store(db).get_validation(validation_id)
