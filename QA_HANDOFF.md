# QA handoff: FastAPI, AI, database

## Summary

- Local test suite: `python -m pytest -q` — **178 passed, 1 skipped**.
- The skipped test is the opt-in live Gemini integration test. No Gemini API
  request was sent.
- The configured development database is local MySQL 8.0.45.
- Alembic is at `a6d3f0c2b841` (head). The student-profile target-role index
  and hashed refresh-token session table are present.
- Refresh-token login, rotation, replay handling, logout revocation, and
  automatic browser retry after access-token expiry are implemented.
- No FastAPI or mocked-AI test failures were found.

## Follow-up items

1. **[Done] Bring the development database schema up to the repository head.**
   - Verified `ENVIRONMENT=development`, local host, database
     `ai_career_mentor`, and MySQL 8.0.45 before applying migrations.
   - Applied revisions `9c4e7a1b2d60` and `a6d3f0c2b841` from the existing
     `f7a8b9c0d1e2` revision. Verified the final revision, InnoDB/utf8mb4
     refresh-token table, both required indexes, and that no token rows were
     created by the migration.
   - The `f7...`, `9c...`, and `a6...` migration scripts are present in
     `alembic/versions`.

2. **[P3] Exercise a live Gemini response only when API credentials and quota
   are approved.**
   - Existing unit tests use mocked providers; the live integration test is
     skipped unless `RUN_GEMINI_LIVE_TESTS=1` is set.
   - If approved, configure `GEMINI_API_KEY` and `GEMINI_MODEL` and run:
     `python -m pytest tests/integration/test_gemini_live.py -q`.

## Validation notes

- The migration upgrade was applied only to the verified local development
  database. No production database was touched.
- The incremental `9c4e7a1b2d60:a6d3f0c2b841` MySQL SQL rendered offline.
- Rendering the full historical migration chain offline still stops at the
  pre-existing data migration `8c3f1e7a9b20`, which requires a live connection.
- A disposable SQLite migration attempt stopped at the MySQL-specific
  `ck_users_role` constraint migration because SQLite does not support that
  standalone `ALTER CHECK` operation. The project documents MySQL 8.x as its
  runtime database; this SQLite result does not establish a MySQL migration
  failure.
- The worktree already had unrelated/uncommitted changes before this follow-up.
  Those pre-existing changes were preserved.
- Live Gemini testing remains skipped; no Gemini API request was sent.
