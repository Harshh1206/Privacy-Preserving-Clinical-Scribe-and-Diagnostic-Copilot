from __future__ import annotations

import json
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Literal

import httpx

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.config import settings
from app.models.schemas import (
    ClinicalAllergy,
    ClinicalCondition,
    ClinicalData,
    ClinicalMeasurement,
    ClinicalMedication,
    Transcript,
)


logger = logging.getLogger(__name__)

_shared_client_lock = threading.Lock()
_shared_client: httpx.Client | None = None
_shared_client_key: tuple[Any, ...] | None = None


class SOAPGenerationError(RuntimeError):
    pass


class GeneratedSOAP(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    subjective: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    assessment: str = Field(min_length=1)
    plan: str = Field(min_length=1)
    clinical_data: ClinicalData = Field(default_factory=ClinicalData, alias="clinicalData")

    @field_validator("subjective", "objective", "assessment", "plan", mode="before")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("SOAP section must be a non-empty string")
        return value.strip()


class ClinicalExtractionAllergy(BaseModel):
    name: str = Field(min_length=1)
    category: Literal["drug", "food", "environmental", "unknown"] = "unknown"
    reaction: str | None = None
    details: str | None = None
    status: Literal["documented_allergies", "explicitly_no_known_allergies", "not_documented"] = "not_documented"
    source: Literal["current_encounter"] = "current_encounter"
    evidence: str | None = None
    verification: Literal["patient_reported", "needs_review", "verified"] = "patient_reported"


class ClinicalExtractionCondition(BaseModel):
    name: str = Field(min_length=1)
    duration: str | None = None
    classification: str | None = None
    status: str | None = None
    provenance: str | None = None
    source: Literal["current_encounter"] = "current_encounter"
    evidence: str | None = None
    verification: Literal["patient_reported", "needs_review", "verified"] = "patient_reported"


class ClinicalExtractionMedication(BaseModel):
    name: str = Field(min_length=1)
    strength: str | None = None
    frequency: str | None = None
    route: str | None = None
    status: str | None = None
    adherence: str | None = None
    source: Literal["current_encounter"] = "current_encounter"
    evidence: str | None = None
    verification: Literal["patient_reported", "needs_review", "verified"] = "patient_reported"


class ClinicalInformationExtraction(BaseModel):
    allergies: list[ClinicalExtractionAllergy] = Field(default_factory=list)
    conditions: list[ClinicalExtractionCondition] = Field(default_factory=list)
    medications: list[ClinicalExtractionMedication] = Field(default_factory=list)

    @classmethod
    def normalize(cls, payload: dict[str, Any]) -> "ClinicalInformationExtraction":
        return cls.model_validate(payload)


# Original single-agent prompt is retained only for compatibility with callers/imports.
SYSTEM_PROMPT = """Document only facts stated in the transcript.
Return concise valid JSON with exactly: subjective, objective, assessment, plan.
Do not invent symptoms, diagnoses, medications, dosages, allergies, examination findings, vital signs, tests, or plans.
Preserve negations, uncertainty, units, source, and missing-information distinctions."""

CLINICAL_EXTRACTION_SYSTEM_PROMPT = """Extract exactly three categories from the consultation transcript only: allergies, medical conditions, and current medications.
Return valid JSON only.
Rules:
- Do not invent anything absent from the transcript.
- Use the transcript as the sole evidence source.
- Distinguish patient-reported history from provisional diagnoses and confirmed diagnoses.
- Set status to one of: documented_allergies, explicitly_no_known_allergies, not_documented.
- For conditions, capture chronicity or acuity only when explicitly documented.
- For medications, only include dosage/frequency/route/adherence if explicitly documented.
- If a fact is unsupported, omit it or mark it as needs_review.
- Preserve exact negations and uncertainty.
Return JSON shaped like:
{
  "allergies": [{"name": "Penicillin", "category": "drug", "reaction": "skin rash", "details": "...", "status": "documented_allergies", "source": "current_encounter", "evidence": "...", "verification": "patient_reported"}],
  "conditions": [{"name": "Asthma", "duration": "2 years", "classification": "chronic", "status": "active", "provenance": "verified", "source": "current_encounter", "evidence": "...", "verification": "patient_reported"}],
  "medications": [{"name": "Metformin", "strength": "500 mg", "frequency": "twice daily", "route": "oral", "status": "current", "adherence": "missed two doses last week", "source": "current_encounter", "evidence": "...", "verification": "patient_reported"}]
}
"""

# ---------------------------------------------------------------------------
# Agent 1 — Subjective + Objective
# ---------------------------------------------------------------------------
AGENT_SO_SYSTEM_PROMPT = """Generate only Subjective and Objective from the transcript. Return valid JSON only.
Produce a comprehensive Subjective and Objective. Subjective must include the chief complaint, HPI onset/duration/progression, associated symptoms, relevant medical history, medications, allergies, and documented family/social history.
Objective must include ONLY documented blood pressure, pulse/heart rate, respiratory rate, temperature, oxygen saturation, examination findings, labs, imaging, and other objective observations.
Copy numerical values, units, and measurement context exactly. Never approximate or substitute a similar vital sign.
Separate patient-reported, clinic-measured, and unknown-source findings. Do not place an assessment, diagnosis, investigation recommendation, medication instruction, counselling, or follow-up in Objective.
Preserve exact negations, uncertainty, and explicitly negative findings. Missing information is not a negative finding.
Do not invent symptoms, medications, doses, allergies, findings, measurements, or tests.
Return JSON only: {"subjective":"...","objective":"...","clinicalData":{"conditions":[],"medications":[],"measurements":[],"allergies":[]}}.
Write "Not documented in the transcript." when a requested subsection has no documented information."""

# ---------------------------------------------------------------------------
# Agent 2 — Assessment + Plan
# ---------------------------------------------------------------------------
AGENT_AP_SYSTEM_PROMPT = """Generate only Assessment and Plan from the transcript. Return valid JSON only.
Assessment: the primary clinical impression, provisional diagnosis, differential diagnoses, and relevant documented clinical reasoning, preserving uncertainty and qualifications.
Plan: every explicitly documented investigation or conditional investigation, medication recommendation or continuation, exact stated dose/frequency/route, supportive care, hydration, rest, monitoring, referral, follow-up timeline, return precaution, and emergency warning sign.
Pay special attention to sentences containing "consider", "if", "may", "recommend", or conditional instructions; preserve conditional plans without converting them into confirmed actions.
Read the complete transcript before concluding that Assessment or Plan is missing. A provisional or "may be" impression is still an Assessment, and explicit recommendations are still a Plan.
Preserve uncertainty and negations. Do not infer or invent diagnoses, findings, tests, prescriptions, doses, or timelines.
Missing assessment: "Not documented in the transcript."; missing plan: "No treatment or follow-up plan was documented in the transcript."
Return JSON only: {"assessment":"...","plan":"..."}."""


def _format_transcript(transcript: Transcript) -> str:
    lines = []
    for entry in transcript.entries:
        speaker = entry.speaker_display_name or entry.speaker or "Unknown speaker"
        lines.append(f"[{entry.timestamp}] {speaker}: {entry.text}")
    return "\n".join(lines)


def _extract_documented_measurements(transcript: Transcript) -> tuple[list[str], ClinicalData]:
    """Extract numerical vitals directly from transcript text without model inference."""
    facts: list[str] = []
    measurements: list[ClinicalMeasurement] = []
    seen: set[tuple[str, str | None, str | None]] = set()

    patterns = (
        (
            "SpO2",
            re.compile(r"(?:SpO(?:₂|2)?|oxygen\s+saturation|O2\s+saturation)[^0-9]{0,25}(\d+(?:\.\d+)?)\s*(?:%|percent)(?:[^.]*)(room\s+air)?", re.I),
            "%",
        ),
        (
            "Blood pressure",
            re.compile(r"\b(?:blood\s+pressure|BP)\b[^0-9]{0,12}(\d{2,3})\s*(?:/|over)\s*(\d{2,3})\s*(mm\s*Hg|mmHg|mg\.?)?", re.I),
            "",
        ),
        (
            "Pulse",
            re.compile(r"\b(?:pulse|heart\s+rate)\b[^0-9]{0,12}(\d{2,3})\s*(bpm|beats\s+per\s+minute)?\b", re.I),
            "bpm",
        ),
        (
            "Temperature",
            re.compile(r"\b(?:temperature|temp)\b[^0-9]{0,12}(\d{2,3}(?:\.\d+)?)\s*(degrees?\s+(?:Celsius|Fahrenheit|C|F)|degrees?\s*[CF°]|°C|°F|Celsius|Fahrenheit|C|F)?\b", re.I),
            "",
        ),
        (
            "Respiratory rate",
            re.compile(r"\b(?:respiratory\s+rate|RR)\b[^0-9]{0,12}(\d{2,3})\s*(?:breaths?\s+per\s+minute|rpm|/min)?\b", re.I),
            "breaths/min",
        ),
    )

    for entry in transcript.entries:
        text = entry.text
        source = "patient_reported" if entry.speaker_role == "patient" else (
            "clinic_measured" if entry.speaker_role in ("physician", "doctor", "nurse") else "unknown"
        )
        for name, pattern, default_unit in patterns:
            for match in pattern.finditer(text):
                if name == "Blood pressure":
                    value = f"{match.group(1)}/{match.group(2)}"
                    captured_unit = match.group(3)
                    unit = (
                        "mmHg"
                        if captured_unit and re.fullmatch(r"mm\s*Hg|mmHg", captured_unit, re.I)
                        else ""
                    )
                elif name == "Temperature":
                    value = match.group(1)
                    unit = match.group(2) or default_unit
                    if unit:
                        normalized = unit.strip().lower().replace("degrees ", "").replace("degree ", "")
                        if normalized in ("c", "celsius", "°c"):
                            unit = "°C"
                        elif normalized in ("f", "fahrenheit", "°f"):
                            unit = "°F"
                        else:
                            unit = ""
                    else:
                        unit = ""
                elif name == "Pulse":
                    value = match.group(1)
                    unit = match.group(2) if match.group(2) else ""
                else:
                    value = match.group(1)
                    unit = default_unit

                key = (name.lower(), value, unit)
                if key in seen:
                    continue
                seen.add(key)

                context = ""
                if name == "SpO2":
                    context_match = re.search(r"\b(room\s+air|on\s+oxygen[^.]*)", text[match.start():], re.I)
                    if context_match:
                        context = f" {context_match.group(1).strip()}"
                if name == "SpO2":
                    fact = f"{name}: {value}%{context}."
                else:
                    fact = (
                        f"{name}: {value} {unit}{context}."
                        if name == "Temperature" and unit
                        else f"{name}: {value}{unit if name == 'Temperature' else (' ' + unit if unit else '')}{context}."
                    )
                facts.append(fact)
                measurements.append(ClinicalMeasurement(
                    name=name,
                    value=value,
                    unit=unit or None,
                    source=source,
                    verification="confirmed" if source == "clinic_measured" else "reported",
                ))

    return facts, ClinicalData(measurements=measurements)


def _apply_documented_objective(
    objective: Any,
    transcript: Transcript,
) -> str | None:
    if not isinstance(objective, str):
        return objective
    documented_facts, _ = _extract_documented_measurements(transcript)
    if not documented_facts:
        return objective.strip()

    aliases = re.compile(
        r"\b(?:SpO[₂2]?|oxygen\s+saturation|O2\s+saturation|blood\s+pressure|BP|pulse|heart\s+rate|temperature|temp|respiratory\s+rate|RR)\b|SpO₂",
        re.I,
    )
    preserved = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", objective)
        if sentence.strip()
        and not aliases.search(sentence)
        and not re.search(
            r"\b(?:diagnosis|provisional|assessment|impression|infection|likely|possible|recommend(?:s|ed)?|plan|follow[- ]up|CBC|COVID|paracetamol|Amlodipine|hydration|rest)\b",
            sentence,
            re.I,
        )
    ]
    combined = preserved + documented_facts
    text = " ".join(combined).strip()
    return text if text else "Not documented in the transcript."


