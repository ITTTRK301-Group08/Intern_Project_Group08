from io import StringIO
from pathlib import Path
import runpy

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


ROOT = Path(__file__).resolve().parents[1]


def _migration(filename: str):
    return runpy.run_path(str(ROOT / "alembic" / "versions" / filename))


def test_role_constraint_migration_emits_mysql_constraint_ddl():
    migration = _migration("c1e49a7f2b30_constrain_user_roles.py")
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="mysql",
        opts={"as_sql": True, "output_buffer": output},
    )

    with Operations.context(context):
        migration["upgrade"]()

    sql = output.getvalue()
    assert "ck_users_role" in sql
    assert "CHECK (role IN ('student', 'admin'))" in sql


def test_student_profile_target_role_index_migration_upgrade_and_downgrade():
    migration = _migration(
        "9c4e7a1b2d60_add_student_profile_target_role_index.py"
    )
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.begin() as connection:
            sa.Table(
                "student_profiles",
                sa.MetaData(),
                sa.Column("target_role_id", sa.Integer()),
            ).create(connection)

            context = MigrationContext.configure(connection)
            with Operations.context(context):
                migration["upgrade"]()

            indexes = sa.inspect(connection).get_indexes("student_profiles")
            assert {index["name"] for index in indexes} == {
                "ix_student_profiles_target_role_id"
            }

            with Operations.context(context):
                migration["downgrade"]()

            assert sa.inspect(connection).get_indexes("student_profiles") == []
    finally:
        engine.dispose()


def test_refresh_token_migration_upgrade_and_downgrade():
    migration = _migration(
        "a6d3f0c2b841_add_refresh_token_sessions.py"
    )
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.begin() as connection:
            sa.Table(
                "users",
                sa.MetaData(),
                sa.Column("id", sa.Integer(), primary_key=True),
            ).create(connection)

            context = MigrationContext.configure(connection)
            with Operations.context(context):
                migration["upgrade"]()

            inspector = sa.inspect(connection)
            assert {
                column["name"]
                for column in inspector.get_columns("refresh_tokens")
            } == {
                "id",
                "user_id",
                "token_hash",
                "family_id",
                "expires_at",
                "revoked_at",
                "created_at",
            }
            assert {
                index["name"]
                for index in inspector.get_indexes("refresh_tokens")
            } == {"ix_refresh_tokens_user_id", "ix_refresh_tokens_family_id"}

            with Operations.context(context):
                migration["downgrade"]()

            assert "refresh_tokens" not in sa.inspect(connection).get_table_names()
    finally:
        engine.dispose()