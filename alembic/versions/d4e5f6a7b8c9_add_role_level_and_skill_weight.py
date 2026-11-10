"""add career role level and role skill weight

Revision ID: d4e5f6a7b8c9
Revises: c1e49a7f2b30
Create Date: 2026-11-09 21:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "c1e49a7f2b30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEEDED_ROLE_LEVELS = {
    "backend-developer": "Junior",
    "frontend-developer": "Fresher",
    "data-analyst": "Intern",
    "machine-learning-engineer": "Junior",
    "cybersecurity-analyst": "Fresher",
    "ux-ui-designer": "Intern",
}

SEEDED_ROLE_SKILL_META = {
    ("backend-developer", "Python"): (True, 1.5),
    ("backend-developer", "SQL"): (True, 1.2),
    ("backend-developer", "Git"): (True, 1.0),
    ("backend-developer", "REST APIs"): (True, 1.5),
    ("backend-developer", "Linux"): (False, 0.8),
    ("frontend-developer", "JavaScript"): (True, 1.5),
    ("frontend-developer", "HTML and CSS"): (True, 1.4),
    ("frontend-developer", "Git"): (True, 1.0),
    ("frontend-developer", "REST APIs"): (False, 0.9),
    ("data-analyst", "SQL"): (True, 1.5),
    ("data-analyst", "Python"): (True, 1.2),
    ("data-analyst", "Data Visualization"): (True, 1.4),
    ("data-analyst", "Statistics"): (True, 1.1),
    ("machine-learning-engineer", "Python"): (True, 1.4),
    ("machine-learning-engineer", "SQL"): (False, 0.8),
    ("machine-learning-engineer", "Statistics"): (True, 1.3),
    ("machine-learning-engineer", "Machine Learning"): (True, 1.6),
    ("cybersecurity-analyst", "Linux"): (True, 1.4),
    ("cybersecurity-analyst", "Networking"): (True, 1.4),
    ("cybersecurity-analyst", "Threat Modeling"): (True, 1.2),
    ("ux-ui-designer", "UX Research"): (True, 1.5),
    ("ux-ui-designer", "Wireframing"): (True, 1.5),
    ("ux-ui-designer", "HTML and CSS"): (False, 0.8),
}


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.add_column(
        "career_roles",
        sa.Column(
            "level",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'Junior'"),
        ),
    )

    roles_table = sa.table(
        "career_roles",
        sa.column("id", sa.Integer()),
        sa.column("slug", sa.String()),
        sa.column("level", sa.String()),
    )
    for slug, level in SEEDED_ROLE_LEVELS.items():
        bind.execute(
            sa.update(roles_table).where(roles_table.c.slug == slug).values(level=level)
        )

    if dialect == "mysql":
        op.create_unique_constraint(
            "uq_career_roles_name_level", "career_roles", ["name", "level"]
        )
    else:
        with op.batch_alter_table("career_roles") as batch_op:
            batch_op.create_unique_constraint(
                "uq_career_roles_name_level", ["name", "level"]
            )

    op.add_column(
        "career_role_skills",
        sa.Column(
            "is_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.add_column(
        "career_role_skills",
        sa.Column(
            "weight",
            sa.Float(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )

    if dialect == "mysql":
        op.create_check_constraint(
            "ck_career_role_skill_weight", "career_role_skills", "weight > 0"
        )
    else:
        with op.batch_alter_table("career_role_skills") as batch_op:
            batch_op.create_check_constraint(
                "ck_career_role_skill_weight", "weight > 0"
            )

    skills_table = sa.table(
        "skills",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String()),
    )
    role_skills_table = sa.table(
        "career_role_skills",
        sa.column("career_role_id", sa.Integer()),
        sa.column("skill_id", sa.Integer()),
        sa.column("is_required", sa.Boolean()),
        sa.column("weight", sa.Float()),
    )
    for (role_slug, skill_name), (is_required, weight) in SEEDED_ROLE_SKILL_META.items():
        role_id_subq = (
            sa.select(roles_table.c.id)
            .where(roles_table.c.slug == role_slug)
            .scalar_subquery()
        )
        skill_id_subq = (
            sa.select(skills_table.c.id)
            .where(skills_table.c.name == skill_name)
            .scalar_subquery()
        )
        op.execute(
            sa.update(role_skills_table)
            .where(
                role_skills_table.c.career_role_id == role_id_subq,
                role_skills_table.c.skill_id == skill_id_subq,
            )
            .values(is_required=is_required, weight=weight)
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "mysql":
        op.drop_constraint(
            "ck_career_role_skill_weight", "career_role_skills", type_="check"
        )
        op.drop_column("career_role_skills", "weight")
        op.drop_column("career_role_skills", "is_required")
        op.drop_constraint(
            "uq_career_roles_name_level", "career_roles", type_="unique"
        )
        op.drop_column("career_roles", "level")
    else:
        with op.batch_alter_table("career_role_skills") as batch_op:
            batch_op.drop_constraint("ck_career_role_skill_weight", type_="check")
            batch_op.drop_column("weight")
            batch_op.drop_column("is_required")
        with op.batch_alter_table("career_roles") as batch_op:
            batch_op.drop_constraint("uq_career_roles_name_level", type_="unique")
            batch_op.drop_column("level")