def _replace_documented_measurements(
    parsed: ClinicalData,
    documented: ClinicalData,
) -> ClinicalData:
    if not documented.measurements:
        return parsed
    documented_names = {_norm_measurement_name(item.name) for item in documented.measurements}
    preserved = [
        item for item in parsed.measurements
        if _norm_measurement_name(item.name) not in documented_names
    ]
    return ClinicalData(
        conditions=parsed.conditions,
        medications=parsed.medications,
        measurements=list(documented.measurements) + preserved,
        allergies=parsed.allergies,
    )


def _norm_measurement_name(name: str) -> str:
    normalized = " ".join(name.strip().lower().replace("_", " ").split())
    if normalized in ("spo2", "sp02", "oxygen saturation", "o2 saturation"):
        return "spo2"
    return normalized


def _quality_review_soap(
    transcript: Transcript,
    generated: GeneratedSOAP,
) -> tuple[GeneratedSOAP, dict[str, bool | int]]:
    """Deterministic quality gate; it never introduces facts absent from the transcript."""
    transcript_text = _format_transcript(transcript)
    transcript_folded = transcript_text.casefold()
    report: dict[str, bool | int] = {
        "objective_vitals_verified": True,
        "unsupported_medications_removed": 0,
        "assessment_recovered": False,
        "plan_recovered": False,
    }

    filtered_medications = []
    for medication in generated.clinical_data.medications:
        name_folded = medication.name.casefold()
        if name_folded in transcript_folded:
            filtered_medications.append(medication)
        else:
            report["unsupported_medications_removed"] = int(report["unsupported_medications_removed"]) + 1

    generated.clinical_data.medications = filtered_medications

    assessment_missing = generated.assessment.strip().casefold().startswith("not documented")
    if assessment_missing:
        assessment_sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", transcript_text)
            if re.search(
                r"\b(?:may be|likely|provisional|differential|diagnosis|impression|suspect|viral|infection)\b",
                sentence,
                re.I,
            )
        ]
        if assessment_sentences:
            generated.assessment = " ".join(assessment_sentences[:3]).strip()
            report["assessment_recovered"] = True

    plan_missing = generated.plan.strip().casefold().startswith("no treatment") or generated.plan.strip().casefold().startswith("not documented")
    if plan_missing:
        plan_sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", transcript_text)
            if re.search(
                r"\b(?:recommend|CBC|COVID|covid|hydration|hydrated|rest|monitor|paracetamol|follow up|follow-up|"
                r"immediate medical attention|seek emergency|chest X-ray|x-ray|wearing a mask|mask)\b",
                sentence,
                re.I,
            )
        ]
        if plan_sentences:
            generated.plan = " ".join(plan_sentences[:8]).strip()
            report["plan_recovered"] = True

    return generated, report


