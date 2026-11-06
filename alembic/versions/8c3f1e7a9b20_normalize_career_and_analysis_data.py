"""normalize career and analysis data

Revision ID: 8c3f1e7a9b20
Revises: 7a2b3c4d5e6f
Create Date: 2026-11-06 13:40:00.000000
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8c3f1e7a9b20"
down_revision: str | Sequence[str] | None = "7a2b3c4d5e6f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TABLE_OPTIONS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


def _json_value(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return value


def _profile_rows(connection):
    profiles = sa.table(
        "student_profiles",
        sa.column("id", sa.Integer()),
        sa.column("strengths", sa.JSON()),
        sa.column("self_assessed_skills", sa.JSON()),
        sa.column("target_role_id", sa.Integer()),
    )
    return connection.execute(
        sa.select(
            profiles.c.id,
            profiles.c.strengths,
            profiles.c.self_assessed_skills,
            profiles.c.target_role_id,
        )
    ).mappings().all()


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "mysql":
        for table_name in ("users", "student_profiles", "cvs"):
            op.execute(
                f"ALTER TABLE `{table_name}` ENGINE=InnoDB "
                "DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci"
            )

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_student_profiles_user_id", table_name="student_profiles")

    op.create_table(
        "career_categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_career_categories_name"),
        sa.UniqueConstraint("slug", name="uq_career_categories_slug"),
        **TABLE_OPTIONS,
    )
    op.create_table(
        "career_roles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("slug", sa.String(length=170), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["career_categories.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_career_roles_slug"),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_career_roles_category_id", "career_roles", ["category_id"])
    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_skills_name"),
        **TABLE_OPTIONS,
    )

    profile_rows = _profile_rows(bind)
    bind.execute(
        sa.text(
            "UPDATE student_profiles SET target_role_id = NULL "
            "WHERE target_role_id <= 0"
        )
    )
    if dialect == "mysql":
        imported_role_ids = {
            row["target_role_id"]
            for row in profile_rows
            if row["target_role_id"] is not None and row["target_role_id"] > 0
        }
        for role_id in sorted(imported_role_ids):
            if role_id > 0:
                bind.execute(
                    sa.text(
                        "INSERT INTO career_roles "
                        "(id, name, slug, is_active, created_at) "
                        "VALUES (:id, :name, :slug, 1, CURRENT_TIMESTAMP)"
                    ),
                    {
                        "id": role_id,
                        "name": f"Imported role {role_id}",
                        "slug": f"imported-role-{role_id}",
                    },
                )
    else:
        roles = sa.table(
            "career_roles",
            sa.column("id", sa.Integer()),
            sa.column("name", sa.String()),
            sa.column("slug", sa.String()),
            sa.column("is_active", sa.Boolean()),
        )
        imported_role_ids = {
            row["target_role_id"]
            for row in profile_rows
            if row["target_role_id"] is not None and row["target_role_id"] > 0
        }
        for role_id in sorted(imported_role_ids):
            bind.execute(
                sa.insert(roles).values(
                    id=role_id,
                    name=f"Imported role {role_id}",
                    slug=f"imported-role-{role_id}",
                    is_active=True,
                )
            )

    if dialect == "mysql":
        op.drop_column("student_profiles", "strengths")
        op.drop_column("student_profiles", "self_assessed_skills")
        op.create_foreign_key(
            "fk_student_profiles_target_role_id_career_roles",
            "student_profiles",
            "career_roles",
            ["target_role_id"],
            ["id"],
            ondelete="SET NULL",
        )
    else:
        with op.batch_alter_table("student_profiles", recreate="always") as batch_op:
            batch_op.drop_column("strengths")
            batch_op.drop_column("self_assessed_skills")
            batch_op.create_foreign_key(
                "fk_student_profiles_target_role_id_career_roles",
                "career_roles",
                ["target_role_id"],
                ["id"],
                ondelete="SET NULL",
            )

    op.create_table(
        "profile_strengths",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("strength", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["student_profiles.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "strength", name="uq_profile_strength"),
        **TABLE_OPTIONS,
    )
    op.create_table(
        "profile_skills",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "level >= 0 AND level <= 5", name="ck_profile_skill_level"
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["student_profiles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "skill_id", name="uq_profile_skill"),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_profile_skills_skill_id", "profile_skills", ["skill_id"])
    op.create_table(
        "career_role_skills",
        sa.Column("career_role_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column(
            "required_level",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("3"),
        ),
        sa.CheckConstraint(
            "required_level >= 0 AND required_level <= 5",
            name="ck_career_role_skill_level",
        ),
        sa.ForeignKeyConstraint(
            ["career_role_id"], ["career_roles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("career_role_id", "skill_id"),
        **TABLE_OPTIONS,
    )
    op.create_index(
        "ix_career_role_skills_skill_id", "career_role_skills", ["skill_id"]
    )
    op.create_table(
        "cv_experiences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cv_id", sa.Integer(), nullable=False),
        sa.Column("job_title", sa.String(length=150), nullable=False),
        sa.Column("company", sa.String(length=150), nullable=True),
        sa.Column("location", sa.String(length=150), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="ck_cv_experience_dates",
        ),
        sa.ForeignKeyConstraint(["cv_id"], ["cvs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_cv_experiences_cv_id", "cv_experiences", ["cv_id"])
    op.create_table(
        "cv_educations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cv_id", sa.Integer(), nullable=False),
        sa.Column("institution", sa.String(length=200), nullable=False),
        sa.Column("degree", sa.String(length=120), nullable=True),
        sa.Column("field_of_study", sa.String(length=150), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="ck_cv_education_dates",
        ),
        sa.ForeignKeyConstraint(["cv_id"], ["cvs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_cv_educations_cv_id", "cv_educations", ["cv_id"])
    op.create_table(
        "analyses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("cv_id", sa.Integer(), nullable=True),
        sa.Column("career_role_id", sa.Integer(), nullable=True),
        sa.Column(
            "consent_accepted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column("consent_purpose_version", sa.String(length=20), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "consent_accepted = 1", name="ck_analysis_consent_accepted"
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_analysis_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cv_id"], ["cvs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["career_role_id"], ["career_roles.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_analyses_user_created", "analyses", ["user_id", "created_at"])
    op.create_table(
        "analysis_skill_gaps",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("analysis_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("current_level", sa.Integer(), nullable=False),
        sa.Column("target_level", sa.Integer(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "current_level >= 0 AND current_level <= 5 "
            "AND target_level >= 0 AND target_level <= 5 "
            "AND target_level >= current_level",
            name="ck_analysis_skill_gap_levels",
        ),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_id", "skill_id", name="uq_analysis_skill_gap"),
        **TABLE_OPTIONS,
    )
    op.create_index(
        "ix_analysis_skill_gaps_skill_id", "analysis_skill_gaps", ["skill_id"]
    )

    skills_table = sa.table(
        "skills",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String()),
    )
    strengths_table = sa.table(
        "profile_strengths",
        sa.column("profile_id", sa.Integer()),
        sa.column("strength", sa.String()),
    )
    profile_skills_table = sa.table(
        "profile_skills",
        sa.column("profile_id", sa.Integer()),
        sa.column("skill_id", sa.Integer()),
        sa.column("level", sa.Integer()),
    )
    known_skills: dict[str, int] = {}
    for row in profile_rows:
        profile_id = row["id"]
        strengths = _json_value(row["strengths"])
        if isinstance(strengths, list):
            seen_strengths: set[str] = set()
            for value in strengths:
                if not isinstance(value, str) or not value.strip():
                    continue
                strength = value.strip()
                normalized_strength = strength.casefold()
                if normalized_strength in seen_strengths:
                    continue
                seen_strengths.add(normalized_strength)
                bind.execute(
                    sa.insert(strengths_table).values(
                        profile_id=profile_id, strength=strength
                    )
                )

        assessments = _json_value(row["self_assessed_skills"])
        if not isinstance(assessments, list):
            continue
        levels_by_name: dict[str, tuple[str, int]] = {}
        for assessment in assessments:
            if not isinstance(assessment, dict):
                continue
            name = assessment.get("skill_name")
            level = assessment.get("level")
            if (
                not isinstance(name, str)
                or not name.strip()
                or not isinstance(level, int)
                or isinstance(level, bool)
                or not 0 <= level <= 5
            ):
                continue
            name = name.strip()
            levels_by_name[name.casefold()] = (name, level)

        for normalized_name, (name, level) in levels_by_name.items():
            skill_id = known_skills.get(normalized_name)
            if skill_id is None:
                existing_id = bind.scalar(
                    sa.select(skills_table.c.id).where(
                        sa.func.lower(skills_table.c.name) == name.lower()
                    )
                )
                if existing_id is None:
                    bind.execute(sa.insert(skills_table).values(name=name))
                    existing_id = bind.scalar(
                        sa.select(skills_table.c.id).where(
                            sa.func.lower(skills_table.c.name) == name.lower()
                        )
                    )
                if existing_id is None:
                    raise RuntimeError(f"Unable to migrate legacy skill {name!r}")
                skill_id = int(existing_id)
                known_skills[normalized_name] = skill_id
            bind.execute(
                sa.insert(profile_skills_table).values(
                    profile_id=profile_id, skill_id=skill_id, level=level
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    profile_rows = bind.execute(
        sa.text("SELECT id FROM student_profiles")
    ).mappings().all()
    strengths_table = sa.table(
        "profile_strengths",
        sa.column("profile_id", sa.Integer()),
        sa.column("strength", sa.String()),
    )
    profile_skills_table = sa.table(
        "profile_skills",
        sa.column("profile_id", sa.Integer()),
        sa.column("skill_id", sa.Integer()),
        sa.column("level", sa.Integer()),
    )
    skills_table = sa.table(
        "skills",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String()),
    )
    restored_profiles: list[tuple[int, list[str], list[dict[str, object]]]] = []
    for profile in profile_rows:
        profile_id = profile["id"]
        strengths = bind.execute(
            sa.select(strengths_table.c.strength)
            .where(strengths_table.c.profile_id == profile_id)
            .order_by(strengths_table.c.strength)
        ).scalars().all()
        assessments = bind.execute(
            sa.select(skills_table.c.name, profile_skills_table.c.level)
            .select_from(
                profile_skills_table.join(
                    skills_table,
                    profile_skills_table.c.skill_id == skills_table.c.id,
                )
            )
            .where(profile_skills_table.c.profile_id == profile_id)
            .order_by(skills_table.c.name)
        ).mappings().all()
        restored_profiles.append(
            (
                profile_id,
                list(strengths),
                [
                    {"skill_name": item["name"], "level": item["level"]}
                    for item in assessments
                ],
            )
        )

    for table_name in (
        "analysis_skill_gaps",
        "analyses",
        "cv_educations",
        "cv_experiences",
        "career_role_skills",
        "profile_skills",
        "profile_strengths",
    ):
        op.drop_table(table_name)

    if dialect == "mysql":
        op.drop_constraint(
            "fk_student_profiles_target_role_id_career_roles",
            "student_profiles",
            type_="foreignkey",
        )
        op.add_column(
            "student_profiles", sa.Column("strengths", sa.JSON(), nullable=True)
        )
        op.add_column(
            "student_profiles",
            sa.Column("self_assessed_skills", sa.JSON(), nullable=True),
        )
        profiles_table = sa.table(
            "student_profiles",
            sa.column("id", sa.Integer()),
            sa.column("strengths", sa.JSON()),
            sa.column("self_assessed_skills", sa.JSON()),
        )
        for profile_id, strengths, assessments in restored_profiles:
            bind.execute(
                sa.update(profiles_table)
                .where(profiles_table.c.id == profile_id)
                .values(strengths=strengths, self_assessed_skills=assessments)
            )
    else:
        with op.batch_alter_table("student_profiles", recreate="always") as batch_op:
            batch_op.drop_constraint(
                "fk_student_profiles_target_role_id_career_roles",
                type_="foreignkey",
            )
            batch_op.add_column(sa.Column("strengths", sa.JSON(), nullable=True))
            batch_op.add_column(
                sa.Column("self_assessed_skills", sa.JSON(), nullable=True)
            )
        profiles_table = sa.table(
            "student_profiles",
            sa.column("id", sa.Integer()),
            sa.column("strengths", sa.JSON()),
            sa.column("self_assessed_skills", sa.JSON()),
        )
        for profile_id, strengths, assessments in restored_profiles:
            bind.execute(
                sa.update(profiles_table)
                .where(profiles_table.c.id == profile_id)
                .values(strengths=strengths, self_assessed_skills=assessments)
            )

    op.drop_index("ix_career_roles_category_id", table_name="career_roles")
    op.drop_table("career_roles")
    op.drop_table("career_categories")
    op.drop_table("skills")
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index(
        "ix_student_profiles_user_id",
        "student_profiles",
        ["user_id"],
        unique=True,
    )
