"""add provenance-preserving patient clinical records

Revision ID: 20261031_0006
Revises: 20261031_0005
"""
from alembic import op
import sqlalchemy as sa


revision = "20261031_0006"
down_revision = "20261031_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patient_clinical_records",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("patient_id", sa.String(), nullable=False),
        sa.Column("consultation_id", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("name_normalized", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=True),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("reaction", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("verification", sa.String(), nullable=False),
        sa.Column("recorded_at", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["consultation_id"], ["consultations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "patient_id", "consultation_id", "category", "name_normalized",
            "value", "unit", "source",
            name="uq_patient_clinical_record_consultation",
        ),
    )
    op.create_index(
        "ix_patient_clinical_records_patient_id",
        "patient_clinical_records",
        ["patient_id"],
    )
    op.create_index(
        "ix_patient_clinical_records_consultation_id",
        "patient_clinical_records",
        ["consultation_id"],
    )
    op.create_index(
        "ix_patient_clinical_records_category",
        "patient_clinical_records",
        ["category"],
    )
    op.create_index(
        "ix_patient_clinical_records_name_normalized",
        "patient_clinical_records",
        ["name_normalized"],
    )


def downgrade() -> None:
    op.drop_index("ix_patient_clinical_records_name_normalized", table_name="patient_clinical_records")
    op.drop_index("ix_patient_clinical_records_category", table_name="patient_clinical_records")
    op.drop_index("ix_patient_clinical_records_consultation_id", table_name="patient_clinical_records")
    op.drop_index("ix_patient_clinical_records_patient_id", table_name="patient_clinical_records")
    op.drop_table("patient_clinical_records")
