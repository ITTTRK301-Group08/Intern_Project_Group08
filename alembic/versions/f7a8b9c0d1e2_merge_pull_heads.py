"""merge migration heads introduced by the pull

Revision ID: f7a8b9c0d1e2
Revises: c5d8e2f0b4a7, c5e9b22d7a01, e71b3c9d4a20
"""

from collections.abc import Sequence

from alembic import op


revision: str = "f7a8b9c0d1e2"
down_revision: str | Sequence[str] | None = (
    "c5d8e2f0b4a7",
    "c5e9b22d7a01",
    "e71b3c9d4a20",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Merge migration histories without changing the schema."""


def downgrade() -> None:
    """Merge revisions do not change the schema."""