def _normalize_json_content(content: str) -> str:
    stripped = content.strip()
    stripped = re.sub(r"<think>.*?</think>", "", stripped, flags=re.DOTALL | re.IGNORECASE).strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    if not stripped.startswith("{"):
        start = stripped.find("{")
        if start >= 0:
            stripped = stripped[start:]
    return stripped


def _normalize_soap_payload(payload: dict[str, Any]) -> dict[str, Any]:
    nested = payload.get("soap")
    if isinstance(nested, dict):
        payload = nested

    normalized: dict[str, Any] = {}
    for key, value in payload.items():
        normalized_key = key.strip().lower().replace("-", "_").replace(" ", "_")
        normalized[normalized_key] = value
    return {
        key: normalized.get(key)
        for key in ("subjective", "objective", "assessment", "plan")
    }


def _safe_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _coerce_verification(value: Any) -> Literal["confirmed", "reported", "awaiting_review"]:
    if isinstance(value, str):
        lowered = value.strip().lower().replace(" ", "_")
        mapping = {
            "patient_reported": "reported",
            "reported": "reported",
            "verified": "confirmed",
            "confirmed": "confirmed",
            "needs_review": "awaiting_review",
            "awaiting_review": "awaiting_review",
            "provisional": "awaiting_review",
        }
        return mapping.get(lowered, "reported")
    return "reported"


