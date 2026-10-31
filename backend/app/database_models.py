from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Patient(Base):
    __tablename__ = "patients"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    mrn: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    dob: Mapped[str] = mapped_column(String, nullable=False)
    sex: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str | None] = mapped_column(String)
    allergies: Mapped[list[str]] = mapped_column(JSONB, default=list)
    conditions: Mapped[list[str]] = mapped_column(JSONB, default=list)
    medications: Mapped[list[str]] = mapped_column(JSONB, default=list)
    last_visit: Mapped[str | None] = mapped_column(String)
    consultation_count: Mapped[int] = mapped_column(Integer, default=0)
    privacy_level: Mapped[str] = mapped_column(String, default="standard")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    consultations: Mapped[list["Consultation"]] = relationship(back_populates="patient")


class Consultation(Base):
    __tablename__ = "consultations"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    date: Mapped[str] = mapped_column(String, nullable=False, index=True)
    chief_complaint: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    physician_id: Mapped[str] = mapped_column(String, nullable=False)
    physician_name: Mapped[str] = mapped_column(String, nullable=False)
    duration: Mapped[int | None] = mapped_column(Integer)
    transcript_id: Mapped[str | None] = mapped_column(String)
    soap_note_id: Mapped[str | None] = mapped_column(String)
    validation_id: Mapped[str | None] = mapped_column(String)
    finalised_at: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)
    safety_status: Mapped[str] = mapped_column(String, default="CLEAR")
    patient: Mapped["Patient"] = relationship(back_populates="consultations")
    transcript: Mapped["Transcript | None"] = relationship(back_populates="consultation", uselist=False)
    soap_note: Mapped["SOAPNote | None"] = relationship(back_populates="consultation", uselist=False)
    validation: Mapped["ValidationResult | None"] = relationship(back_populates="consultation", uselist=False)
    audits: Mapped[list["AuditEntry"]] = relationship(back_populates="consultation", cascade="all, delete-orphan")


class Transcript(Base):
    __tablename__ = "transcripts"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    consultation_id: Mapped[str] = mapped_column(ForeignKey("consultations.id", ondelete="CASCADE"), unique=True, index=True)
    recorded_at: Mapped[str] = mapped_column(String, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    language: Mapped[str] = mapped_column(String, default="en-US")
    consultation: Mapped["Consultation"] = relationship(back_populates="transcript")
    entries: Mapped[list["TranscriptEntry"]] = relationship(back_populates="transcript", cascade="all, delete-orphan")


class TranscriptEntry(Base):
    __tablename__ = "transcript_entries"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    transcript_id: Mapped[str] = mapped_column(ForeignKey("transcripts.id", ondelete="CASCADE"), index=True)
    consultation_id: Mapped[str] = mapped_column(String, index=True)
    timestamp: Mapped[str] = mapped_column(String, nullable=False)
    offset_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker: Mapped[str] = mapped_column(String, nullable=False)
    speaker_role: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    linked_claim_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float)
    transcript: Mapped["Transcript"] = relationship(back_populates="entries")


class SOAPNote(Base):
    __tablename__ = "soap_notes"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    consultation_id: Mapped[str] = mapped_column(ForeignKey("consultations.id", ondelete="CASCADE"), unique=True, index=True)
    subjective: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    objective: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    assessment: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    plan: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)
    is_finalized: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    finalized_at: Mapped[str | None] = mapped_column(String)
    finalized_by: Mapped[str | None] = mapped_column(String)
    version: Mapped[int] = mapped_column(Integer, default=1)
    consultation: Mapped["Consultation"] = relationship(back_populates="soap_note")


class ValidationResult(Base):
    __tablename__ = "validation_results"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    consultation_id: Mapped[str] = mapped_column(ForeignKey("consultations.id", ondelete="CASCADE"), index=True)
    soap_note_version: Mapped[int] = mapped_column(Integer, nullable=False)
    grounding_score: Mapped[int] = mapped_column(Integer, nullable=False)
    hallucination_risk: Mapped[str] = mapped_column(String, nullable=False)
    supported_count: Mapped[int] = mapped_column(Integer, nullable=False)
    unsupported_count: Mapped[int] = mapped_column(Integer, nullable=False)
    conflict_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_claim_count: Mapped[int] = mapped_column(Integer, nullable=False)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    validated_at: Mapped[str] = mapped_column(String, nullable=False)
    validation_notes: Mapped[str | None] = mapped_column(Text)
    consultation: Mapped["Consultation"] = relationship(back_populates="validation")
    claims: Mapped[list["ValidationClaim"]] = relationship(back_populates="validation", cascade="all, delete-orphan")
    evidence: Mapped[list["EvidenceRecord"]] = relationship(back_populates="validation", cascade="all, delete-orphan")


class ValidationClaim(Base):
    __tablename__ = "validation_claims"
    __table_args__ = (UniqueConstraint("validation_id", "id", name="uq_validation_claim"),)
    id: Mapped[str] = mapped_column(String, primary_key=True)
    validation_id: Mapped[str] = mapped_column(ForeignKey("validation_results.id", ondelete="CASCADE"), index=True)
    soap_section: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    conflict_description: Mapped[str | None] = mapped_column(Text)
    conflicting_entities: Mapped[list[str] | None] = mapped_column(JSONB)
    suggested_correction: Mapped[str | None] = mapped_column(Text)
    validation: Mapped["ValidationResult"] = relationship(back_populates="claims")


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    validation_id: Mapped[str] = mapped_column(ForeignKey("validation_results.id", ondelete="CASCADE"), index=True)
    transcript_entry_id: Mapped[str] = mapped_column(String, index=True)
    transcript_text: Mapped[str] = mapped_column(Text, nullable=False)
    speaker: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[str] = mapped_column(String, nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False)
    match_type: Mapped[str] = mapped_column(String, nullable=False)
    validation: Mapped["ValidationResult"] = relationship(back_populates="evidence")


class MedicalEntity(Base):
    __tablename__ = "medical_entities"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    consultation_id: Mapped[str | None] = mapped_column(ForeignKey("consultations.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    normalized_term: Mapped[str | None] = mapped_column(String)
    icd_code: Mapped[str | None] = mapped_column(String)
    rx_norm_code: Mapped[str | None] = mapped_column(String)


class TeamBState(Base):
    __tablename__ = "team_b_state"
    consultation_id: Mapped[str] = mapped_column(
        ForeignKey("consultations.id", ondelete="CASCADE"), primary_key=True
    )
    claims: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    entities: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    soap_version: Mapped[int] = mapped_column(Integer, default=1)


class AuditEntry(Base):
    __tablename__ = "audit_entries"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    consultation_id: Mapped[str] = mapped_column(ForeignKey("consultations.id", ondelete="CASCADE"), index=True)
    timestamp: Mapped[str] = mapped_column(String, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    soap_version: Mapped[int | None] = mapped_column(Integer)
    consultation: Mapped["Consultation"] = relationship(back_populates="audits")
