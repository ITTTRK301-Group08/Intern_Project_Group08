"""add analysis benchmark metadata

Revision ID: e71b3c9d4a20
Revises: d3f4a8c21b60
Create Date: 2026-11-13 23:59:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e71b3c9d4a20"
down_revision: str | Sequence[str] | None = "d3f4a8c21b60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("analyses") as batch_op:
        batch_op.add_column(
            sa.Column(
                "market_source",
                sa.String(150),
                nullable=False,
                server_default="Benchmark tham chiếu (danh mục kỹ năng/vị trí nội bộ)",
            )
        )
        batch_op.add_column(sa.Column("benchmark_date", sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("analyses") as batch_op:
        batch_op.drop_column("benchmark_date")
        batch_op.drop_column("market_source")
