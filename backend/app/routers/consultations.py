from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.models.schemas import (
    AuditEntry,
    Consultation,
    CreateConsultationRequest,
    FinalizeRequest,
    FinalizeResponse,
    SOAPNote,
    ValidationResult,
)
from app.services.errors import bad_request, conflict
from app.services.soap_generation import GroqSOAPGenerator, SOAPGenerationError
from app.services.store import get_store
from app.database import get_db

router = APIRouter(prefix="/api/consultations", tags=["consultations"])


@router.get("", response_model=list[Consultation])
def list_consultations(patient_id: Optional[str] = Query(default=None, alias="patientId"), db: Session = Depends(get_db)) -> list[Consultation]:
    return get_store(db).list_consultations(patient_id)


@router.get("/{consultation_id}", response_model=Consultation)
def get_consultation(consultation_id: str, db: Session = Depends(get_db)) -> Consultation:
    return get_store(db).get_consultation(consultation_id)


@router.post("", response_model=Consultation, status_code=201)
def create_consultation(body: CreateConsultationRequest, db: Session = Depends(get_db)) -> Consultation:
    return get_store(db).create_consultation(
        patient_id=body.patient_id,
        chief_complaint=body.chief_complaint,
        physician_id=body.physician_id,
        physician_name=body.physician_name,
        duration=body.duration,
    )


@router.post("/{consultation_id}/validate", response_model=ValidationResult)
def validate_consultation(consultation_id: str, db: Session = Depends(get_db)) -> ValidationResult:
    return get_store(db).validate_consultation(consultation_id)


@router.post("/{consultation_id}/finalize", response_model=FinalizeResponse)
def finalize_consultation(consultation_id: str, body: FinalizeRequest, db: Session = Depends(get_db)) -> FinalizeResponse:
    consultation, soap_note = get_store(db).finalize(
        consultation_id, body.physician_id, body.physician_name
    )
    return FinalizeResponse(consultation=consultation, soap_note=soap_note)


@router.post("/{consultation_id}/generate-soap", response_model=SOAPNote)
def generate_soap_note(consultation_id: str, db: Session = Depends(get_db)) -> SOAPNote:
    store = get_store(db)
    consultation = store.get_consultation(consultation_id)
    transcript = store.get_transcript_by_consultation(consultation_id)

    if transcript is None:
        raise bad_request("No transcript exists for this consultation")
    if transcript.processing_status != "completed":
        raise conflict("The transcript is not ready. Processing must complete before SOAP generation")
    if not transcript.entries:
        raise bad_request("The transcript has no entries to generate a SOAP note from")

    try:
        generated = GroqSOAPGenerator().generate(transcript)
    except SOAPGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    soap_note = store.generate_soap(
        consultation_id=consultation_id,
        soap_note_id=consultation.soap_note_id,
        generated=generated,
    )
    return soap_note


@router.get("/{consultation_id}/audit", response_model=list[AuditEntry])
def get_audit_trail(consultation_id: str, db: Session = Depends(get_db)) -> list[AuditEntry]:
    return get_store(db).get_audit_trail(consultation_id)
