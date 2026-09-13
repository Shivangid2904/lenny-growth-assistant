"""Add unique constraint to transcript_chunks on episode_id and chunk_index

Revision ID: 0002_chunk_unique
Revises: 0001_initial_schema
Create Date: 2026-09-13 16:10:00

"""
from typing import Sequence, Union
from alembic import op

revision: str = "0002_chunk_unique"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_transcript_chunks_episode_chunk",
        "transcript_chunks",
        ["episode_id", "chunk_index"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_transcript_chunks_episode_chunk",
        "transcript_chunks",
        type_="unique",
    )
