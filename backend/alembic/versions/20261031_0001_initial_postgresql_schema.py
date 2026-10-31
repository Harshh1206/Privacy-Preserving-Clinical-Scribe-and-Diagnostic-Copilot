"""initial PostgreSQL clinical scribe schema

Revision ID: 20261031_0001
Revises:
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261031_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("patients",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("mrn", sa.String(), nullable=False),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column("dob", sa.String(), nullable=False),
        sa.Column("sex", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("allergies", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("medications", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("last_visit", sa.String(), nullable=True),
        sa.Column("consultation_count", sa.Integer(), nullable=False),
        sa.Column("privacy_level", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("mrn"))
    op.create_index("ix_patients_mrn", "patients", ["mrn"], unique=False)

    op.create_table("consultations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("patient_id", sa.String(), nullable=False),
        sa.Column("date", sa.String(), nullable=False),
        sa.Column("chief_complaint", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("physician_id", sa.String(), nullable=False),
        sa.Column("physician_name", sa.String(), nullable=False),
        sa.Column("duration", sa.Integer(), nullable=True),
        sa.Column("transcript_id", sa.String(), nullable=True),
        sa.Column("soap_note_id", sa.String(), nullable=True),
        sa.Column("validation_id", sa.String(), nullable=True),
        sa.Column("finalised_at", sa.String(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
        sa.Column("safety_status", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_consultations_patient_id", "consultations", ["patient_id"], unique=False)
    op.create_index("ix_consultations_date", "consultations", ["date"], unique=False)
    op.create_index("ix_consultations_status", "consultations", ["status"], unique=False)

    op.create_table("transcripts",
        sa.Column("id", sa.String(), nullable=False), sa.Column("consultation_id", sa.String(), nullable=False),
        sa.Column("recorded_at", sa.String(), nullable=False), sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["consultation_id"], ["consultations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("consultation_id"))
    op.create_index("ix_transcripts_consultation_id", "transcripts", ["consultation_id"], unique=False)
    op.create_table("transcript_entries",
        sa.Column("id", sa.String(), nullable=False), sa.Column("transcript_id", sa.String(), nullable=False),
        sa.Column("consultation_id", sa.String(), nullable=False), sa.Column("timestamp", sa.String(), nullable=False),
        sa.Column("offset_ms", sa.Integer(), nullable=False), sa.Column("speaker", sa.String(), nullable=False),
        sa.Column("speaker_role", sa.String(), nullable=False), sa.Column("text", sa.Text(), nullable=False),
        sa.Column("linked_claim_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["transcript_id"], ["transcripts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_transcript_entries_transcript_id", "transcript_entries", ["transcript_id"], unique=False)
    op.create_index("ix_transcript_entries_consultation_id", "transcript_entries", ["consultation_id"], unique=False)

    op.create_table("soap_notes",
        sa.Column("id", sa.String(), nullable=False), sa.Column("consultation_id", sa.String(), nullable=False),
        sa.Column("subjective", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("objective", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("assessment", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("plan", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False), sa.Column("updated_at", sa.String(), nullable=False),
        sa.Column("is_finalized", sa.Boolean(), nullable=False), sa.Column("finalized_at", sa.String(), nullable=True),
        sa.Column("finalized_by", sa.String(), nullable=True), sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["consultation_id"], ["consultations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("consultation_id"))
    op.create_index("ix_soap_notes_consultation_id", "soap_notes", ["consultation_id"], unique=False)
    op.create_index("ix_soap_notes_is_finalized", "soap_notes", ["is_finalized"], unique=False)

    op.create_table("validation_results",
        sa.Column("id", sa.String(), nullable=False), sa.Column("consultation_id", sa.String(), nullable=False),
        sa.Column("soap_note_version", sa.Integer(), nullable=False), sa.Column("grounding_score", sa.Integer(), nullable=False),
        sa.Column("hallucination_risk", sa.String(), nullable=False), sa.Column("supported_count", sa.Integer(), nullable=False),
        sa.Column("unsupported_count", sa.Integer(), nullable=False), sa.Column("conflict_count", sa.Integer(), nullable=False),
        sa.Column("total_claim_count", sa.Integer(), nullable=False), sa.Column("is_stale", sa.Boolean(), nullable=False),
        sa.Column("validated_at", sa.String(), nullable=False), sa.Column("validation_notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["consultation_id"], ["consultations.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_validation_results_consultation_id", "validation_results", ["consultation_id"], unique=False)
    op.create_index("ix_validation_results_is_stale", "validation_results", ["is_stale"], unique=False)
    op.create_table("validation_claims",
        sa.Column("id", sa.String(), nullable=False), sa.Column("validation_id", sa.String(), nullable=False),
        sa.Column("soap_section", sa.String(), nullable=False), sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False), sa.Column("severity", sa.String(), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("conflict_description", sa.Text(), nullable=True),
        sa.Column("conflicting_entities", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("suggested_correction", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["validation_id"], ["validation_results.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("validation_id", "id", name="uq_validation_claim"))
    op.create_index("ix_validation_claims_validation_id", "validation_claims", ["validation_id"], unique=False)
    op.create_table("evidence_records",
        sa.Column("id", sa.String(), nullable=False), sa.Column("validation_id", sa.String(), nullable=False),
        sa.Column("transcript_entry_id", sa.String(), nullable=False), sa.Column("transcript_text", sa.Text(), nullable=False),
        sa.Column("speaker", sa.String(), nullable=False), sa.Column("timestamp", sa.String(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=False), sa.Column("match_type", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["validation_id"], ["validation_results.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_evidence_records_validation_id", "evidence_records", ["validation_id"], unique=False)
    op.create_index("ix_evidence_records_transcript_entry_id", "evidence_records", ["transcript_entry_id"], unique=False)

    op.create_table("medical_entities",
        sa.Column("id", sa.String(), nullable=False), sa.Column("consultation_id", sa.String(), nullable=True),
        sa.Column("text", sa.String(), nullable=False), sa.Column("type", sa.String(), nullable=False),
        sa.Column("normalized_term", sa.String(), nullable=True), sa.Column("icd_code", sa.String(), nullable=True),
        sa.Column("rx_norm_code", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["consultation_id"], ["consultations.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_medical_entities_consultation_id", "medical_entities", ["consultation_id"], unique=False)
    op.create_table("team_b_state",
        sa.Column("consultation_id", sa.String(), nullable=False),
        sa.Column("claims", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("entities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("soap_version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["consultation_id"], ["consultations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("consultation_id"))
    op.create_table("audit_entries",
        sa.Column("id", sa.String(), nullable=False), sa.Column("consultation_id", sa.String(), nullable=False),
        sa.Column("timestamp", sa.String(), nullable=False), sa.Column("action", sa.String(), nullable=False),
        sa.Column("actor", sa.String(), nullable=False), sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("soap_version", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["consultation_id"], ["consultations.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_audit_entries_consultation_id", "audit_entries", ["consultation_id"], unique=False)
    op.create_index("ix_audit_entries_timestamp", "audit_entries", ["timestamp"], unique=False)


def downgrade() -> None:
    for table in ("audit_entries", "team_b_state", "medical_entities", "evidence_records",
                  "validation_claims", "validation_results", "soap_notes", "transcript_entries",
                  "transcripts", "consultations", "patients"):
        op.drop_table(table)