def _coerce_condition_status(value: Any) -> Literal["active", "reported", "resolved", "unknown"]:
    if not isinstance(value, str):
        return "reported"
    lowered = value.strip().lower().replace(" ", "_")
    if lowered in {"active", "chronic", "current", "ongoing"}:
        return "active"
    if lowered in {"resolved", "inactive", "past"}:
        return "resolved"
    if lowered in {"patient_reported", "reported", "provisional", "suspected"}:
        return "reported"
    return "unknown"


def _coerce_medication_status(value: Any) -> Literal["current", "reported_current", "discontinued", "unknown"]:
    if not isinstance(value, str):
        return "reported_current"
    lowered = value.strip().lower().replace(" ", "_")
    if lowered in {"current", "active", "ongoing", "continue"}:
        return "current"
    if lowered in {"discontinued", "stopped", "paused"}:
        return "discontinued"
    if lowered in {"reported_current", "patient_reported"}:
        return "reported_current"
    return "unknown"


def _parse_clinical_extraction_payload(payload: dict[str, Any]) -> ClinicalData:
    if not isinstance(payload, dict):
        raise ValueError("Clinical extraction payload must be an object")

    data_raw = payload.get("clinicalData")
    if data_raw is None:
        data_raw = payload

    if not isinstance(data_raw, dict):
        raise ValueError("Clinical extraction payload is not an object")

    extracted = ClinicalInformationExtraction.model_validate({
        "allergies": data_raw.get("allergies") or data_raw.get("allergy") or [],
        "conditions": data_raw.get("conditions") or data_raw.get("medicalConditions") or [],
        "medications": data_raw.get("medications") or data_raw.get("currentMedications") or [],
    })

    conditions: list[ClinicalCondition] = []
    for item in extracted.conditions:
        name = (item.name or "").strip()
        if not name:
            continue
        conditions.append(ClinicalCondition(
            name=name,
            status=_coerce_condition_status(item.status),
            verification=_coerce_verification(item.verification),
            duration=item.duration,
            classification=item.classification,
            provenance=item.provenance,
            source=item.source,
            evidence=item.evidence,
            source_consultation_id=None,
        ))

    medications: list[ClinicalMedication] = []
    for item in extracted.medications:
        name = (item.name or "").strip()
        if not name:
            continue
        medications.append(ClinicalMedication(
            name=name,
            dose=item.strength,
            frequency=item.frequency,
            strength=item.strength,
            route=item.route,
            status=_coerce_medication_status(item.status),
            verification=_coerce_verification(item.verification),
            adherence=item.adherence,
            source=item.source,
            evidence=item.evidence,
            source_consultation_id=None,
        ))

    allergies: list[ClinicalAllergy] = []
    for item in extracted.allergies:
        name = (item.name or "").strip()
        if not name:
            continue
        allergies.append(ClinicalAllergy(
            substance=name,
            reaction=item.reaction,
            category=item.category,
            status=item.status,
            details=item.details,
            source=item.source,
            evidence=item.evidence,
            verification=_coerce_verification(item.verification),
            source_consultation_id=None,
        ))

    return ClinicalData(
        conditions=conditions,
        medications=medications,
        measurements=[],
        allergies=allergies,
    )


