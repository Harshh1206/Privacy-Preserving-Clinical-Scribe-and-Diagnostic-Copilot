import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.schemas import EHRResult, ExportRequest, ExportResult
from app.services.fhir import build_fhir_composition
from app.services.pdf import pdf_base64
from app.services.store import get_store
from app.config import settings
from app.database import get_db

router = APIRouter(prefix="/api/exports", tags=["exports"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@router.post("/pdf", response_model=ExportResult)
def export_pdf(req: ExportRequest, db: Session = Depends(get_db)) -> ExportResult:
    store = get_store(db)
    con = store.get_consultation(req.consultation_id)
    patient = store.get_patient(con.patient_id)
    soap = store.get_soap(con.soap_note_id)
    validation = store.get_validation(con.validation_id) if con.validation_id else None
    transcript = store.get_transcript(con.transcript_id) if con.transcript_id else None
    content = pdf_base64(
        consultation=con,
        patient=patient,
        soap=soap,
        validation=validation,
        transcript=transcript,
        include_transcript=req.include_transcript,
        include_validation=req.include_validation,
    )
    filename = f"ClinicalNote_{patient.last_name}_{req.consultation_id}_{int(datetime.now().timestamp() * 1000)}.pdf"
    store.add_audit(
        req.consultation_id,
        "exported",
        settings.default_physician_name,
        f"Exported PDF: {filename} (transcript: {req.include_transcript}, validation: {req.include_validation}).",
        soap.version,
    )
    return ExportResult(format="pdf", filename=filename, content=content, generated_at=_now())


@router.post("/fhir", response_model=ExportResult)
def export_fhir(req: ExportRequest, db: Session = Depends(get_db)) -> ExportResult:
    store = get_store(db)
    con = store.get_consultation(req.consultation_id)
    patient = store.get_patient(con.patient_id)
    soap = store.get_soap(con.soap_note_id)
    validation = store.get_validation(con.validation_id) if con.validation_id else None
    transcript = store.get_transcript(con.transcript_id) if con.transcript_id else None
    resource = build_fhir_composition(
        con, patient, soap, validation, transcript, req.include_transcript, req.include_validation
    )
    filename = f"FHIR_{req.consultation_id}_{int(datetime.now().timestamp() * 1000)}.json"
    store.add_audit(
        req.consultation_id,
        "exported",
        settings.default_physician_name,
        f"Exported FHIR Composition: {filename}.",
        soap.version,
    )
    return ExportResult(
        format="fhir",
        filename=filename,
        content=json.dumps(resource, indent=2),
        generated_at=_now(),
    )


@router.post("/ehr", response_model=EHRResult)
def send_to_ehr(req: ExportRequest, db: Session = Depends(get_db)) -> EHRResult:
    store = get_store(db)
    con = store.get_consultation(req.consultation_id)
    confirmation = f"EHR-MOCK-{int(datetime.now().timestamp() * 1000)}"
    store.add_audit(
        req.consultation_id,
        "sent_to_ehr",
        settings.default_physician_name,
        f"MOCK: Note sent to EHR system. Confirmation ID: {confirmation}.",
    )
    return EHRResult(
        success=True,
        confirmation_id=confirmation,
        message=(
            f"Note for consultation {req.consultation_id} successfully transmitted to Mock EHR. "
            f"Patient: {con.patient_id}."
        ),
    )
