import base64
import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.database_models import (
    Consultation,
    EvidenceRecord,
    Patient,
    SOAPNote,
    Transcript,
    TranscriptEntry,
    ValidationClaim,
    ValidationResult,
)
from app.main import app


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


@pytest.fixture
def qa_record():
    suffix = _suffix()
    ids = {
        "patient": f"qa-patient-{suffix}",
        "consultation": f"qa-con-{suffix}",
        "transcript": f"qa-tx-{suffix}",
        "soap": f"qa-soap-{suffix}",
        "validation": f"qa-val-{suffix}",
        "mrn": f"QA-MRN-{suffix}",
    }
    db = SessionLocal()
    try:
        patient = Patient(
            id=ids["patient"],
            mrn=ids["mrn"],
            first_name="QA",
            last_name=f"Synthetic-{suffix}",
            dob="1990-01-01",
            sex="O",
            phone=None,
            allergies=[],
            conditions=["Synthetic test condition"],
            medications=[],
            last_visit=None,
            consultation_count=1,
            privacy_level="standard",
        )
        consultation = Consultation(
            id=ids["consultation"],
            patient_id=ids["patient"],
            date="2026-10-31T09:00:00Z",
            chief_complaint="Synthetic QA encounter",
            status="pending-review",
            physician_id="dr-001",
            physician_name="Dr. Sarah Chen",
            transcript_id=ids["transcript"],
            soap_note_id=ids["soap"],
            validation_id=ids["validation"],
            created_at="2026-10-31T09:00:00Z",
            updated_at="2026-10-31T09:00:00Z",
            safety_status="CLEAR",
        )
        transcript = Transcript(
            id=ids["transcript"],
            consultation_id=ids["consultation"],
            recorded_at="2026-10-31T09:00:00Z",
            duration_ms=1000,
            language="en-US",
        )
        entry = TranscriptEntry(
            id=f"qa-entry-{suffix}",
            transcript_id=ids["transcript"],
            consultation_id=ids["consultation"],
            timestamp="00:00:01",
            offset_ms=1000,
            speaker="Patient",
            speaker_role="patient",
            text="Synthetic QA symptom: headache is improving.",
            linked_claim_ids=[],
            confidence=1.0,
        )
        soap = SOAPNote(
            id=ids["soap"],
            consultation_id=ids["consultation"],
            subjective={"text": "Synthetic QA subjective"},
            objective={"text": "Synthetic QA objective"},
            assessment={"text": "Synthetic QA assessment"},
            plan={"text": "Synthetic QA plan"},
            created_at="2026-10-31T09:00:00Z",
            updated_at="2026-10-31T09:00:00Z",
            is_finalized=False,
            version=1,
        )
        validation = ValidationResult(
            id=ids["validation"],
            consultation_id=ids["consultation"],
            soap_note_version=1,
            grounding_score=100,
            hallucination_risk="low",
            supported_count=1,
            unsupported_count=0,
            conflict_count=0,
            total_claim_count=1,
            is_stale=False,
            validated_at="2026-10-31T09:00:00Z",
            validation_notes="Synthetic QA validation",
        )
        claim = ValidationClaim(
            id=f"qa-claim-{suffix}",
            validation_id=ids["validation"],
            soap_section="assessment",
            text="Synthetic QA assessment",
            status="supported",
            severity="low",
            evidence_ids=[],
        )
        evidence = EvidenceRecord(
            id=f"qa-evidence-{suffix}",
            validation_id=ids["validation"],
            transcript_entry_id=entry.id,
            transcript_text=entry.text,
            speaker=entry.speaker,
            timestamp=entry.timestamp,
            relevance_score=1.0,
            match_type="exact",
        )
        db.add_all([patient, consultation, transcript, entry, soap, validation, claim, evidence])
        db.commit()
        yield ids
    finally:
        db = SessionLocal()
        try:
            consultation = db.get(Consultation, ids["consultation"])
            if consultation is not None:
                soap = db.get(SOAPNote, ids["soap"])
                validation = db.get(ValidationResult, ids["validation"])
                transcript = db.get(Transcript, ids["transcript"])
                if validation is not None:
                    db.delete(validation)
                if soap is not None:
                    db.delete(soap)
                if transcript is not None:
                    db.delete(transcript)
                db.flush()
                db.delete(consultation)
            patient = db.get(Patient, ids["patient"])
            if patient is not None:
                db.delete(patient)
            db.commit()
        finally:
            db.close()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_database_status(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


@pytest.mark.parametrize("path,response_status", [
    ("/api/patients/not-a-real-patient", 404),
    ("/api/consultations/not-a-real-consultation", 404),
    ("/api/transcripts/not-a-real-transcript", 404),
    ("/api/validations/not-a-real-validation", 404),
    ("/api/soap-notes/not-a-real-soap", 404),
])
def test_unknown_record_ids(client, path, response_status):
    response = client.get(path)
    assert response.status_code == response_status
    assert isinstance(response.json().get("detail"), str)


@pytest.mark.parametrize("path", [
    "/api/patients",
    "/api/consultations",
])
def test_read_lists_are_postgresql_backed(client, qa_record, path):
    response = client.get(path)
    assert response.status_code == 200
    records = response.json()
    assert isinstance(records, list)
    if path.endswith("/patients"):
        assert any(record["id"] == qa_record["patient"] for record in records)
    else:
        assert any(record["id"] == qa_record["consultation"] for record in records)


def test_patient_consultation_transcript_soap_validation_relationships(client, qa_record):
    patient = client.get(f"/api/patients/{qa_record['patient']}")
    consultation = client.get(f"/api/consultations/{qa_record['consultation']}")
    transcript = client.get(f"/api/transcripts/{qa_record['transcript']}")
    soap = client.get(f"/api/soap-notes/{qa_record['soap']}")
    validation = client.get(f"/api/validations/{qa_record['validation']}")
    assert patient.status_code == consultation.status_code == 200
    assert consultation.json()["patientId"] == qa_record["patient"]
    assert transcript.status_code == 200
    assert transcript.json()["consultationId"] == qa_record["consultation"]
    assert transcript.json()["entries"][0]["text"].startswith("Synthetic QA")
    assert soap.status_code == 200
    assert soap.json()["consultationId"] == qa_record["consultation"]
    assert validation.status_code == 200
    assert validation.json()["consultationId"] == qa_record["consultation"]
    assert validation.json()["totalClaimCount"] == 1


def test_consultation_filter_and_audit(client, qa_record):
    filtered = client.get("/api/consultations", params={"patientId": qa_record["patient"]})
    assert filtered.status_code == 200
    assert all(record["patientId"] == qa_record["patient"] for record in filtered.json())
    audit = client.get(f"/api/consultations/{qa_record['consultation']}/audit")
    assert audit.status_code == 200
    assert isinstance(audit.json(), list)


def test_unknown_consultation_actions(client):
    assert client.post("/api/consultations/not-a-real-consultation/validate").status_code == 404
    assert client.post(
        "/api/consultations/not-a-real-consultation/finalize",
        json={"physicianId": "qa", "physicianName": "QA Physician"},
    ).status_code == 404
    assert client.get("/api/consultations/not-a-real-consultation/audit").status_code == 404


def test_soap_patch_persists_in_separate_session(client, qa_record):
    response = client.patch(
        f"/api/soap-notes/{qa_record['soap']}",
        json={"plan": {"text": "Synthetic QA updated plan", "lastEditedBy": "QA Engineer"}},
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["version"] == 2
    assert updated["plan"]["text"] == "Synthetic QA updated plan"
    db = SessionLocal()
    try:
        row = db.get(SOAPNote, qa_record["soap"])
        assert row is not None
        assert row.plan["text"] == "Synthetic QA updated plan"
        assert row.version == 2
    finally:
        db.close()


@pytest.mark.parametrize("payload", [
    {"plan": {}},
    {"plan": {"text": 123}},
])
def test_invalid_soap_patch_shapes(client, qa_record, payload):
    response = client.patch(f"/api/soap-notes/{qa_record['soap']}", json=payload)
    assert response.status_code == 422


def test_empty_soap_patch_is_valid_noop(client, qa_record):
    response = client.patch(f"/api/soap-notes/{qa_record['soap']}", json={})
    assert response.status_code == 200


def test_malformed_soap_json(client, qa_record):
    response = client.patch(
        f"/api/soap-notes/{qa_record['soap']}",
        content=b"{",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 422


def test_finalize_repeat_and_locked_edits(client, qa_record):
    first = client.post(
        f"/api/consultations/{qa_record['consultation']}/finalize",
        json={"physicianId": "qa-physician", "physicianName": "QA Physician"},
    )
    assert first.status_code == 200
    assert first.json()["soapNote"]["isFinalized"] is True
    assert first.json()["consultation"]["status"] == "finalized"
    second = client.post(
        f"/api/consultations/{qa_record['consultation']}/finalize",
        json={"physicianId": "qa-physician", "physicianName": "QA Physician"},
    )
    assert second.status_code == 409
    blocked_patch = client.patch(
        f"/api/soap-notes/{qa_record['soap']}",
        json={"plan": {"text": "Must remain blocked"}},
    )
    assert blocked_patch.status_code == 409
    blocked_validation = client.post(f"/api/consultations/{qa_record['consultation']}/validate")
    assert blocked_validation.status_code == 409


def test_finalize_missing_fields(client, qa_record):
    response = client.post(
        f"/api/consultations/{qa_record['consultation']}/finalize",
        json={"physicianName": "QA Physician"},
    )
    assert response.status_code == 422


def test_pdf_export_contract_and_audit(client, qa_record):
    response = client.post("/api/exports/pdf", json={
        "consultationId": qa_record["consultation"],
        "format": "pdf",
        "includeTranscript": True,
        "includeValidation": True,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["format"] == "pdf"
    raw = base64.b64decode(body["content"], validate=True)
    assert raw.startswith(b"%PDF")
    audit = client.get(f"/api/consultations/{qa_record['consultation']}/audit").json()
    assert any(entry["action"] == "exported" for entry in audit)


def test_fhir_export_required_fields(client, qa_record):
    response = client.post("/api/exports/fhir", json={
        "consultationId": qa_record["consultation"],
        "format": "fhir",
        "includeTranscript": True,
        "includeValidation": True,
    })
    assert response.status_code == 200
    body = response.json()
    resource = json.loads(body["content"])
    assert resource["resourceType"] == "Composition"
    assert resource["status"] in {"preliminary", "final"}
    assert resource["subject"]["reference"] == f"Patient/{qa_record['patient']}"
    assert len(resource["section"]) >= 4


def test_mock_ehr_export_contract(client, qa_record):
    response = client.post("/api/exports/ehr", json={
        "consultationId": qa_record["consultation"],
        "format": "ehr",
        "includeTranscript": False,
        "includeValidation": True,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["confirmationId"].startswith("EHR-MOCK-")
    assert "Mock EHR" in body["message"]
    audit = client.get(f"/api/consultations/{qa_record['consultation']}/audit").json()
    assert any(entry["action"] == "sent_to_ehr" for entry in audit)


@pytest.mark.parametrize("payload", [
    {"consultationId": "qa-missing", "format": "pdf"},
    {"consultationId": "qa-missing", "format": "not-a-format"},
])
def test_export_validation_and_missing_data(client, payload):
    endpoint = "/api/exports/pdf"
    response = client.post(endpoint, json=payload)
    assert response.status_code in {404, 422}


def test_legacy_team_b_ingest_persists(client, qa_record):
    soap = client.get(f"/api/soap-notes/{qa_record['soap']}").json()
    payload = {
        "consultationId": qa_record["consultation"],
        "soapNote": soap,
        "entities": [{"id": f"qa-ent-{_suffix()}", "text": "Synthetic symptom", "type": "symptom"}],
        "claims": [{
            "id": f"qa-tb-{_suffix()}",
            "soapSection": "assessment",
            "text": "Synthetic Team B assessment",
            "status": "supported",
            "severity": "low",
            "evidenceIds": [],
        }],
        "evidence": [],
        "transcript": None,
    }
    response = client.post("/api/team-b/ingest", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["consultation"]["id"] == qa_record["consultation"]
    assert body["soapNote"]["consultationId"] == qa_record["consultation"]
    assert body["validation"]["consultationId"] == qa_record["consultation"]
    db = SessionLocal()
    try:
        assert db.get(Consultation, qa_record["consultation"]) is not None
        assert db.get(SOAPNote, qa_record["soap"]) is not None
        assert db.get(ValidationResult, qa_record["validation"]) is not None
    finally:
        db.close()


def test_legacy_team_b_mismatched_ids(client, qa_record):
    soap = client.get(f"/api/soap-notes/{qa_record['soap']}").json()
    payload = {
        "consultationId": qa_record["consultation"],
        "soapNote": {**soap, "consultationId": "qa-different-consultation"},
        "entities": [],
        "claims": [],
        "evidence": [],
    }
    response = client.post("/api/team-b/ingest", json=payload)
    assert response.status_code == 400


@pytest.mark.parametrize("payload", [
    {},
    {"consultationId": "qa-missing", "soapNote": {}},
    {"consultationId": "qa-missing", "soapNote": {}, "entities": "not-a-list"},
])
def test_legacy_team_b_invalid_payload(client, payload):
    response = client.post("/api/team-b/ingest", json=payload)
    assert response.status_code == 422


def test_legacy_team_b_unknown_consultation(client, qa_record):
    payload = {
        "consultationId": "not-a-real-consultation",
        "soapNote": {
            "id": "not-a-real-soap",
            "consultationId": "not-a-real-consultation",
            "subjective": {"text": ""},
            "objective": {"text": ""},
            "assessment": {"text": ""},
            "plan": {"text": ""},
            "createdAt": "2026-10-31T09:00:00Z",
            "updatedAt": "2026-10-31T09:00:00Z",
        },
    }
    response = client.post("/api/team-b/ingest", json=payload)
    assert response.status_code == 404


def test_official_team_b_ingest(client, qa_record):
    payload = {
        "patientInfo": {
            "demographics": {"firstName": "QA", "lastName": "Updated-Synthetic"},
            "allergies": ["Synthetic Allergy"],
            "medications": ["Synthetic Medication"],
        },
        "soapNote": {
            "subjective": "Official synthetic subjective",
            "objective": "Official synthetic objective",
            "assessment": "Official synthetic assessment",
            "plan": "Official synthetic plan",
        },
        "conflicts": [],
        "safetyStatus": "CLEAR",
    }
    response = client.post(
        f"/api/team-b/ingest/{qa_record['consultation']}",
        json=payload,
    )
    assert response.status_code == 200
    assert response.json()["soapNote"]["plan"]["text"] == "Official synthetic plan"


def test_official_team_b_invalid_payload(client, qa_record):
    response = client.post(
        f"/api/team-b/ingest/{qa_record['consultation']}",
        json={"soapNote": [], "conflicts": "invalid"},
    )
    assert response.status_code == 422


def test_official_team_b_unknown_consultation(client):
    response = client.post(
        "/api/team-b/ingest/not-a-real-consultation",
        json={"patientInfo": {}, "soapNote": {}, "conflicts": [], "safetyStatus": "CLEAR"},
    )
    assert response.status_code == 404


def test_malformed_team_b_json(client):
    response = client.post(
        "/api/team-b/ingest",
        content=b"{",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 422


def test_database_unique_and_foreign_key_constraints():
    suffix = _suffix()
    db = SessionLocal()
    patient_id = f"qa-unique-{suffix}"
    mrn = f"QA-UNIQUE-{suffix}"
    try:
        db.add(Patient(
            id=patient_id, mrn=mrn, first_name="QA", last_name="Unique",
            dob="1990-01-01", sex="O",
        ))
        db.commit()
        db.add(Patient(
            id=f"qa-unique-2-{suffix}", mrn=mrn, first_name="QA", last_name="Duplicate",
            dob="1990-01-01", sex="O",
        ))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        db.add(Consultation(
            id=f"qa-bad-con-{suffix}",
            patient_id="patient-that-does-not-exist",
            date="2026-10-31T09:00:00Z",
            chief_complaint="QA constraint test",
            status="pending-review",
            physician_id="qa",
            physician_name="QA",
            created_at="2026-10-31T09:00:00Z",
            updated_at="2026-10-31T09:00:00Z",
        ))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        existing = db.get(Patient, patient_id)
        if existing is not None:
            db.delete(existing)
        db.commit()
        db.close()


def test_seed_tables_relationships_and_migration_state():
    db = SessionLocal()
    try:
        table_count = db.execute(text(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        )).scalar_one()
        assert table_count >= 12
        patients = db.execute(text("SELECT count(*) FROM patients")).scalar_one()
        consultations = db.execute(text("SELECT count(*) FROM consultations")).scalar_one()
        assert patients >= 3
        assert consultations >= 4
    finally:
        db.close()
