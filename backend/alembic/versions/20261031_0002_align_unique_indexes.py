"""align unique index definitions with ORM models

Revision ID: 20261031_0002
Revises: 20261031_0001
Create Date: 2026-10-31
"""

from alembic import op


revision = "20261031_0002"
down_revision = "20261031_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("patients_mrn_key", "patients", type_="unique")
    op.drop_index("ix_patients_mrn", table_name="patients")
    op.create_index("ix_patients_mrn", "patients", ["mrn"], unique=True)

    op.drop_constraint("transcripts_consultation_id_key", "transcripts", type_="unique")
    op.drop_index("ix_transcripts_consultation_id", table_name="transcripts")
    op.create_index("ix_transcripts_consultation_id", "transcripts", ["consultation_id"], unique=True)

    op.drop_constraint("soap_notes_consultation_id_key", "soap_notes", type_="unique")
    op.drop_index("ix_soap_notes_consultation_id", table_name="soap_notes")
    op.create_index("ix_soap_notes_consultation_id", "soap_notes", ["consultation_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_patients_mrn", table_name="patients")
    op.create_index("ix_patients_mrn", "patients", ["mrn"], unique=False)
    op.create_unique_constraint("patients_mrn_key", "patients", ["mrn"])

    op.drop_index("ix_transcripts_consultation_id", table_name="transcripts")
    op.create_index("ix_transcripts_consultation_id", "transcripts", ["consultation_id"], unique=False)
    op.create_unique_constraint(
        "transcripts_consultation_id_key", "transcripts", ["consultation_id"]
    )

    op.drop_index("ix_soap_notes_consultation_id", table_name="soap_notes")
    op.create_index("ix_soap_notes_consultation_id", "soap_notes", ["consultation_id"], unique=False)
    op.create_unique_constraint(
        "soap_notes_consultation_id_key", "soap_notes", ["consultation_id"]
    )
