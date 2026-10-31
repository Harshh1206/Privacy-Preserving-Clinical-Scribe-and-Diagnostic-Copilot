from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


def to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        extra="ignore",
    )


PatientSex = Literal["M", "F", "O"]
ConsultationStatus = Literal["scheduled", "in-progress", "pending-review", "finalized", "cancelled"]
SafetyStatus = Literal["CLEAR", "CONFLICT_DETECTED"]
ClaimStatus = Literal["supported", "unsupported", "conflict", "pending"]
Severity = Literal["low", "medium", "high", "critical"]
HallucinationRisk = Literal["low", "moderate", "high"]
ExportFormat = Literal["pdf", "fhir", "ehr"]
SpeakerRole = Literal["physician", "patient", "nurse", "system"]
SoapSectionKey = Literal["subjective", "objective", "assessment", "plan"]
PrivacyLevel = Literal["standard", "sensitive", "restricted"]
EntityType = Literal["symptom", "diagnosis", "medication", "procedure", "lab", "allergy", "vital"]
MatchType = Literal["exact", "semantic", "inferred"]
AuditAction = Literal["created", "edited", "validated", "revalidated", "finalized", "exported", "sent_to_ehr"]


class Patient(CamelModel):
    id: str
    mrn: str
    first_name: str
    last_name: str
    dob: str
    sex: PatientSex
    phone: Optional[str] = None
    allergies: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    last_visit: Optional[str] = None
    consultation_count: int = 0
    privacy_level: PrivacyLevel = "standard"


class Consultation(CamelModel):
    id: str
    patient_id: str
    date: str
    chief_complaint: str
    status: ConsultationStatus
    physician_id: str
    physician_name: str
    duration: Optional[int] = None
    transcript_id: str
    soap_note_id: str
    validation_id: Optional[str] = None
    finalised_at: Optional[str] = None
    created_at: str
    updated_at: str
    safety_status: SafetyStatus = "CLEAR"


class TranscriptEntry(CamelModel):
    id: str
    consultation_id: str
    timestamp: str
    offset_ms: int
    speaker: str
    speaker_role: SpeakerRole
    text: str
    linked_claim_ids: Optional[list[str]] = None
    confidence: Optional[float] = None


class Transcript(CamelModel):
    id: str
    consultation_id: str
    entries: list[TranscriptEntry] = Field(default_factory=list)
    recorded_at: str
    duration_ms: int
    language: str = "en-US"


class SOAPSection(CamelModel):
    text: str
    last_edited_at: Optional[str] = None
    last_edited_by: Optional[str] = None


class SOAPNote(CamelModel):
    id: str
    consultation_id: str
    subjective: SOAPSection
    objective: SOAPSection
    assessment: SOAPSection
    plan: SOAPSection
    created_at: str
    updated_at: str
    is_finalized: bool = False
    finalized_at: Optional[str] = None
    finalized_by: Optional[str] = None
    version: int = 1


class SOAPNotePatch(CamelModel):
    subjective: Optional[SOAPSection] = None
    objective: Optional[SOAPSection] = None
    assessment: Optional[SOAPSection] = None
    plan: Optional[SOAPSection] = None


class MedicalEntity(CamelModel):
    id: str
    text: str
    type: EntityType
    normalized_term: Optional[str] = None
    icd_code: Optional[str] = None
    rx_norm_code: Optional[str] = None


class Evidence(CamelModel):
    id: str
    transcript_entry_id: str
    transcript_text: str
    speaker: str
    timestamp: str
    relevance_score: float
    match_type: MatchType = "semantic"


class Claim(CamelModel):
    id: str
    soap_section: SoapSectionKey
    text: str
    status: ClaimStatus
    severity: Severity
    evidence_ids: list[str] = Field(default_factory=list)
    conflict_description: Optional[str] = None
    conflicting_entities: Optional[list[str]] = None
    suggested_correction: Optional[str] = None


class ValidationResult(CamelModel):
    id: str
    consultation_id: str
    soap_note_version: int
    claims: list[Claim] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    grounding_score: int
    hallucination_risk: HallucinationRisk
    supported_count: int
    unsupported_count: int
    conflict_count: int
    total_claim_count: int
    is_stale: bool = False
    validated_at: str
    validation_notes: Optional[str] = None


class AuditEntry(CamelModel):
    id: str
    consultation_id: str
    timestamp: str
    action: AuditAction
    actor: str
    detail: str
    soap_version: Optional[int] = None


class ExportRequest(CamelModel):
    consultation_id: str
    format: ExportFormat
    include_transcript: bool = False
    include_validation: bool = True


class ExportResult(CamelModel):
    format: ExportFormat
    filename: str
    content: str
    generated_at: str


class EHRResult(CamelModel):
    success: bool
    confirmation_id: str
    message: str


class FinalizeRequest(CamelModel):
    physician_id: str
    physician_name: str


class FinalizeResponse(CamelModel):
    consultation: Consultation
    soap_note: SOAPNote


class TeamBIngest(CamelModel):
    """Structured Team B payload. Scores are ignored and recomputed."""

    consultation_id: str
    soap_note: SOAPNote
    entities: list[MedicalEntity] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    transcript: Optional[Transcript] = None


class TeamBConflict(CamelModel):
    type: str
    allergy: str
    medication: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    status: Literal["BLOCKED", "REVIEW"]
    message: str


class TeamBPatientInfo(CamelModel):
    demographics: dict[str, Any] = Field(default_factory=dict)
    allergies: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)


class TeamBSOAPNote(CamelModel):
    subjective: str = ""
    objective: str = ""
    assessment: str = ""
    plan: str = ""


class TeamBResponse(CamelModel):
    """Official Team B response contract. Grounding data is intentionally absent."""

    patient_info: TeamBPatientInfo = Field(default_factory=TeamBPatientInfo)
    soap_note: TeamBSOAPNote = Field(default_factory=TeamBSOAPNote)
    conflicts: list[TeamBConflict] = Field(default_factory=list)
    safety_status: SafetyStatus = "CLEAR"


class TeamBIngestResponse(CamelModel):
    consultation: Consultation
    soap_note: SOAPNote
    validation: ValidationResult
    entities: list[MedicalEntity] = Field(default_factory=list)


class ErrorBody(CamelModel):
    detail: str | list[Any]
