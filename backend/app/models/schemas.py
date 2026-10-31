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
SpeakerRole = Literal["doctor", "physician", "patient", "nurse", "system", "unknown"]
SoapSectionKey = Literal["subjective", "objective", "assessment", "plan"]
PrivacyLevel = Literal["standard", "sensitive", "restricted"]
EntityType = Literal["symptom", "diagnosis", "medication", "procedure", "lab", "allergy", "vital"]
MatchType = Literal["exact", "semantic", "inferred"]
AuditAction = Literal["created", "generated", "edited", "validated", "revalidated", "finalized", "exported", "sent_to_ehr"]


class ClinicalRecord(CamelModel):
    id: str
    patient_id: str
    consultation_id: str
    category: Literal["condition", "medication", "measurement", "allergy"]
    name: str
    value: Optional[str] = None
    unit: Optional[str] = None
    source: Optional[str] = None
    reaction: Optional[str] = None
    status: Optional[str] = None
    verification: Literal["confirmed", "reported", "awaiting_review"] = "reported"
    recorded_at: Optional[str] = None
    updated_at: str


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
    clinical_records: list[ClinicalRecord] = Field(default_factory=list)
    last_visit: Optional[str] = None
    consultation_count: int = 0
    privacy_level: PrivacyLevel = "standard"


class CreatePatientRequest(CamelModel):
    mrn: str = Field(min_length=1, max_length=100)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    dob: str = Field(min_length=1, max_length=10)
    sex: PatientSex
    phone: Optional[str] = None
    allergies: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
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
    speaker_id: Optional[str] = None
    speaker_display_name: Optional[str] = None
    start_time_ms: Optional[int] = None
    end_time_ms: Optional[int] = None
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
    processing_status: Literal["pending", "processing", "completed", "failed"] = "completed"
    processing_error: Optional[str] = None
    processed_at: Optional[str] = None
    model_name: Optional[str] = None
    speaker_mappings: dict[str, dict[str, str]] = Field(default_factory=dict)
    diarization_status: Literal["disabled", "processing", "completed", "failed"] = "disabled"
    diarization_error: Optional[str] = None


class SpeakerMappingRequest(CamelModel):
    speaker_role: Literal["doctor", "patient", "unknown"]
    speaker_display_name: str = Field(min_length=1, max_length=100)


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


class ClinicalCondition(CamelModel):
    name: str = Field(min_length=1, max_length=200)
    status: Literal["active", "reported", "resolved", "unknown"] = "reported"
    verification: Literal["confirmed", "reported", "awaiting_review"] = "reported"
    source_consultation_id: Optional[str] = None


class ClinicalMedication(CamelModel):
    name: str = Field(min_length=1, max_length=200)
    dose: Optional[str] = None
    frequency: Optional[str] = None
    status: Literal["current", "reported_current", "discontinued", "unknown"] = "reported_current"
    verification: Literal["confirmed", "reported", "awaiting_review"] = "reported"
    source_consultation_id: Optional[str] = None


class ClinicalMeasurement(CamelModel):
    name: str = Field(min_length=1, max_length=200)
    value: Optional[str] = None
    unit: Optional[str] = None
    source: Literal["patient_reported", "clinic_measured", "unknown"] = "unknown"
    recorded_at: Optional[str] = None
    verification: Literal["confirmed", "reported", "awaiting_review"] = "reported"
    source_consultation_id: Optional[str] = None


class ClinicalAllergy(CamelModel):
    substance: str = Field(min_length=1, max_length=200)
    reaction: Optional[str] = None
    verification: Literal["confirmed", "reported", "awaiting_review"] = "reported"
    source_consultation_id: Optional[str] = None


class ClinicalData(CamelModel):
    conditions: list[ClinicalCondition] = Field(default_factory=list)
    medications: list[ClinicalMedication] = Field(default_factory=list)
    measurements: list[ClinicalMeasurement] = Field(default_factory=list)
    allergies: list[ClinicalAllergy] = Field(default_factory=list)


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


class CreateConsultationRequest(CamelModel):
    patient_id: str
    chief_complaint: str = Field(min_length=1)
    physician_id: str = Field(min_length=1)
    physician_name: str = Field(min_length=1)
    duration: Optional[int] = Field(default=None, ge=0)


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
