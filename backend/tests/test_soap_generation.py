import json
import sys
import threading
import types
import uuid

import pytest
import httpx
from fastapi.testclient import TestClient

from app.config import settings
from app.database import SessionLocal
from app.database_models import Consultation, Patient, SOAPNote, Transcript, TranscriptEntry
from app.main import app
from app.models.schemas import (
    ClinicalData,
    Transcript as TranscriptSchema,
    TranscriptEntry as TranscriptEntrySchema,
)
from app.services.soap_generation import (
    AGENT_AP_SYSTEM_PROMPT,
    AGENT_SO_SYSTEM_PROMPT,
    GeneratedSOAP,
    OllamaSOAPGenerator,
    SOAPGenerationError,
    _merge_clinical_data,
    _parse_clinical_extraction_payload,
)
from app.services.store import reset_store


# ---------------------------------------------------------------------------
# Shared test helpers for the two-agent architecture
# ---------------------------------------------------------------------------

_VALID_SO_PAYLOAD = json.dumps({
    "subjective": "Patient reports persistent headache for two days.",
    "objective": "Blood pressure 130/85 mmHg. Pulse 78 bpm.",
})

_VALID_AP_PAYLOAD = json.dumps({
    "assessment": "Tension-type headache, reported.",
    "plan": "Rest and OTC analgesics as needed. Follow up in one week.",
})


def _make_transcript() -> TranscriptSchema:
    return TranscriptSchema(
        id="tx-test",
        consultationId="con-test",
        entries=[],
        recordedAt="2026-10-31T09:00:00Z",
        durationMs=1000,
        processingStatus="completed",
    )


def _fake_groq_for_two_agents(
    so_content: str | None = None,
    ap_content: str | None = None,
    so_exception: Exception | None = None,
    ap_exception: Exception | None = None,
):
    """Return a fake httpx client class that dispatches by agent prompt."""
    so_content = so_content if so_content is not None else _VALID_SO_PAYLOAD
    ap_content = ap_content if ap_content is not None else _VALID_AP_PAYLOAD

    class DispatchingFakeOllamaClient:
        def __init__(self, **kwargs):
            pass

        def close(self):
            pass

        def post(self, url, json):
            messages = json.get("messages", [])
            system_content = messages[0]["content"] if messages else ""
            if "Subjective and Objective" in system_content:
                if so_exception is not None:
                    raise so_exception
                content = so_content
            else:
                if ap_exception is not None:
                    raise ap_exception
                content = ap_content
            return types.SimpleNamespace(
                status_code=200,
                json=lambda: {"message": {"content": content}},
            )

    return DispatchingFakeOllamaClient


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
    FakeGroq = _fake_groq_for_two_agents(so_content="not json")
    monkeypatch.setattr("app.services.soap_generation.httpx.Client", FakeGroq)

    with pytest.raises(SOAPGenerationError, match="invalid JSON"):
        OllamaSOAPGenerator().generate(_make_transcript())


def test_generate_soap_maps_timeout(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "test-key", raising=False)
    FakeGroq = _fake_groq_for_two_agents(
        so_exception=TimeoutError("provider timeout"),
    )
    monkeypatch.setattr("app.services.soap_generation.httpx.Client", FakeGroq)

    with pytest.raises(SOAPGenerationError, match="timed out"):
        OllamaSOAPGenerator().generate(_make_transcript())


@pytest.mark.parametrize("so_content, ap_content", [
    (
        '```json\n{"Subjective":"Patient reports headache.","Objective":"Not documented.","clinicalData":{"conditions":null,"medications":[{"name":"Metformin","verification":null}]}}\n```',
        '{"Assessment":"Not documented.","Plan":"No specific plan was documented."}',
    ),
    (
        '{"subjective":"Patient reports headache.","objective":"Not documented.","clinicalData":{"conditions":[{"name":"Type 2 diabetes","verification":"reported"}],"measurements":[{"name":"Glucose","value":192,"unit":"mg/dL","source":null}]}}',
        '{"assessment":"Not documented.","plan":"No specific plan was documented."}',
    ),
])
def test_generate_soap_normalizes_harmless_formatting_and_extracts_clinical_data(monkeypatch, so_content, ap_content):
    monkeypatch.setattr(settings, "groq_api_key", "test-key", raising=False)
    FakeGroq = _fake_groq_for_two_agents(so_content=so_content, ap_content=ap_content)
    monkeypatch.setattr("app.services.soap_generation.httpx.Client", FakeGroq)

    generated = OllamaSOAPGenerator().generate(_make_transcript())
    assert generated.subjective
    assert generated.objective
    assert generated.assessment
    assert generated.plan
    assert isinstance(generated.clinical_data.conditions, list)


