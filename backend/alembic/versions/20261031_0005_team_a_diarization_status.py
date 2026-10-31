"""add Team A diarization status metadata

Revision ID: 20261031_0005
Revises: 20261031_0004
"""
from alembic import op
import sqlalchemy as sa

revision = "20261031_0005"
down_revision = "20261031_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "transcripts",
        sa.Column("diarization_status", sa.String(), nullable=False, server_default="disabled"),
    )
    op.add_column(
        "transcripts",
        sa.Column("diarization_error", sa.Text(), nullable=True),
    )
    op.alter_column("transcripts", "diarization_status", server_default=None)


def downgrade() -> None:
    op.drop_column("transcripts", "diarization_error")
    op.drop_column("transcripts", "diarization_status")
