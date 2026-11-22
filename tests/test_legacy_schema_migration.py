from pathlib import Path
import runpy

import sqlalchemy as sa
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = (
    ROOT
    / "alembic"
    / "versions"
    / "c8f19a2d4e60_reconcile_legacy_skill_gap_evidence.py"
)
VERSIONS_PATH = ROOT / "alembic" / "versions"


def _run_migration(connection, path: Path, migration_name: str = "upgrade") -> None:
    migration = runpy.run_path(str(path))
    context = MigrationContext.configure(connection)
    with Operations.context(context):
        migration[migration_name]()


def test_legacy_skill_gap_schema_gets_evidence_fields_and_constraint():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    "CREATE TABLE analysis_skill_gaps "
                    "(id INTEGER PRIMARY KEY, current_level INTEGER NOT NULL)"
                )
            )
            connection.execute(
                sa.text(
                    "INSERT INTO analysis_skill_gaps (id, current_level) VALUES (1, 3)"
                )
            )

            _run_migration(connection, MIGRATION_PATH)

            inspector = sa.inspect(connection)
            columns = {
                column["name"]
                for column in inspector.get_columns("analysis_skill_gaps")
            }
            assert {"evidence", "has_evidence"} <= columns
            assert "ck_analysis_skill_gap_evidence" in {
                constraint["name"]
                for constraint in inspector.get_check_constraints(
                    "analysis_skill_gaps"
                )
            }
            assert connection.execute(
                sa.text(
                    "SELECT current_level, has_evidence "
                    "FROM analysis_skill_gaps WHERE id = 1"
                )
            ).one() == (0, 0)
    finally:
        engine.dispose()


def test_evidence_migration_is_safe_when_fields_already_exist():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    "CREATE TABLE analysis_skill_gaps ("
                    "id INTEGER PRIMARY KEY, "
                    "current_level INTEGER NOT NULL, "
                    "evidence TEXT, "
                    "has_evidence BOOLEAN NOT NULL DEFAULT 0, "
                    "CONSTRAINT ck_analysis_skill_gap_evidence CHECK ("
                    "(has_evidence = 1 AND evidence IS NOT NULL "
                    "AND length(trim(evidence)) > 0) "
                    "OR (has_evidence = 0 AND current_level = 0))"
                    ")"
                )
            )

            _run_migration(connection, MIGRATION_PATH)

            inspector = sa.inspect(connection)
            assert {
                column["name"]
                for column in inspector.get_columns("analysis_skill_gaps")
            } >= {"evidence", "has_evidence"}
            assert len(
                [
                    constraint
                    for constraint in inspector.get_check_constraints(
                        "analysis_skill_gaps"
                    )
                    if constraint["name"] == "ck_analysis_skill_gap_evidence"
                ]
            ) == 1
    finally:
        engine.dispose()


def test_alembic_history_has_one_head_and_recognizes_legacy_revision():
    config = Config(str(ROOT / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)

    assert scripts.get_heads() == ["a9b8c7d6e5f4"]
    assert scripts.get_revision("a6d3f0c2b841") is not None


def test_learning_plan_and_resource_migrations_create_required_schema():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.begin() as connection:
            metadata = sa.MetaData()
            sa.Table(
                "users",
                metadata,
                sa.Column("id", sa.Integer(), primary_key=True),
            )
            sa.Table(
                "analyses",
                metadata,
                sa.Column("id", sa.Integer(), primary_key=True),
            )
            sa.Table(
                "skills",
                metadata,
                sa.Column("id", sa.Integer(), primary_key=True),
            )
            resources = sa.Table(
                "learning_resources",
                metadata,
                sa.Column("id", sa.Integer(), primary_key=True),
                sa.Column("resource_type", sa.String(30), nullable=False),
                sa.Column("is_active", sa.Boolean(), nullable=False),
                sa.Column("skill_id", sa.Integer()),
                sa.Column("slug", sa.String(100), nullable=False),
                sa.CheckConstraint(
                    "resource_type IN ('documentation', 'course', 'video', "
                    "'article', 'practice')",
                    name="ck_learning_resource_type",
                ),
            )
            metadata.create_all(connection)
            connection.execute(
                resources.insert().values(
                    id=1,
                    resource_type="course",
                    is_active=True,
                    skill_id=None,
                    slug="python-tutorial",
                )
            )

            _run_migration(
                connection,
                VERSIONS_PATH / "f6a7b8c9d0e1_create_learning_plans_tables.py",
            )
            _run_migration(
                connection,
                VERSIONS_PATH
                / "91d2e7a4c6b8_approve_curated_learning_resources.py",
            )

            inspector = sa.inspect(connection)
            assert {"learning_plans", "learning_plan_items"} <= set(
                inspector.get_table_names()
            )
            assert {
                "ix_learning_plans_user_status",
                "ix_learning_plans_analysis",
            } <= {
                index["name"] for index in inspector.get_indexes("learning_plans")
            }
            assert "ix_learning_plan_items_plan_week" in {
                index["name"]
                for index in inspector.get_indexes("learning_plan_items")
            }
            assert "approval_status" in {
                column["name"]
                for column in inspector.get_columns("learning_resources")
            }
            assert "ix_learning_resources_approval_active_skill" in {
                index["name"]
                for index in inspector.get_indexes("learning_resources")
            }
            assert connection.execute(
                sa.text(
                    "SELECT approval_status FROM learning_resources WHERE id = 1"
                )
            ).scalar_one() == "approved"
    finally:
        engine.dispose()
