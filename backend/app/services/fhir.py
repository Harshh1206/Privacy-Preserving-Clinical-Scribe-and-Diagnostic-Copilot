from __future__ import annotations

from html import escape
from datetime import datetime, timezone

from app.models.schemas import Consultation, Patient, SOAPNote, Transcript, ValidationResult


def _esc(text: str) -> str:
    return escape(text or "").replace("\n", "<br/>")


def build_fhir_composition(
    consultation: Consultation,
    patient: Patient,
    soap: SOAPNote,
    validation: ValidationResult | None,
    transcript: Transcript | None,
    include_transcript: bool,
    include_validation: bool,
) -> dict:
    status = "final" if soap.is_finalized else "preliminary"
    generated = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    resource = {
        "resourceType": "Composition",
        "id": f"comp-{consultation.id}",
        "status": status,
        "type": {
            "coding": [{"system": "http://loinc.org", "code": "11488-4", "display": "Consult note"}],
        },
        "date": generated,
        "title": "Clinical Encounter Note",
        "subject": {
            "reference": f"Patient/{patient.id}",
            "display": f"{patient.first_name} {patient.last_name}",
        },
        "author": [{"display": consultation.physician_name}],
        "section": [
            {"title": "Subjective", "text": {"status": "generated", "div": f"<div>{_esc(soap.subjective.text)}</div>"}},
            {"title": "Objective", "text": {"status": "generated", "div": f"<div>{_esc(soap.objective.text)}</div>"}},
            {"title": "Assessment", "text": {"status": "generated", "div": f"<div>{_esc(soap.assessment.text)}</div>"}},
            {"title": "Plan", "text": {"status": "generated", "div": f"<div>{_esc(soap.plan.text)}</div>"}},
        ],
        "_mock": True,
    }
    if include_validation and validation:
        claims_html = "".join(
            f"<p><b>{escape(c.status)}</b> [{escape(c.soap_section)}] {escape(c.text)}</p>"
            for c in validation.claims
        )
        resource["section"].append(
            {
                "title": "AI Grounding Report",
                "text": {
                    "status": "generated",
                    "div": (
                        f"<div>Grounding score: {validation.grounding_score}/100. "
                        f"Hallucination risk: {validation.hallucination_risk}. "
                        f"Supported {validation.supported_count}, unsupported {validation.unsupported_count}, "
                        f"conflicts {validation.conflict_count}.{claims_html}</div>"
                    ),
                },
            }
        )
    if include_transcript and transcript:
        lines = "".join(
            f"<p>[{escape(e.timestamp)}] {escape(e.speaker)}: {escape(e.text)}</p>" for e in transcript.entries
        )
        resource["section"].append(
            {
                "title": "Encounter Transcript",
                "text": {"status": "generated", "div": f"<div>{lines}</div>"},
            }
        )
    return resource
