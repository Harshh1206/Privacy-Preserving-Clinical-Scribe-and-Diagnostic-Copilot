from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.config import settings
from app.models.schemas import ClinicalData, Transcript


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


SYSTEM_PROMPT = """You are a clinical documentation assistant.
Convert only the supplied consultation transcript into a detailed SOAP note.

Rules:
- Use only facts explicitly stated in the transcript.
- Do not invent diagnoses, symptoms, medications, allergies, procedures, vitals, test results, or plans.
- Abnormal measurements are findings, not evidence that a treatment decision was made.
- The Plan must contain only documented actions, recommendations, tests, referrals, treatment instructions, or follow-up instructions.
- Separate documented decisions from items requiring clinician review in the Plan.
- Do not infer medication changes, investigations, lifestyle counselling, referrals, treatment, or follow-up schedules unless explicitly stated.
- If no plan is documented, write "No treatment or follow-up plan was documented in the transcript."
- Avoid repetitive generic filler.
- Clinical data extraction is conservative: use patient-reported or awaiting-review status unless the transcript explicitly documents confirmation.
- Distinguish patient-reported measurements from clinic-measured values and preserve source and units.
- Allergy entries require the substance and reaction when stated; verification must be reported or awaiting_review unless confirmed by the clinician.
- Preserve negations and uncertainty exactly (for example: denial of fever, possible diagnosis).
- If information is absent from the transcript, write "Not documented in the transcript."
- Return valid JSON only.
- Return exactly these keys: subjective, objective, assessment, plan.
- Each SOAP value must be a detailed clinical narrative string for that SOAP section.
- Do not add extra top-level keys."""


def _format_transcript(transcript: Transcript) -> str:
    lines = []
    for entry in transcript.entries:
        speaker = entry.speaker_display_name or entry.speaker or "Unknown speaker"
        lines.append(f"[{entry.timestamp}] {speaker}: {entry.text}")
    return "\n".join(lines)


def _normalize_json_content(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
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


class GroqSOAPGenerator:
    def generate(self, transcript: Transcript) -> GeneratedSOAP:
        if not settings.groq_api_key:
            raise SOAPGenerationError(
                "SOAP generation is unavailable because GROQ_API_KEY is not configured."
            )

        try:
            from groq import Groq
        except ImportError as exc:
            raise SOAPGenerationError(
                "SOAP generation is unavailable because the Groq SDK is not installed."
            ) from exc

        user_prompt = (
            "Create the SOAP JSON from this transcript:\n\n"
            + _format_transcript(transcript)
        )
        try:
            client = Groq(
                api_key=settings.groq_api_key,
                timeout=45,
                max_retries=1,
            )
            response = client.chat.completions.create(
                model=settings.team_b_soap_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )
        except Exception as exc:
            status_code = getattr(exc, "status_code", None)
            exception_name = exc.__class__.__name__.lower()
            if isinstance(exc, TimeoutError) or "timeout" in exception_name:
                raise SOAPGenerationError(
                    "SOAP generation timed out. Try again when the AI service is responsive."
                ) from exc
            if status_code in (401, 403):
                raise SOAPGenerationError(
                    "SOAP generation authentication failed. Verify GROQ_API_KEY."
                ) from exc
            if status_code == 429:
                raise SOAPGenerationError(
                    "SOAP generation rate limit reached. Try again later."
                ) from exc
            if status_code and 500 <= int(status_code) < 600:
                raise SOAPGenerationError(
                    "The SOAP generation service is temporarily unavailable."
                ) from exc
            raise SOAPGenerationError(
                "SOAP generation failed. Check the configured AI service and try again."
            ) from exc

        try:
            choices = getattr(response, "choices", None) or []
            content = choices[0].message.content if choices else None
        except (AttributeError, IndexError, TypeError):
            content = None
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        if not isinstance(content, str) or not content.strip():
            raise SOAPGenerationError("SOAP generation returned no content.")

        try:
            payload: dict[str, Any] = json.loads(_normalize_json_content(content))
        except json.JSONDecodeError as exc:
            raise SOAPGenerationError(
                "SOAP generation returned invalid JSON."
            ) from exc
        if not isinstance(payload, dict):
            raise SOAPGenerationError(
                "SOAP generation returned an invalid SOAP structure."
            )

        soap_payload = _normalize_soap_payload(payload)
        try:
            generated = GeneratedSOAP.model_validate(soap_payload)
        except ValidationError as exc:
            raise SOAPGenerationError(
                "SOAP generation returned an invalid SOAP structure."
            ) from exc

        generated.clinical_data = _parse_clinical_data(payload)
        return generated
