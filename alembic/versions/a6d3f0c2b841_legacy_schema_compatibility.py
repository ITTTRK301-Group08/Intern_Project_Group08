"""recognize the legacy local schema revision

Revision ID: a6d3f0c2b841
Revises: b7e9c2d4f610, e5f6a7b8c9d0
"""

from collections.abc import Sequence

from alembic import op


revision: str = "a6d3f0c2b841"
down_revision: str | Sequence[str] | None = (
    "b7e9c2d4f610",
    "e5f6a7b8c9d0",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Adopt the legacy revision marker; schema differences are repaired next."""


def downgrade() -> None:
    """Keep this compatibility marker schema-neutral."""
