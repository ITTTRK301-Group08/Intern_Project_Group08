"""merge interview and analysis migration heads

Revision ID: 2c333ed80045
Revises: 4f2fe7519541, a1b2c3d4e5f6
Create Date: 2026-11-16 19:58:54.477677

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c333ed80045'
down_revision: Union[str, Sequence[str], None] = ('4f2fe7519541', 'a1b2c3d4e5f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