@pytest.mark.parametrize("so_payload, ap_payload, error_match", [
    (
        {"subjective": "Reported headache", "objective": ""},
        {"assessment": "Not documented", "plan": "Not documented"},
        "invalid SOAP structure",
    ),
    (
        {"subjective": None, "objective": "Not documented"},
        {"assessment": "Not documented", "plan": "Not documented"},
        "invalid SOAP structure",
    ),
    (
        {"subjective": "Reported headache", "objective": "Not documented"},
        {"plan": "Not documented"},
        "invalid SOAP structure",
    ),
])
def test_generate_soap_rejects_missing_empty_or_null_sections(monkeypatch, so_payload, ap_payload, error_match):
    monkeypatch.setattr(settings, "groq_api_key", "test-key", raising=False)
    FakeGroq = _fake_groq_for_two_agents(
        so_content=json.dumps(so_payload),
        ap_content=json.dumps(ap_payload),
    )
    monkeypatch.setattr("app.services.soap_generation.httpx.Client", FakeGroq)

    with pytest.raises(SOAPGenerationError, match=error_match):
        OllamaSOAPGenerator().generate(_make_transcript())


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
        "app.routers.consultations.OllamaSOAPGenerator",
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

    monkeypatch.setattr("app.routers.consultations.OllamaSOAPGenerator", FakeGenerator)

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
        "app.routers.consultations.OllamaSOAPGenerator",
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


# =========================================================================
# NEW TESTS — Two-agent parallel architecture
# =========================================================================


def test_two_agent_both_succeed(monkeypatch):
    """Both agents return valid JSON → merged GeneratedSOAP has all 4 sections."""
    monkeypatch.setattr(settings, "groq_api_key", "test-key", raising=False)
    FakeGroq = _fake_groq_for_two_agents()
    monkeypatch.setattr("app.services.soap_generation.httpx.Client", FakeGroq)

    generated = OllamaSOAPGenerator().generate(_make_transcript())
    assert generated.subjective == "Patient reports persistent headache for two days."
    assert generated.objective == "Blood pressure 130/85 mmHg. Pulse 78 bpm."
    assert generated.assessment == "Tension-type headache, reported."
    assert generated.plan == "Rest and OTC analgesics as needed. Follow up in one week."


def test_two_agent_so_agent_output_structure(monkeypatch):
    """Agent 1 returns only subjective + objective — no assessment/plan keys."""
    monkeypatch.setattr(settings, "groq_api_key", "test-key", raising=False)
    so = json.dumps({"subjective": "Chief complaint: headache.", "objective": "BP 120/80."})
    ap = json.dumps({"assessment": "Likely tension headache.", "plan": "Ibuprofen PRN."})
    FakeGroq = _fake_groq_for_two_agents(so_content=so, ap_content=ap)
    monkeypatch.setattr("app.services.soap_generation.httpx.Client", FakeGroq)

    generated = OllamaSOAPGenerator().generate(_make_transcript())
    assert generated.subjective == "Chief complaint: headache."
    assert generated.objective == "BP 120/80."


def test_two_agent_ap_agent_output_structure(monkeypatch):
    """Agent 2 returns only assessment + plan — no subjective/objective keys."""
    monkeypatch.setattr(settings, "groq_api_key", "test-key", raising=False)
    FakeGroq = _fake_groq_for_two_agents()
    monkeypatch.setattr("app.services.soap_generation.httpx.Client", FakeGroq)

    generated = OllamaSOAPGenerator().generate(_make_transcript())
    assert generated.assessment == "Tension-type headache, reported."
    assert generated.plan == "Rest and OTC analgesics as needed. Follow up in one week."


