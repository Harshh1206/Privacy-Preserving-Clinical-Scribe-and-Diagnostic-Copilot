from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.schemas import Claim, SOAPNote, SOAPSection, TeamBIngest, TeamBIngestResponse, TeamBResponse
from app.services.errors import bad_request
from app.services.store import get_store
from app.database import get_db

router = APIRouter(prefix="/api/team-b", tags=["team-b"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _to_soap_note(payload: TeamBResponse, consultation_id: str, soap_note_id: str) -> SOAPNote:
    timestamp = _now()
    return SOAPNote(
        id=soap_note_id,
        consultation_id=consultation_id,
        subjective=SOAPSection(text=payload.soap_note.subjective),
        objective=SOAPSection(text=payload.soap_note.objective),
        assessment=SOAPSection(text=payload.soap_note.assessment),
        plan=SOAPSection(text=payload.soap_note.plan),
        created_at=timestamp,
        updated_at=timestamp,
    )


def _to_conflict_claims(payload: TeamBResponse, consultation_id: str) -> list[Claim]:
    return [
        Claim(
            id=f"tb-{consultation_id}-conflict-{index}",
            soap_section="plan",
            text=conflict.message,
            status="conflict",
            severity=conflict.severity.lower(),
            evidence_ids=[],
            conflict_description=conflict.message,
            conflicting_entities=[conflict.allergy, conflict.medication],
        )
        for index, conflict in enumerate(payload.conflicts, start=1)
    ]


@router.post("/ingest/{consultation_id}", response_model=TeamBIngestResponse)
def ingest_official_team_b(consultation_id: str, payload: TeamBResponse, db: Session = Depends(get_db)) -> TeamBIngestResponse:
    store = get_store(db)
    consultation = store.get_consultation(consultation_id)
    patient_info = payload.patient_info
    demographic_updates = {
        field: str(patient_info.demographics[field])
        for field in ("first_name", "last_name", "dob", "phone")
        if field in patient_info.demographics and patient_info.demographics[field] is not None
    }
    store.update_patient_from_team_b(
        consultation_id,
        {
            **demographic_updates,
            "allergies": patient_info.allergies,
            "medications": patient_info.medications,
        },
    )
    con, soap, validation = store.ingest_team_b(
        consultation_id=consultation_id,
        soap=_to_soap_note(payload, consultation_id, consultation.soap_note_id),
        claims=_to_conflict_claims(payload, consultation_id),
        evidence=[],
        entities=[],
        transcript=None,
        safety_status=payload.safety_status,
    )
    return TeamBIngestResponse(consultation=con, soap_note=soap, validation=validation, entities=[])


@router.post("/ingest", response_model=TeamBIngestResponse)
def ingest_team_b(payload: TeamBIngest, db: Session = Depends(get_db)) -> TeamBIngestResponse:
    if payload.consultation_id != payload.soap_note.consultation_id:
        raise bad_request("soapNote.consultationId must match consultationId")
    store = get_store(db)
    con, soap, validation = store.ingest_team_b(
        consultation_id=payload.consultation_id,
        soap=payload.soap_note,
        claims=payload.claims,
        evidence=payload.evidence,
        entities=payload.entities,
        transcript=payload.transcript,
    )
    return TeamBIngestResponse(
        consultation=con,
        soap_note=soap,
        validation=validation,
        entities=store.get_entities(payload.consultation_id),
    )
