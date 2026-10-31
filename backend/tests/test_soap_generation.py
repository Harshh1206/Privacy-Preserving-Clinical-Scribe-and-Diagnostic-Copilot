import json
import sys
import types
import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database import SessionLocal
from app.database_models import Consultation, Patient, SOAPNote, Transcript, TranscriptEntry
from app.main import app
from app.models.schemas import Transcript as TranscriptSchema
from app.services.soap_generation import GeneratedSOAP, GroqSOAPGenerator, SOAPGenerationError
from app.services.store import reset_store


@pytest.fixture()
def client():
    reset_store()
    with TestClient(app) as c:
        yield c
    reset_store()


def test_generated_soap_model_requires_all_sections():
    with pytest.raises(Exception):
        GeneratedSOAP.model_validate({
            "subjective": "Headache for two days.",
            "objective": "Not documented in the transcript.",
            "assessment": "Not documented in the transcript.",
        })


def test_generate_soap_rejects_invalid_json(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "test-key", raising=False)

    class FakeCompletions:
        def create(self, **kwargs):
            message = types.SimpleNamespace(content="not json")
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])

    class FakeGroq:
        def __init__(self, api_key, **kwargs):
            assert api_key == "test-key"
            self.chat = types.SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setitem(sys.modules, "groq", types.SimpleNamespace(Groq=FakeGroq))
    transcript = TranscriptSchema(
        id="tx-test",
        consultationId="con-test",
        entries=[],
        recordedAt="2026-10-31T09:00:00Z",
        durationMs=1000,
        processingStatus="completed",
    )

    with pytest.raises(SOAPGenerationError, match="invalid JSON"):
        GroqSOAPGenerator().generate(transcript)


def test_generate_soap_maps_timeout(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "test-key", raising=False)

    class FakeCompletions:
        def create(self, **kwargs):
            raise TimeoutError("provider timeout")

    class FakeGroq:
        def __init__(self, api_key, **kwargs):
            self.chat = types.SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setitem(sys.modules, "groq", types.SimpleNamespace(Groq=FakeGroq))
    transcript = TranscriptSchema(
        id="tx-test",
        consultationId="con-test",
        entries=[],
        recordedAt="2026-10-31T09:00:00Z",
        durationMs=1000,
        processingStatus="completed",
    )

    with pytest.raises(SOAPGenerationError, match="timed out"):
        GroqSOAPGenerator().generate(transcript)


@pytest.mark.parametrize("content", [
    '```json\n{"Subjective":"Patient reports headache.","Objective":"Not documented.","Assessment":"Not documented.","Plan":"No specific plan was documented.","clinicalData":{"conditions":null,"medications":[{"name":"Metformin","verification":null}]}}\n```',
    '{"subjective":"Patient reports headache.","objective":"Not documented.","assessment":"Not documented.","plan":"No specific plan was documented.","clinicalData":{"conditions":[{"name":"Type 2 diabetes","verification":"reported"}],"measurements":[{"name":"Glucose","value":192,"unit":"mg/dL","source":null}]}}',
])
def test_generate_soap_normalizes_harmless_formatting_and_extracts_clinical_data(monkeypatch, content):
    monkeypatch.setattr(settings, "groq_api_key", "test-key", raising=False)

    class FakeCompletions:
        def create(self, **kwargs):
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(
                    message=types.SimpleNamespace(content=content)
                )]
            )

    class FakeGroq:
        def __init__(self, api_key, **kwargs):
            self.chat = types.SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setitem(sys.modules, "groq", types.SimpleNamespace(Groq=FakeGroq))
    transcript = TranscriptSchema(
        id="tx-test",
        consultationId="con-test",
        entries=[],
        recordedAt="2026-10-31T09:00:00Z",
        durationMs=1000,
        processingStatus="completed",
    )

    generated = GroqSOAPGenerator().generate(transcript)
    assert generated.subjective
    assert generated.objective
    assert generated.assessment
    assert generated.plan
    assert isinstance(generated.clinical_data.conditions, list)


@pytest.mark.parametrize("payload, error_match", [
    ({"subjective": "Reported headache", "objective": "", "assessment": "Not documented", "plan": "Not documented"}, "invalid SOAP structure"),
    ({"subjective": "Reported headache", "objective": "Not documented", "assessment": "Not documented"}, "invalid SOAP structure"),
    ({"subjective": None, "objective": "Not documented", "assessment": "Not documented", "plan": "Not documented"}, "invalid SOAP structure"),
])
def test_generate_soap_rejects_missing_empty_or_null_sections(monkeypatch, payload, error_match):
    monkeypatch.setattr(settings, "groq_api_key", "test-key", raising=False)

    class FakeCompletions:
        def create(self, **kwargs):
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(
                    message=types.SimpleNamespace(content=json.dumps(payload))
                )]
            )

    class FakeGroq:
        def __init__(self, api_key, **kwargs):
            self.chat = types.SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setitem(sys.modules, "groq", types.SimpleNamespace(Groq=FakeGroq))
    transcript = TranscriptSchema(
        id="tx-test",
        consultationId="con-test",
        entries=[],
        recordedAt="2026-10-31T09:00:00Z",
        durationMs=1000,
        processingStatus="completed",
    )

    with pytest.raises(SOAPGenerationError, match=error_match):
        GroqSOAPGenerator().generate(transcript)


