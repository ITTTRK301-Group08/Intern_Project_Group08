"""merge refresh token and legacy heads

Revision ID: 0809bd421a27
Revises: 2c333ed80045, d5c7e9a1b3f0
Create Date: 2026-11-17 19:04:39.956361

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0809bd421a27'
down_revision: Union[str, Sequence[str], None] = ('2c333ed80045', 'd5c7e9a1b3f0')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
