"""add learning-resource approval workflow and project type

Revision ID: 91d2e7a4c6b8
Revises: 4f2fe7519541
Create Date: 2026-11-17 08:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "91d2e7a4c6b8"
down_revision: str | Sequence[str] | None = "4f2fe7519541"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEEDED_RESOURCE_SLUGS = (
    "python-tutorial",
    "sqlbolt-lessons",
    "git-documentation",
    "mdn-javascript-guide",
    "mdn-html-css",
    "kaggle-python",
    "kaggle-data-visualization",
    "kaggle-statistics",
    "google-ml-crash-course",
    "linux-journey",
    "owasp-top-ten",
    "cloudflare-learning-networking",
    "nng-ux-research",
    "figma-wireframing",
)


def upgrade() -> None:
    with op.batch_alter_table("learning_resources") as batch_op:
        batch_op.drop_constraint("ck_learning_resource_type", type_="check")
        batch_op.add_column(
            sa.Column(
                "approval_status",
                sa.String(length=20),
                nullable=False,
                server_default="pending",
            )
        )
        batch_op.create_check_constraint(
            "ck_learning_resource_type",
            "resource_type IN ('documentation', 'course', 'video', 'article', 'practice', 'project')",
        )
        batch_op.create_check_constraint(
            "ck_learning_resource_approval_status",
            "approval_status IN ('pending', 'approved', 'rejected')",
        )
        batch_op.create_index(
            "ix_learning_resources_approval_active_skill",
            ["approval_status", "is_active", "skill_id"],
        )

    op.execute(
        sa.text(
            "UPDATE learning_resources SET approval_status = 'approved' "
            "WHERE slug IN :slugs"
        ).bindparams(sa.bindparam("slugs", expanding=True)).params(
            slugs=list(SEEDED_RESOURCE_SLUGS)
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE learning_resources SET resource_type = 'practice' "
            "WHERE resource_type = 'project'"
        )
    )
    with op.batch_alter_table("learning_resources") as batch_op:
        batch_op.drop_index("ix_learning_resources_approval_active_skill")
        batch_op.drop_constraint(
            "ck_learning_resource_approval_status", type_="check"
        )
        batch_op.drop_constraint("ck_learning_resource_type", type_="check")
        batch_op.drop_column("approval_status")
        batch_op.create_check_constraint(
            "ck_learning_resource_type",
            "resource_type IN ('documentation', 'course', 'video', 'article', 'practice')",
        )