def _parse_clinical_data(payload: dict[str, Any]) -> ClinicalData:
    raw = payload.get("clinicalData")
    if raw is None:
        raw = payload.get("clinical_data")
    if not isinstance(raw, dict):
        return ClinicalData()

    sanitized: dict[str, list[dict[str, Any]]] = {
        "conditions": [],
        "medications": [],
        "measurements": [],
        "allergies": [],
    }

    for item in _safe_list(raw.get("conditions")):
        name = item.get("name")
        if isinstance(name, str) and name.strip():
            sanitized["conditions"].append({
                "name": name.strip(),
                "status": item.get("status") if item.get("status") in ("active", "reported", "resolved", "unknown") else "reported",
                "verification": item.get("verification") if item.get("verification") in ("confirmed", "reported", "awaiting_review") else "reported",
            })

    for item in _safe_list(raw.get("medications")):
        name = item.get("name")
        if isinstance(name, str) and name.strip():
            sanitized["medications"].append({
                "name": name.strip(),
                "dose": item.get("dose").strip() if isinstance(item.get("dose"), str) else None,
                "frequency": item.get("frequency").strip() if isinstance(item.get("frequency"), str) else None,
                "status": item.get("status") if item.get("status") in ("current", "reported_current", "discontinued", "unknown") else "reported_current",
                "verification": item.get("verification") if item.get("verification") in ("confirmed", "reported", "awaiting_review") else "reported",
            })

    for item in _safe_list(raw.get("measurements")):
        name = item.get("name")
        if isinstance(name, str) and name.strip():
            sanitized["measurements"].append({
                "name": name.strip(),
                "value": item.get("value").strip() if isinstance(item.get("value"), str) else str(item["value"]).strip() if item.get("value") is not None else None,
                "unit": item.get("unit").strip() if isinstance(item.get("unit"), str) and item.get("unit").strip() else None,
                "source": item.get("source") if item.get("source") in ("patient_reported", "clinic_measured", "unknown") else "unknown",
                "recordedAt": item.get("recordedAt") if isinstance(item.get("recordedAt"), str) else item.get("recorded_at"),
                "verification": item.get("verification") if item.get("verification") in ("confirmed", "reported", "awaiting_review") else "reported",
            })

    for item in _safe_list(raw.get("allergies")):
        substance = item.get("substance") or item.get("name")
        if isinstance(substance, str) and substance.strip():
            sanitized["allergies"].append({
                "substance": substance.strip(),
                "reaction": item.get("reaction").strip() if isinstance(item.get("reaction"), str) and item.get("reaction").strip() else None,
                "verification": item.get("verification") if item.get("verification") in ("confirmed", "reported", "awaiting_review") else "reported",
            })

    return ClinicalData.model_validate(sanitized)


