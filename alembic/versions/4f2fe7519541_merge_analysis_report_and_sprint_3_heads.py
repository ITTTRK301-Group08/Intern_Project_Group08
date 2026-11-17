"""merge analysis report and sprint 3 heads

Revision ID: 4f2fe7519541
Revises: d3f4a8c21b60, f6a7b8c9d0e1
Create Date: 2026-11-16 14:12:27.824610

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4f2fe7519541'
down_revision: Union[str, Sequence[str], None] = ('d3f4a8c21b60', 'f6a7b8c9d0e1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
