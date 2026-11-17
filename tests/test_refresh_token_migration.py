from io import StringIO
from pathlib import Path
import runpy

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


ROOT = Path(__file__).resolve().parents[1]


def test_refresh_token_migration_upgrade_and_downgrade():
    migration = runpy.run_path(
        str(ROOT / "alembic" / "versions" / "b7e9c2d4f610_add_refresh_token_sessions.py")
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