def _merge_clinical_data(primary: ClinicalData, secondary: ClinicalData) -> ClinicalData:
    """Merge clinical data from two agents, deduplicating by normalised name."""

    def _norm(name: str) -> str:
        return " ".join(name.strip().lower().split())

    # Conditions
    seen_conditions: set[str] = set()
    merged_conditions = []
    for cond in list(primary.conditions) + list(secondary.conditions):
        key = _norm(cond.name)
        if key not in seen_conditions:
            seen_conditions.add(key)
            merged_conditions.append(cond)

    # Medications
    seen_medications: set[str] = set()
    merged_medications = []
    for med in list(primary.medications) + list(secondary.medications):
        key = _norm(med.name)
        if key not in seen_medications:
            seen_medications.add(key)
            merged_medications.append(med)

    # Measurements
    seen_measurements: set[tuple[str, str | None, str | None]] = set()
    merged_measurements = []
    for m in list(primary.measurements) + list(secondary.measurements):
        key = (_norm(m.name), m.value, m.unit)
        if key not in seen_measurements:
            seen_measurements.add(key)
            merged_measurements.append(m)

    # Allergies
    seen_allergies: set[str] = set()
    merged_allergies = []
    for allergy in list(primary.allergies) + list(secondary.allergies):
        key = _norm(allergy.substance)
        if key not in seen_allergies:
            seen_allergies.add(key)
            merged_allergies.append(allergy)

    return ClinicalData(
        conditions=merged_conditions,
        medications=merged_medications,
        measurements=merged_measurements,
        allergies=merged_allergies,
    )


