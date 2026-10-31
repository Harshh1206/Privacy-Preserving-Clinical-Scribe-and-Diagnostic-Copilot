"""add Team A transcript processing status

Revision ID: 20261031_0003
Revises: 20261031_0002
"""
from alembic import op
import sqlalchemy as sa

revision = "20261031_0003"
down_revision = "20261031_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("transcripts", sa.Column("processing_status", sa.String(), nullable=False, server_default="completed"))
    op.add_column("transcripts", sa.Column("processing_error", sa.Text(), nullable=True))
    op.add_column("transcripts", sa.Column("processed_at", sa.String(), nullable=True))
    op.add_column("transcripts", sa.Column("model_name", sa.String(), nullable=True))
    op.create_index("ix_transcripts_processing_status", "transcripts", ["processing_status"], unique=False)
    op.alter_column("transcripts", "processing_status", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_transcripts_processing_status", table_name="transcripts")
    op.drop_column("transcripts", "model_name")
    op.drop_column("transcripts", "processed_at")
    op.drop_column("transcripts", "processing_error")
    op.drop_column("transcripts", "processing_status")
