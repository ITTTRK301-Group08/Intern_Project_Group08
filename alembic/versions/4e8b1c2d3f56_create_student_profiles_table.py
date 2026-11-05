"""create student_profiles table

Revision ID: 4e8b1c2d3f56
Revises: 1d4c3f9a2b10
Create Date: 2026-11-05 00:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4e8b1c2d3f56"
down_revision: str | Sequence[str] | None = "1d4c3f9a2b10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "student_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("major", sa.String(length=150), nullable=True),
        sa.Column("university", sa.String(length=200), nullable=True),
        sa.Column("strengths", sa.JSON(), nullable=True),
        sa.Column("self_assessed_skills", sa.JSON(), nullable=True),
        sa.Column("career_goal", sa.String(length=255), nullable=True),
        sa.Column("target_role_id", sa.Integer(), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_student_profiles_user_id"),
    )
    op.create_index("ix_student_profiles_user_id", "student_profiles", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_student_profiles_user_id", table_name="student_profiles")
    op.drop_table("student_profiles")