def test_two_agent_concurrent_execution(monkeypatch):
    """Both futures are submitted before either result is collected when parallel mode is enabled."""
    monkeypatch.setattr(settings, "ollama_parallel_agents", True)
    call_threads: list[str] = []

    class ThreadTrackingFakeOllamaClient:
        def __init__(self, **kwargs):
            pass

        def close(self):
            pass

        def post(self, url, json):
            call_threads.append(threading.current_thread().name)
            messages = json.get("messages", [])
            system_content = messages[0]["content"] if messages else ""
            if "Subjective and Objective" in system_content:
                content = _VALID_SO_PAYLOAD
            else:
                content = _VALID_AP_PAYLOAD
            return types.SimpleNamespace(
                status_code=200,
                json=lambda: {"message": {"content": content}},
            )

    monkeypatch.setattr("app.services.soap_generation.httpx.Client", ThreadTrackingFakeOllamaClient)
    generated = OllamaSOAPGenerator().generate(_make_transcript())
    assert generated.subjective
    assert generated.assessment
    # Three calls should have been made total: SO, AP, and clinical extractor
    assert len(call_threads) == 3


def test_clinical_extraction_payload_keeps_allergy_condition_and_medication_details():
    extracted = _parse_clinical_extraction_payload({
        "allergies": [{
            "name": "Penicillin",
            "category": "drug",
            "reaction": "skin rash",
            "status": "documented_allergies",
            "verification": "patient_reported",
        }],
        "conditions": [{
            "name": "Type 2 Diabetes Mellitus",
            "status": "active",
            "classification": "chronic",
            "duration": "approximately 6 years",
            "verification": "patient_reported",
        }],
        "medications": [{
            "name": "Metformin",
            "strength": "500 mg",
            "frequency": "twice daily",
            "status": "current",
            "verification": "patient_reported",
            "adherence": "missed two doses last week",
        }],
    })

    assert extracted.allergies[0].category == "drug"
    assert extracted.conditions[0].classification == "chronic"
    assert extracted.medications[0].strength == "500 mg"
    assert extracted.medications[0].adherence == "missed two doses last week"


def test_two_agent_so_agent_fails(monkeypatch):
    """Agent 1 raises → SOAPGenerationError, nothing persisted."""
    monkeypatch.setattr(settings, "groq_api_key", "test-key", raising=False)
    FakeGroq = _fake_groq_for_two_agents(
        so_exception=RuntimeError("Agent 1 broke"),
    )
    monkeypatch.setattr("app.services.soap_generation.httpx.Client", FakeGroq)

    with pytest.raises(SOAPGenerationError, match="failed"):
        OllamaSOAPGenerator().generate(_make_transcript())


def test_two_agent_ap_agent_fails(monkeypatch):
    """Agent 2 raises → SOAPGenerationError."""
    monkeypatch.setattr(settings, "groq_api_key", "test-key", raising=False)
    FakeGroq = _fake_groq_for_two_agents(
        ap_exception=RuntimeError("Agent 2 broke"),
    )
    monkeypatch.setattr("app.services.soap_generation.httpx.Client", FakeGroq)

    with pytest.raises(SOAPGenerationError, match="failed"):
        OllamaSOAPGenerator().generate(_make_transcript())


def test_two_agent_both_fail(monkeypatch):
    """Both agents fail → SOAPGenerationError."""
    monkeypatch.setattr(settings, "groq_api_key", "test-key", raising=False)
    FakeGroq = _fake_groq_for_two_agents(
        so_exception=RuntimeError("Agent 1 broke"),
        ap_exception=RuntimeError("Agent 2 broke"),
    )
    monkeypatch.setattr("app.services.soap_generation.httpx.Client", FakeGroq)

    with pytest.raises(SOAPGenerationError):
        OllamaSOAPGenerator().generate(_make_transcript())


def test_two_agent_timeout(monkeypatch):
    """One agent times out → SOAPGenerationError with 'timed out' message."""
    monkeypatch.setattr(settings, "groq_api_key", "test-key", raising=False)
    FakeGroq = _fake_groq_for_two_agents(
        ap_exception=TimeoutError("provider timeout"),
    )
    monkeypatch.setattr("app.services.soap_generation.httpx.Client", FakeGroq)

    with pytest.raises(SOAPGenerationError, match="timed out"):
        OllamaSOAPGenerator().generate(_make_transcript())


def test_two_agent_malformed_json_from_one_agent(monkeypatch):
    """One agent returns invalid JSON → SOAPGenerationError."""
    monkeypatch.setattr(settings, "groq_api_key", "test-key", raising=False)
    FakeGroq = _fake_groq_for_two_agents(ap_content="{not valid json!}")
    monkeypatch.setattr("app.services.soap_generation.httpx.Client", FakeGroq)

    with pytest.raises(SOAPGenerationError, match="invalid JSON"):
        OllamaSOAPGenerator().generate(_make_transcript())


