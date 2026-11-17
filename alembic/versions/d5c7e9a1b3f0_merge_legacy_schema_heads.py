"""merge the current and legacy-schema migration branches

Revision ID: d5c7e9a1b3f0
Revises: a6c4d2e8f901, c8f19a2d4e60
"""

from collections.abc import Sequence

from alembic import op


revision: str = "d5c7e9a1b3f0"
down_revision: str | Sequence[str] | None = (
    "a6c4d2e8f901",
    "c8f19a2d4e60",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Merge migration histories without changing the schema."""


def downgrade() -> None:
    """Merge revisions do not change the schema."""
