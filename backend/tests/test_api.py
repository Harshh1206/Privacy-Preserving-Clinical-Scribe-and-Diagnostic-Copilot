from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.store import reset_store


@pytest.fixture()
def client():
    reset_store()
    with TestClient(app) as c:
        yield c
    reset_store()


def test_health_and_docs(client: TestClient):
    assert client.get("/health").json()["status"] == "ok"
    docs = client.get("/docs")
    assert docs.status_code == 200
    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    paths = schema.json()["paths"]
    for p in (
        "/api/patients",
        "/api/consultations",
        "/api/soap-notes/{soap_note_id}",
        "/api/consultations/{consultation_id}/validate",
        "/api/consultations/{consultation_id}/finalize",
        "/api/exports/pdf",
        "/api/exports/fhir",
        "/api/exports/ehr",
        "/api/team-b/ingest",
    ):
        assert p in paths


def test_patients_and_consultations(client: TestClient):
    patients = client.get("/api/patients").json()
    assert len(patients) == 3
    assert patients[0]["firstName"]
    pt = client.get("/api/patients/pt-003").json()
    assert "Penicillin" in pt["allergies"][0]
    cons = client.get("/api/consultations").json()
    assert len(cons) == 4
    filtered = client.get("/api/consultations", params={"patientId": "pt-001"}).json()
    assert all(c["patientId"] == "pt-001" for c in filtered)
    missing = client.get("/api/patients/nope")
    assert missing.status_code == 404


def test_clean_scenario_grounding_calculated(client: TestClient):
    val = client.get("/api/validations/val-001").json()
    assert val["groundingScore"] == 100
    assert val["hallucinationRisk"] == "low"
    assert val["unsupportedCount"] == 0
    assert val["conflictCount"] == 0
    assert val["supportedCount"] == val["totalClaimCount"] == 7


def test_unsupported_claim_scenario(client: TestClient):
    val = client.get("/api/validations/val-002").json()
    texts = " ".join(c["text"] for c in val["claims"] if c["status"] == "unsupported")
    assert "9.2" in texts
    assert val["unsupportedCount"] >= 1
    assert val["groundingScore"] == int(round((val["supportedCount"] / val["totalClaimCount"]) * 100))
    assert val["groundingScore"] < 100


def test_conflict_flags_without_drug_recommendation(client: TestClient):
    val = client.get("/api/validations/val-003").json()
    conflicts = [c for c in val["claims"] if c["status"] == "conflict"]
    assert len(conflicts) >= 1
    blob = json.dumps(val).lower()
    assert "amoxicillin" in blob
    assert "azithromycin" not in blob
    assert "clindamycin" not in blob
    assert "physician review" in (conflicts[0].get("conflictDescription") or "").lower()
    assert conflicts[0].get("suggestedCorrection") in (None, "")
    assert val["groundingScore"] == int(round((val["supportedCount"] / val["totalClaimCount"]) * 100))


def test_edit_invalidates_validation_and_blocks_finalize(client: TestClient):
    soap = client.get("/api/soap-notes/soap-001").json()
    patched = client.patch(
        "/api/soap-notes/soap-001",
        json={
            "plan": {
                "text": soap["plan"]["text"] + "\nAdded home BP log reminder.",
                "lastEditedBy": "Dr. Sarah Chen",
            }
        },
    )
    assert patched.status_code == 200
    assert patched.json()["version"] == soap["version"] + 1
    val = client.get("/api/validations/val-001").json()
    assert val["isStale"] is True
    blocked = client.post(
        "/api/consultations/con-001/finalize",
        json={"physicianId": "dr-001", "physicianName": "Dr. Sarah Chen"},
    )
    assert blocked.status_code == 409
    fresh = client.post("/api/consultations/con-001/validate").json()
    assert fresh["isStale"] is False
    assert fresh["soapNoteVersion"] == patched.json()["version"]
    assert fresh["groundingScore"] == int(round((fresh["supportedCount"] / max(fresh["totalClaimCount"], 1)) * 100))
    done = client.post(
        "/api/consultations/con-001/finalize",
        json={"physicianId": "dr-001", "physicianName": "Dr. Sarah Chen"},
    )
    assert done.status_code == 200
    assert done.json()["soapNote"]["isFinalized"] is True
    assert done.json()["consultation"]["status"] == "finalized"
    locked = client.patch("/api/soap-notes/soap-001", json={"plan": {"text": "nope"}})
    assert locked.status_code == 409
    reval = client.post("/api/consultations/con-001/validate")
    assert reval.status_code == 409


def test_exports_and_audit(client: TestClient):
    pdf = client.post(
        "/api/exports/pdf",
        json={"consultationId": "con-002", "format": "pdf", "includeTranscript": True, "includeValidation": True},
    )
    assert pdf.status_code == 200
    body = pdf.json()
    assert body["format"] == "pdf"
    assert body["content"]
    fhir = client.post(
        "/api/exports/fhir",
        json={"consultationId": "con-003", "format": "fhir", "includeTranscript": False, "includeValidation": True},
    )
    assert fhir.status_code == 200
    resource = json.loads(fhir.json()["content"])
    assert resource["resourceType"] == "Composition"
    assert resource["type"]["coding"][0]["code"] == "11488-4"
    ehr = client.post(
        "/api/exports/ehr",
        json={"consultationId": "con-003", "format": "ehr", "includeTranscript": False, "includeValidation": True},
    )
    assert ehr.json()["success"] is True
    audit = client.get("/api/consultations/con-003/audit").json()
    actions = {a["action"] for a in audit}
    assert "exported" in actions
    assert "sent_to_ehr" in actions


def test_team_b_ingest_recomputes_scores(client: TestClient):
    soap = client.get("/api/soap-notes/soap-002").json()
    payload = {
        "consultationId": "con-002",
        "soapNote": soap,
        "entities": [{"id": "ent-1", "text": "Metformin", "type": "medication"}],
        "claims": [
            {
                "id": "cl-x",
                "soapSection": "objective",
                "text": "Last HbA1c result: 9.2%.",
                "status": "supported",
                "severity": "low",
                "evidenceIds": [],
            }
        ],
        "evidence": [],
    }
    res = client.post("/api/team-b/ingest", json=payload)
    assert res.status_code == 200
    val = res.json()["validation"]
    assert val["claims"][0]["status"] == "unsupported"
    assert val["groundingScore"] == 0