def test_two_agent_empty_section(monkeypatch):
    """One agent returns empty string for a required section → SOAPGenerationError."""
    monkeypatch.setattr(settings, "groq_api_key", "test-key", raising=False)
    FakeGroq = _fake_groq_for_two_agents(
        so_content=json.dumps({"subjective": "", "objective": "BP normal."}),
    )
    monkeypatch.setattr("app.services.soap_generation.httpx.Client", FakeGroq)

    with pytest.raises(SOAPGenerationError, match="invalid SOAP structure"):
        OllamaSOAPGenerator().generate(_make_transcript())


def test_two_agent_clinical_data_merge_deduplication():
    """Clinical data from both agents merged without duplicates."""
    primary = ClinicalData.model_validate({
        "conditions": [{"name": "Type 2 diabetes", "status": "reported", "verification": "reported"}],
        "medications": [{"name": "Metformin", "dose": "500 mg", "status": "reported_current", "verification": "reported"}],
        "measurements": [{"name": "Blood glucose", "value": "192", "unit": "mg/dL", "source": "patient_reported", "verification": "reported"}],
        "allergies": [{"substance": "Penicillin", "reaction": "rash", "verification": "reported"}],
    })
    secondary = ClinicalData.model_validate({
        "conditions": [
            {"name": "Type 2 diabetes", "status": "active", "verification": "confirmed"},  # duplicate
            {"name": "Hypertension", "status": "reported", "verification": "reported"},  # new
        ],
        "medications": [{"name": "Metformin", "dose": "1000 mg", "status": "current", "verification": "confirmed"}],  # dup
        "measurements": [],
        "allergies": [{"substance": "Penicillin", "verification": "confirmed"}],  # dup
    })

    merged = _merge_clinical_data(primary, secondary)
    # Conditions: primary's "Type 2 diabetes" kept (first seen), plus new "Hypertension"
    assert len(merged.conditions) == 2
    assert merged.conditions[0].name == "Type 2 diabetes"
    assert merged.conditions[0].status == "reported"  # primary wins
    assert merged.conditions[1].name == "Hypertension"
    # Medications: primary's "Metformin" kept (first seen)
    assert len(merged.medications) == 1
    assert merged.medications[0].dose == "500 mg"  # primary wins
    # Measurements: only from primary
    assert len(merged.measurements) == 1
    # Allergies: deduplicated
    assert len(merged.allergies) == 1
    assert merged.allergies[0].reaction == "rash"  # primary wins


def test_two_agent_negation_preserved(monkeypatch):
    """Patient denies fever → preserved as denial, not converted."""
    monkeypatch.setattr(settings, "groq_api_key", "test-key", raising=False)
    so = json.dumps({
        "subjective": "Patient denies fever, chills, or night sweats.",
        "objective": "Temperature 98.6 degrees F. No lymphadenopathy.",
    })
    ap = json.dumps({
        "assessment": "No infectious etiology suspected based on documented findings.",
        "plan": "Not documented in the transcript.",
    })
    FakeGroq = _fake_groq_for_two_agents(so_content=so, ap_content=ap)
    monkeypatch.setattr("app.services.soap_generation.httpx.Client", FakeGroq)

    generated = OllamaSOAPGenerator().generate(_make_transcript())
    assert "denies" in generated.subjective.lower()
    # Ensure the denial wasn't converted to a positive or removed
    assert "fever" in generated.subjective.lower()


def test_two_agent_endpoint_integration(client, monkeypatch):
    """Full endpoint test confirms SOAPNote response contract is unchanged."""
    generated = GeneratedSOAP(
        subjective="Patient reports headache without fever.",
        objective="BP 130/85 mmHg.",
        assessment="Tension headache, reported.",
        plan="OTC analgesics. Follow up in one week.",
    )

    class FakeGenerator:
        def generate(self, transcript):
            assert transcript.id == "tx-001"
            return generated

    monkeypatch.setattr(
        "app.routers.consultations.OllamaSOAPGenerator",
        FakeGenerator,
    )

    response = client.post("/api/consultations/con-001/generate-soap")
    assert response.status_code == 200
    body = response.json()
    # Verify exact response contract expected by the frontend
    assert "id" in body
    assert body["consultationId"] == "con-001"
    assert body["subjective"]["text"] == generated.subjective
    assert body["objective"]["text"] == generated.objective
    assert body["assessment"]["text"] == generated.assessment
    assert body["plan"]["text"] == generated.plan
    assert body["version"] == 2
    assert body["isFinalized"] is False
    assert "createdAt" in body
    assert "updatedAt" in body


