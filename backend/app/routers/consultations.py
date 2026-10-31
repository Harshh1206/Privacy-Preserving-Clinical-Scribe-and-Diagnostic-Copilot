from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.models.schemas import (
    AuditEntry,
    Consultation,
    FinalizeRequest,
    FinalizeResponse,
    ValidationResult,
)
from app.services.store import get_store
from app.database import get_db

router = APIRouter(prefix="/api/consultations", tags=["consultations"])


@router.get("", response_model=list[Consultation])
def list_consultations(patient_id: Optional[str] = Query(default=None, alias="patientId"), db: Session = Depends(get_db)) -> list[Consultation]:
    return get_store(db).list_consultations(patient_id)


@router.get("/{consultation_id}", response_model=Consultation)
def get_consultation(consultation_id: str, db: Session = Depends(get_db)) -> Consultation:
    return get_store(db).get_consultation(consultation_id)


@router.post("/{consultation_id}/validate", response_model=ValidationResult)
def validate_consultation(consultation_id: str, db: Session = Depends(get_db)) -> ValidationResult:
    return get_store(db).validate_consultation(consultation_id)


@router.post("/{consultation_id}/finalize", response_model=FinalizeResponse)
def finalize_consultation(consultation_id: str, body: FinalizeRequest, db: Session = Depends(get_db)) -> FinalizeResponse:
    consultation, soap_note = get_store(db).finalize(
        consultation_id, body.physician_id, body.physician_name
    )
    return FinalizeResponse(consultation=consultation, soap_note=soap_note)


@router.get("/{consultation_id}/audit", response_model=list[AuditEntry])
def get_audit_trail(consultation_id: str, db: Session = Depends(get_db)) -> list[AuditEntry]:
    return get_store(db).get_audit_trail(consultation_id)
