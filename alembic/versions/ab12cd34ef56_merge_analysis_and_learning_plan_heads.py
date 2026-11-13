"""merge analysis report and learning plan migration heads

Revision ID: ab12cd34ef56
Revises: e71b3c9d4a20, f8c2d1a96b40
Create Date: 2026-11-14 00:28:30.000000
"""

from collections.abc import Sequence

revision: str = "ab12cd34ef56"
down_revision: str | Sequence[str] | None = ("e71b3c9d4a20", "f8c2d1a96b40")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