def test_two_agent_model_not_found(monkeypatch):
    class MissingModelClient:
        def __init__(self, **kwargs):
            pass
        def close(self):
            pass
        def post(self, url, json):
            return types.SimpleNamespace(
                status_code=404,
                json=lambda: {"error": "model not found"},
            )

    monkeypatch.setattr("app.services.soap_generation.httpx.Client", MissingModelClient)
    with pytest.raises(SOAPGenerationError, match="model .* was not found"):
        OllamaSOAPGenerator().generate(_make_transcript())


def test_two_agent_empty_ollama_response(monkeypatch):
    class EmptyResponseClient:
        def __init__(self, **kwargs):
            pass
        def close(self):
            pass
        def post(self, url, json):
            return types.SimpleNamespace(
                status_code=200,
                json=lambda: {"message": {"content": ""}},
            )

    monkeypatch.setattr("app.services.soap_generation.httpx.Client", EmptyResponseClient)
    with pytest.raises(SOAPGenerationError, match="empty response"):
        OllamaSOAPGenerator().generate(_make_transcript())


def test_two_agent_malformed_ollama_response(monkeypatch):
    class MalformedResponseClient:
        def __init__(self, **kwargs):
            pass
        def close(self):
            pass
        def post(self, url, json):
            return types.SimpleNamespace(
                status_code=200,
                json=lambda: {"message": None},
            )

    monkeypatch.setattr("app.services.soap_generation.httpx.Client", MalformedResponseClient)
    with pytest.raises(SOAPGenerationError, match="empty response"):
        OllamaSOAPGenerator().generate(_make_transcript())


def test_two_agent_ollama_unavailable(monkeypatch):
    """Unavailable Ollama service → clear backend error."""
    class UnavailableClient:
        def __init__(self, **kwargs):
            pass
        def close(self):
            pass
        def post(self, url, json):
            raise httpx.ConnectError("connection refused", request=httpx.Request("POST", url))

    monkeypatch.setattr("app.services.soap_generation.httpx.Client", UnavailableClient)
    with pytest.raises(SOAPGenerationError, match="Ollama is unavailable"):
        OllamaSOAPGenerator().generate(_make_transcript())