def test_generate_soap_endpoint_persists_generated_sections(client, monkeypatch):
    generated = GeneratedSOAP(
        subjective="Patient reports headache without fever.",
        objective="Not documented in the transcript.",
        assessment="Not documented in the transcript.",
        plan="No treatment plan was documented in the transcript.",
    )

    class FakeGenerator:
        def generate(self, transcript):
            assert transcript.id == "tx-001"
            return generated

    monkeypatch.setattr(
        "app.routers.consultations.GroqSOAPGenerator",
        FakeGenerator,
    )

    response = client.post("/api/consultations/con-001/generate-soap")

    assert response.status_code == 200
    body = response.json()
    assert body["consultationId"] == "con-001"
    assert body["subjective"]["text"] == generated.subjective
    assert body["objective"]["text"] == generated.objective
    assert body["assessment"]["text"] == generated.assessment
    assert body["plan"]["text"] == generated.plan
    assert body["version"] == 2

    persisted = client.get(f"/api/soap-notes/{body['id']}")
    assert persisted.status_code == 200
    assert persisted.json()["subjective"]["text"] == generated.subjective


def test_generated_clinical_data_updates_patient_without_duplicate_records(client, monkeypatch):
    generated = GeneratedSOAP(
        subjective="Type 2 diabetes diagnosed three years ago. Blood glucose was 192 mg/dL; amoxicillin caused a rash.",
        objective="Blood pressure 150/96 mmHg and pulse 94 bpm in clinic.",
        assessment="Type 2 diabetes and hypertension, both reported for clinician review.",
        plan="No treatment or follow-up plan was documented in the transcript.",
        clinicalData={
            "conditions": [
                {"name": "Type 2 diabetes", "status": "reported", "verification": "reported"},
                {"name": "High blood pressure", "status": "reported", "verification": "reported"},
            ],
            "medications": [
                {"name": "Metformin", "dose": "500 mg", "frequency": "twice daily", "status": "reported_current", "verification": "reported"},
                {"name": "Amlodipine", "dose": "5 mg", "frequency": "once daily", "status": "reported_current", "verification": "reported"},
            ],
            "measurements": [
                {"name": "Blood glucose", "value": "192", "unit": "mg/dL", "source": "patient_reported", "verification": "reported"},
                {"name": "Blood pressure", "value": "150/96", "unit": "mmHg", "source": "clinic_measured", "verification": "reported"},
                {"name": "Pulse", "value": "94", "unit": "bpm", "source": "clinic_measured", "verification": "reported"},
            ],
            "allergies": [
                {"substance": "Amoxicillin", "reaction": "skin rash", "verification": "reported"},
            ],
        },
    )

    class FakeGenerator:
        def generate(self, transcript):
            return generated

    monkeypatch.setattr("app.routers.consultations.GroqSOAPGenerator", FakeGenerator)

    first = client.post("/api/consultations/con-001/generate-soap")
    second = client.post("/api/consultations/con-001/generate-soap")
    assert first.status_code == 200
    assert second.status_code == 200

    patient = client.get("/api/patients/pt-001")
    assert patient.status_code == 200
    body = patient.json()
    assert any("Type 2 diabetes" in item for item in body["conditions"])
    assert any("Metformin" in item for item in body["medications"])
    assert any("Amoxicillin" in item for item in body["allergies"])

    records = body["clinicalRecords"]
    measurement_names = [(record["name"], record["source"], record["value"], record["unit"]) for record in records if record["category"] == "measurement"]
    assert ("Blood glucose", "patient_reported", "192", "mg/dL") in measurement_names
    assert ("Blood pressure", "clinic_measured", "150/96", "mmHg") in measurement_names
    allergy = next(record for record in records if record["category"] == "allergy")
    assert allergy["name"] == "Amoxicillin"
    assert allergy["reaction"] == "skin rash"
    assert allergy["verification"] == "reported"

    diabetes_records = [record for record in records if record["category"] == "condition" and record["name"] == "Type 2 diabetes"]
    assert len(diabetes_records) == 1


def test_generate_soap_endpoint_returns_safe_bad_gateway(client, monkeypatch):
    class FakeGenerator:
        def generate(self, transcript):
            raise SOAPGenerationError("SOAP generation service is unavailable.")

    monkeypatch.setattr(
        "app.routers.consultations.GroqSOAPGenerator",
        FakeGenerator,
    )

    response = client.post("/api/consultations/con-001/generate-soap")

    assert response.status_code == 502
    assert response.json()["detail"] == "SOAP generation service is unavailable."


def test_generate_soap_endpoint_rejects_empty_or_unprocessed_transcript(client):
    suffix = uuid.uuid4().hex[:10]
    patient_id = None
    consultation_id = None
    try:
        created = client.post("/api/patients", json={
            "mrn": f"TEST-SOAP-{suffix}",
            "firstName": "SOAP",
            "lastName": "Test",
            "dob": "1990-01-01",
            "sex": "O",
            "allergies": [],
            "conditions": [],
            "medications": [],
            "privacyLevel": "standard",
        })
        assert created.status_code == 201
        patient_id = created.json()["id"]

        consultation = client.post("/api/consultations", json={
            "patientId": patient_id,
            "chiefComplaint": "Follow-up",
            "physicianId": "dr-001",
            "physicianName": "Dr. Sarah Chen",
        })
        assert consultation.status_code == 201
        consultation_id = consultation.json()["id"]

        response = client.post(
            f"/api/consultations/{consultation_id}/generate-soap"
        )
        assert response.status_code == 409
    finally:
        db = SessionLocal()
        try:
            if consultation_id:
                db.query(TranscriptEntry).filter(
                    TranscriptEntry.consultation_id == consultation_id
                ).delete(synchronize_session=False)
                db.query(Transcript).filter(
                    Transcript.consultation_id == consultation_id
                ).delete(synchronize_session=False)
                db.query(SOAPNote).filter(
                    SOAPNote.consultation_id == consultation_id
                ).delete(synchronize_session=False)
                db.query(Consultation).filter(
                    Consultation.id == consultation_id
                ).delete(synchronize_session=False)
            if patient_id:
                db.query(Patient).filter(Patient.id == patient_id).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()
