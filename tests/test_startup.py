import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("secret_key", "should_start"),
    [
        ("too-short", False),
        ("startup-test-secret-that-is-at-least-32-bytes", True),
    ],
)
def test_app_import_uses_dotenv_secret_without_test_override(
    tmp_path: Path, secret_key: str, should_start: bool
):
    (tmp_path / ".env").write_text(
        f"DATABASE_URL=sqlite+pysqlite:///:memory:\nSECRET_KEY={secret_key}\n",
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment.pop("SECRET_KEY", None)
    environment["PYTHONPATH"] = str(ROOT)

    result = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    if should_start:
        assert result.returncode == 0, result.stderr
    else:
        assert result.returncode != 0
        assert "SECRET_KEY" in result.stderr