def test_exact_synthetic_consultation_accuracy_regression(monkeypatch):
    transcript = TranscriptSchema(
        id="tx-spo2-regression",
        consultationId="con-spo2-regression",
        entries=[
            TranscriptEntrySchema(
                id="e1", consultation_id="con-spo2-regression", timestamp="00:00",
                offset_ms=0, speaker="patient", speaker_role="patient",
                text="I have cough, nasal congestion, and fever for three days.",
            ),
            TranscriptEntrySchema(
                id="e2", consultation_id="con-spo2-regression", timestamp="00:30",
                offset_ms=30000, speaker="Dr", speaker_role="physician",
                text="Temperature is 38.2 C, pulse 96 bpm, blood pressure 118 over 76, respiratory rate 18 breaths/min, and SpO₂ is 98% on room air.",
            ),
            TranscriptEntrySchema(
                id="e3", consultation_id="con-spo2-regression", timestamp="01:00",
                offset_ms=60000, speaker="Dr", speaker_role="physician",
                text="Based on your symptoms, this may be an acute respiratory tract infection, likely viral.",
            ),
            TranscriptEntrySchema(
                id="e4", consultation_id="con-spo2-regression", timestamp="01:30",
                offset_ms=90000, speaker="Dr", speaker_role="physician",
                text="I recommend CBC and COVID-19 testing, hydration, rest, temperature monitoring, appropriate paracetamol use, and continuing Amlodipine. Follow up in 2–3 days. Seek emergency care for difficulty breathing, chest pain, confusion, or blue lips.",
            ),
        ],
        recordedAt="2026-11-08T16:00:00Z",
        durationMs=120000,
        processingStatus="completed",
    )

    so_payload = json.dumps({
        "subjective": "Patient reports cough, nasal congestion, and fever.",
        "objective": "SpO₂ 90% on room air. Based on symptoms, possible infection.",
        "clinicalData": {
            "conditions": [],
            "medications": [],
            "measurements": [{"name": "SpO2", "value": "90", "unit": "%", "source": "clinic_measured"}],
            "allergies": [],
        },
    })
    ap_payload = json.dumps({
        "assessment": "Provisional acute respiratory tract infection, likely viral.",
        "plan": (
            "CBC and COVID-19 testing; hydration and rest; monitor temperature; "
            "use paracetamol appropriately; continue Amlodipine; follow up in 2–3 days; "
            "seek emergency care for difficulty breathing, chest pain, confusion, or blue lips."
        ),
    })
    monkeypatch.setattr(
        "app.services.soap_generation.httpx.Client",
        _fake_groq_for_two_agents(so_content=so_payload, ap_content=ap_payload),
    )

    generated = OllamaSOAPGenerator().generate(transcript)
    objective_lower = generated.objective.lower()
    assessment_lower = generated.assessment.lower()
    plan_lower = generated.plan.lower()

    assert "98%" in generated.objective
    assert "90%" not in generated.objective
    assert "118/76" in generated.objective
    assert "96 bpm" in generated.objective.lower()
    assert "38.2" in objective_lower and ("c" in objective_lower or "°c" in objective_lower)
    assert "possible infection" not in objective_lower
    assert "acute respiratory tract infection" in assessment_lower
    assert "likely viral" in assessment_lower
    assert "cbc" in plan_lower
    assert "covid-19" in plan_lower
    assert "hydration" in plan_lower and "rest" in plan_lower
    assert "paracetamol" in plan_lower
    assert "amlodipine" in plan_lower
    assert "2–3 days" in generated.plan or "2-3 days" in generated.plan
    assert "difficulty breathing" in plan_lower
    assert "chest pain" in plan_lower
    assert "confusion" in plan_lower
    assert "blue lips" in plan_lower
    assert all(m.value != "90" for m in generated.clinical_data.measurements if m.name.lower().startswith("spo"))
    assert any(m.value == "98" and m.unit == "%" for m in generated.clinical_data.measurements)


def test_quality_review_recovers_documented_assessment_and_plan_without_extra_model_call(monkeypatch):
    transcript = TranscriptSchema(
        id="tx-quality-review",
        consultationId="con-quality-review",
        entries=[
            TranscriptEntrySchema(
                id="e1", consultation_id="con-quality-review", timestamp="00:00",
                offset_ms=0, speaker="Dr", speaker_role="physician",
                text="Based on your symptoms, this may be an acute respiratory tract infection, likely viral.",
            ),
            TranscriptEntrySchema(
                id="e2", consultation_id="con-quality-review", timestamp="00:30",
                offset_ms=30000, speaker="Dr", speaker_role="physician",
                text="Recommend CBC and COVID-19 testing. Consider a chest X-ray if fever persists. Stay hydrated and get adequate rest. Follow up in two to three days. Seek emergency care for difficulty breathing.",
            ),
        ],
        recordedAt="2026-11-08T17:30:00Z",
        durationMs=60000,
        processingStatus="completed",
    )
    monkeypatch.setattr(
        "app.services.soap_generation.httpx.Client",
        _fake_groq_for_two_agents(
            so_content=json.dumps({
                "subjective": "Symptoms documented.",
                "objective": "Not documented in the transcript.",
            }),
            ap_content=json.dumps({
                "assessment": "Not documented in the transcript.",
                "plan": "No treatment or follow-up plan was documented in the transcript.",
            }),
        ),
    )

    generated = OllamaSOAPGenerator().generate(transcript)
    assert "acute respiratory tract infection" in generated.assessment.lower()
    assert "likely viral" in generated.assessment.lower()
    assert "cbc" in generated.plan.lower()
    assert "covid-19" in generated.plan.lower()
    assert "chest x-ray" in generated.plan.lower()
    assert "if fever persists" in generated.plan.lower()
    assert "two to three days" in generated.plan.lower()
    assert "difficulty breathing" in generated.plan.lower()


