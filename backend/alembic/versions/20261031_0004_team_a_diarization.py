"""add Team A speaker diarization metadata

Revision ID: 20261031_0004
Revises: 20261031_0003
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261031_0004"
down_revision = "20261031_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("transcripts", sa.Column(
        "speaker_mappings",
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
    ))
    op.add_column("transcript_entries", sa.Column("speaker_id", sa.String(), nullable=True))
    op.add_column("transcript_entries", sa.Column("speaker_display_name", sa.String(), nullable=True))
    op.add_column("transcript_entries", sa.Column("start_time_ms", sa.Integer(), nullable=True))
    op.add_column("transcript_entries", sa.Column("end_time_ms", sa.Integer(), nullable=True))
    op.create_index(
        "ix_transcript_entries_speaker_id",
        "transcript_entries",
        ["speaker_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_transcript_entries_speaker_id", table_name="transcript_entries")
    op.drop_column("transcript_entries", "end_time_ms")
    op.drop_column("transcript_entries", "start_time_ms")
    op.drop_column("transcript_entries", "speaker_display_name")
    op.drop_column("transcript_entries", "speaker_id")
    op.drop_column("transcripts", "speaker_mappings")