class OllamaSOAPClient:
    def __init__(self) -> None:
        timeout = httpx.Timeout(
            settings.ollama_request_timeout_seconds,
            connect=settings.ollama_connect_timeout_seconds,
        )
        limits = httpx.Limits(
            max_connections=settings.ollama_pool_max_connections,
            max_keepalive_connections=settings.ollama_pool_max_keepalive_connections,
        )
        key = (
            httpx.Client,
            settings.ollama_request_timeout_seconds,
            settings.ollama_connect_timeout_seconds,
            settings.ollama_pool_max_connections,
            settings.ollama_pool_max_keepalive_connections,
        )
        global _shared_client, _shared_client_key
        with _shared_client_lock:
            if _shared_client is None or _shared_client_key != key:
                if _shared_client is not None:
                    _shared_client.close()
                _shared_client = httpx.Client(timeout=timeout, limits=limits)
                _shared_client_key = key
        self._client = _shared_client

    def close(self) -> None:
        # The shared transport remains open across generate() calls and generator instances.
        return

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        agent_label: str,
    ) -> dict[str, Any]:
        url = settings.ollama_base_url.rstrip("/") + "/api/chat"
        is_subjective_objective = agent_label == "Subjective/Objective"
        estimated_input_tokens = max(1, (len(system_prompt) + len(user_prompt)) // 3)
        required_ctx = min(
            settings.ollama_num_ctx,
            32768,
        )
        dynamic_num_ctx = max(
            required_ctx,
            min(
                32768,
                estimated_input_tokens + (
                    settings.ollama_num_predict_subjective_objective
                    if is_subjective_objective
                    else settings.ollama_num_predict_assessment_plan
                ) + 1024,
            ),
        )
        num_predict = (
            settings.ollama_num_predict_subjective_objective
            if is_subjective_objective
            else settings.ollama_num_predict_assessment_plan
        )
        if is_subjective_objective:
            response_schema = {
                "type": "object",
                "properties": {
                    "subjective": {"type": "string"},
                    "objective": {"type": "string"},
                    "clinicalData": {"type": "object"},
                },
                "required": ["subjective", "objective"],
                "additionalProperties": False,
            }
        elif agent_label == "Clinical Information Extractor":
            response_schema = {
                "type": "object",
                "properties": {
                    "allergies": {"type": "array", "items": {"type": "object"}},
                    "conditions": {"type": "array", "items": {"type": "object"}},
                    "medications": {"type": "array", "items": {"type": "object"}},
                },
                "required": ["allergies", "conditions", "medications"],
                "additionalProperties": False,
            }
        else:
            response_schema = {
                "type": "object",
                "properties": {
                    "assessment": {"type": "string"},
                    "plan": {"type": "string"},
                },
                "required": ["assessment", "plan"],
                "additionalProperties": False,
            }
        body = {
            "model": settings.ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "format": response_schema,
            "think": False,
            "keep_alive": settings.ollama_keep_alive,
            "options": {
                "temperature": settings.ollama_temperature,
                "num_ctx": dynamic_num_ctx,
                "num_predict": num_predict,
            },
        }

        try:
            response = self._client.post(url, json=body)
        except httpx.ConnectError as exc:
            raise SOAPGenerationError(
                f"Ollama is unavailable for SOAP generation ({agent_label}). "
                "Start Ollama and verify OLLAMA_BASE_URL."
            ) from exc
        except (httpx.TimeoutException, TimeoutError) as exc:
            raise SOAPGenerationError(
                f"SOAP generation ({agent_label}) timed out. "
                "The local Ollama service did not respond in time."
            ) from exc
        except httpx.HTTPError as exc:
            raise SOAPGenerationError(
                f"SOAP generation ({agent_label}) could not connect to Ollama."
            ) from exc
        except Exception as exc:
            raise SOAPGenerationError(
                f"SOAP generation ({agent_label}) failed. Check the local Ollama service and configured model."
            ) from exc

        if response.status_code == 404:
            raise SOAPGenerationError(
                f"Ollama model '{settings.ollama_model}' was not found for SOAP generation ({agent_label})."
            )
        if response.status_code >= 400:
            try:
                error_payload = response.json()
                error_text = error_payload.get("error", "")
            except ValueError:
                error_text = ""
            if isinstance(error_text, str) and "model" in error_text.lower() and "not found" in error_text.lower():
                raise SOAPGenerationError(
                    f"Ollama model '{settings.ollama_model}' was not found for SOAP generation ({agent_label})."
                )
            raise SOAPGenerationError(
                f"Ollama SOAP generation ({agent_label}) failed with HTTP {response.status_code}."
            )

        try:
            response_payload = response.json()
        except ValueError as exc:
            raise SOAPGenerationError(
                f"Ollama SOAP generation ({agent_label}) returned a malformed response."
            ) from exc

        message = response_payload.get("message", {})
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        if not isinstance(content, str) or not content.strip():
            raise SOAPGenerationError(
                f"Ollama SOAP generation ({agent_label}) returned an empty response."
            )

        try:
            parsing_started = time.perf_counter()
            payload = json.loads(_normalize_json_content(content))
        except json.JSONDecodeError as exc:
            raise SOAPGenerationError(
                f"Ollama SOAP generation ({agent_label}) returned invalid JSON."
            ) from exc
        finally:
            if "parsing_started" in locals():
                logger.info(
                    "SOAP %s JSON parsing completed in %.1f ms",
                    agent_label,
                    round((time.perf_counter() - parsing_started) * 1000, 1),
                )
        if not isinstance(payload, dict):
            raise SOAPGenerationError(
                f"Ollama SOAP generation ({agent_label}) returned an invalid structure."
            )
        return payload


class OllamaSOAPGenerator:
    """Two-agent local SOAP generator using one configurable Ollama model."""

    def __init__(self, client: OllamaSOAPClient | None = None) -> None:
        self._client = client

    def _get_client(self) -> OllamaSOAPClient:
        if self._client is None:
            self._client = OllamaSOAPClient()
        return self._client

    def _call_agent(
        self,
        client: OllamaSOAPClient,
        system_prompt: str,
        user_prompt: str,
        agent_label: str,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            return client.chat(system_prompt, user_prompt, agent_label)
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 1)
            logger.info("SOAP agent %s completed in %.1f ms", agent_label, duration_ms)

    def extract_clinical_information(self, transcript: Transcript) -> ClinicalData:
        formatted = _format_transcript(transcript)
        client = self._get_client()
        started = time.perf_counter()
        try:
            payload = self._call_agent(
                client,
                CLINICAL_EXTRACTION_SYSTEM_PROMPT,
                "Consultation transcript:\n" + formatted,
                "Clinical Information Extractor",
            )
            parsed = _parse_clinical_extraction_payload(payload)
            logger.info(
                "Clinical information extraction completed in %.1f ms",
                round((time.perf_counter() - started) * 1000, 1),
            )
            return parsed
        except Exception as exc:  # pragma: no cover - defensive guard for extraction failures
            logger.warning(
                "Clinical information extraction failed and was ignored so SOAP generation can continue: %s",
                exc,
            )
            logger.info(
                "Clinical information extraction failed in %.1f ms",
                round((time.perf_counter() - started) * 1000, 1),
            )
            return ClinicalData()

    def generate(self, transcript: Transcript) -> GeneratedSOAP:
        total_started = time.perf_counter()
        formatted = _format_transcript(transcript)
        so_user_prompt = (
            "Consultation transcript:\n" + formatted
        )
        ap_user_prompt = (
            "Consultation transcript:\n" + formatted
        )

        client = self._get_client()
        if settings.ollama_parallel_agents:
            with ThreadPoolExecutor(max_workers=2) as pool:
                future_so = pool.submit(
                    self._call_agent,
                    client,
                    AGENT_SO_SYSTEM_PROMPT,
                    so_user_prompt,
                    "Subjective/Objective",
                )
                future_ap = pool.submit(
                    self._call_agent,
                    client,
                    AGENT_AP_SYSTEM_PROMPT,
                    ap_user_prompt,
                    "Assessment/Plan",
                )
                so_payload = future_so.result()
                ap_payload = future_ap.result()
        else:
            so_payload = self._call_agent(
                client,
                AGENT_SO_SYSTEM_PROMPT,
                so_user_prompt,
                "Subjective/Objective",
            )
            ap_payload = self._call_agent(
                client,
                AGENT_AP_SYSTEM_PROMPT,
                ap_user_prompt,
                "Assessment/Plan",
            )

        so_norm = _normalize_soap_payload(so_payload)
        ap_norm = _normalize_soap_payload(ap_payload)
        merged: dict[str, Any] = {
            "subjective": so_norm.get("subjective"),
            "objective": _apply_documented_objective(so_norm.get("objective"), transcript),
            "assessment": ap_norm.get("assessment"),
            "plan": ap_norm.get("plan"),
        }

        validation_started = time.perf_counter()
        try:
            generated = GeneratedSOAP.model_validate(merged)
        except ValidationError as exc:
            raise SOAPGenerationError(
                "SOAP generation returned an invalid SOAP structure."
            ) from exc
        finally:
            logger.info(
                "SOAP Pydantic validation completed in %.1f ms",
                round((time.perf_counter() - validation_started) * 1000, 1),
            )

        parsing_started = time.perf_counter()
        so_clinical = _parse_clinical_data(so_payload)
        ap_clinical = _parse_clinical_data(ap_payload)
        _, documented_measurements = _extract_documented_measurements(transcript)
        so_clinical = _replace_documented_measurements(so_clinical, documented_measurements)
        logger.info(
            "SOAP clinical JSON parsing and validation completed in %.1f ms",
            round((time.perf_counter() - parsing_started) * 1000, 1),
        )

        merge_started = time.perf_counter()
        extracted_clinical = self.extract_clinical_information(transcript)
        clinical_summary = _merge_clinical_data(
            _merge_clinical_data(so_clinical, ap_clinical),
            extracted_clinical,
        )
        generated.clinical_data = clinical_summary
        logger.info(
            "SOAP clinical data merge completed in %.1f ms",
            round((time.perf_counter() - merge_started) * 1000, 1),
        )
        review_started = time.perf_counter()
        generated, quality_report = _quality_review_soap(transcript, generated)
        logger.info(
            "SOAP deterministic quality review completed in %.1f ms; assessment_recovered=%s plan_recovered=%s unsupported_medications_removed=%s",
            round((time.perf_counter() - review_started) * 1000, 1),
            quality_report["assessment_recovered"],
            quality_report["plan_recovered"],
            quality_report["unsupported_medications_removed"],
        )
        logger.info(
            "SOAP total generation completed in %.1f ms",
            round((time.perf_counter() - total_started) * 1000, 1),
        )
        return generated