def test_quality_review_removes_unverified_generated_medication(monkeypatch):
    transcript = TranscriptSchema(
        id="tx-med-review",
        consultationId="con-med-review",
        entries=[
            TranscriptEntrySchema(
                id="e1", consultation_id="con-med-review", timestamp="00:00",
                offset_ms=0, speaker="patient", speaker_role="patient",
                text="I am taking Amlodipine every morning.",
            ),
        ],
        recordedAt="2026-11-08T17:30:00Z",
        durationMs=1000,
        processingStatus="completed",
    )
    monkeypatch.setattr(
        "app.services.soap_generation.httpx.Client",
        _fake_groq_for_two_agents(
            so_content=json.dumps({
                "subjective": "Patient reports taking Amlodipine.",
                "objective": "Not documented in the transcript.",
                "clinicalData": {
                    "medications": [
                        {"name": "Amlodipine", "dose": "5 mg", "frequency": "once daily", "verification": "confirmed"},
                        {"name": "Invented Drug", "dose": "10 mg", "frequency": "daily", "verification": "confirmed"},
                    ],
                },
            }),
            ap_content=json.dumps({
                "assessment": "Not documented in the transcript.",
                "plan": "Continue Amlodipine.",
            }),
        ),
    )

    generated = OllamaSOAPGenerator().generate(transcript)
    assert [medication.name for medication in generated.clinical_data.medications] == ["Amlodipine"]


def test_genuinely_missing_assessment_and_plan_fallback(monkeypatch):
    transcript = _make_transcript()
    transcript.entries = [
        TranscriptEntrySchema(
            id="e1", consultation_id="con-test", timestamp="00:00",
            offset_ms=0, speaker="patient", speaker_role="patient",
            text="Patient reports a headache.",
        ),
    ]
    monkeypatch.setattr(
        "app.services.soap_generation.httpx.Client",
        _fake_groq_for_two_agents(
            so_content=json.dumps({"subjective": "Patient reports a headache.", "objective": "Not documented in the transcript."}),
            ap_content=json.dumps({"assessment": "Not documented in the transcript.", "plan": "No treatment or follow-up plan was documented in the transcript."}),
        ),
    )

    generated = OllamaSOAPGenerator().generate(transcript)
    assert generated.assessment == "Not documented in the transcript."
    assert generated.plan == "No treatment or follow-up plan was documented in the transcript."


def test_agent_system_prompts_configured():
    """Verify system prompts for both agents are distinct and contain required directives."""
    assert "Subjective and Objective" in AGENT_SO_SYSTEM_PROMPT
    assert "Assessment and Plan" in AGENT_AP_SYSTEM_PROMPT
    assert "negations" in AGENT_SO_SYSTEM_PROMPT.lower()
    assert "negations" in AGENT_AP_SYSTEM_PROMPT.lower()
    assert "valid json" in AGENT_SO_SYSTEM_PROMPT.lower()
    assert "valid json" in AGENT_AP_SYSTEM_PROMPT.lower()


def test_ollama_request_disables_thinking_and_sets_agent_output_limits(monkeypatch):
    captured_bodies = []

    class CapturingClient:
        def __init__(self, **kwargs):
            pass

        def close(self):
            pass

        def post(self, url, json):
            captured_bodies.append(json)
            messages = json["messages"]
            if "Subjective and Objective" in messages[0]["content"]:
                content = _VALID_SO_PAYLOAD
            elif "Assessment and Plan" in messages[0]["content"]:
                content = _VALID_AP_PAYLOAD
            else:
                content = json.dumps({
                    "allergies": [{"name": "Penicillin", "category": "drug", "reaction": "skin rash", "status": "documented_allergies", "verification": "patient_reported"}],
                    "conditions": [{"name": "Type 2 Diabetes Mellitus", "status": "active", "classification": "chronic", "verification": "patient_reported"}],
                    "medications": [{"name": "Metformin", "strength": "500 mg", "frequency": "twice daily", "status": "current", "verification": "patient_reported"}],
                })
            return types.SimpleNamespace(
                status_code=200,
                json=lambda: {"message": {"content": content}},
            )

    monkeypatch.setattr("app.services.soap_generation.httpx.Client", CapturingClient)
    OllamaSOAPGenerator().generate(_make_transcript())

    assert len(captured_bodies) == 3
    for body in captured_bodies:
        assert body["model"] == "qwen3:8b"
        assert body["think"] is False
        assert body["stream"] is False
        assert isinstance(body["format"], dict)
        assert body["options"]["num_ctx"] == settings.ollama_num_ctx
        assert body["options"]["num_predict"] > 0
