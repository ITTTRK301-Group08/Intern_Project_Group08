"""Tiện ích dùng chung cho sao lưu / khôi phục MySQL.

Mục tiêu: không truyền mật khẩu trên command line, tự tìm mysqldump/mysql
trên cả Windows lẫn Linux/macOS, và tái dùng cấu hình DATABASE_URL của app.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Console Windows mặc định cp1252 không in được tiếng Việt.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from sqlalchemy.engine import URL, make_url  # noqa: E402

from app.core.config import get_settings  # noqa: E402


@dataclass(frozen=True)
class DatabaseInfo:
    url: URL
    host: str
    port: int
    user: str
    password: str
    database: str


def get_database_info(database_url: str | None = None) -> DatabaseInfo:
    """Đọc DATABASE_URL từ tham số, env hoặc .env của dự án."""
    raw = database_url or os.environ.get("DATABASE_URL") or get_settings().database_url
    url = make_url(raw)
    if url.get_backend_name() != "mysql":
        raise ValueError(
            f"Chỉ hỗ trợ sao lưu MySQL, nhận được backend {url.get_backend_name()!r}"
        )
    if not url.database:
        raise ValueError("DATABASE_URL không chứa tên cơ sở dữ liệu")
    return DatabaseInfo(
        url=url,
        host=url.host or "localhost",
        port=int(url.port or 3306),
        user=url.username or "",
        password=url.password or "",
        database=url.database,
    )


def _client_filename(name: str) -> str:
    return name + ".exe" if os.name == "nt" else name


def find_mysql_client(name: str, explicit: str | None = None) -> str:
    """Tìm mysqldump/mysql: tham số > env > PATH > đường dẫn cài đặt thường gặp."""
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise FileNotFoundError(f"Không tìm thấy client tại {path}")
        return str(path)

    filename = _client_filename(name)
    env_dir = os.environ.get("MYSQL_CLIENT_DIR")
    candidates: list[Path] = []
    if env_dir:
        candidates.append(Path(env_dir) / filename)

    located = shutil.which(filename) or shutil.which(name)
    if located:
        return located

    if os.name == "nt":
        program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        for version in ("9.4", "9.3", "9.2", "9.1", "9.0", "8.4", "8.3", "8.2", "8.1", "8.0"):
            candidates.append(program_files / "MySQL" / f"MySQL Server {version}" / "bin" / filename)
        candidates.append(program_files / "MySQL" / "MySQL Workbench 8.0" / "bin" / filename)
    else:
        candidates.extend([Path("/usr/bin") / filename, Path("/usr/local/bin") / filename])

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    raise FileNotFoundError(
        f"Không tìm thấy {filename}. Truyền đường dẫn qua --{name} "
        f"hoặc đặt MYSQL_CLIENT_DIR."
    )


def _option_value(value: str) -> str:
    """Escape giá trị trong file option của MySQL (\\ và \" )."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


@contextmanager
def mysql_defaults_file(info: DatabaseInfo, database: str | None = None) -> Iterator[Path]:
    """Tạo file option tạm để client MySQL đọc credential, không lộ password."""
    lines = [
        "[client]",
        f"host={_option_value(info.host)}",
        f"port={_option_value(str(info.port))}",
        f"user={_option_value(info.user)}",
        f"password={_option_value(info.password)}",
        "default-character-set=utf8mb4",
    ]
    if database:
        lines.append(f"database={_option_value(database)}")

    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".cnf", delete=False
    ) as handle:
        handle.write("\n".join(lines) + "\n")
        path = Path(handle.name)

    if os.name != "nt":
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)


def run_command(
    command: list[str],
    *,
    stdin_file=None,
    stdout_file=None,
) -> str | None:
    """Chạy client MySQL và đưa stderr về dạng dễ đọc."""
    try:
        completed = subprocess.run(
            command,
            stdin=stdin_file,
            stdout=stdout_file or subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        message = (exc.stderr or "").strip() or str(exc)
        raise RuntimeError(f"Lệnh thất bại: {Path(command[0]).name}\n{message}") from exc

    if completed.stderr and completed.stderr.strip():
        print(completed.stderr.strip(), file=sys.stderr)
    return None if stdout_file is not None else completed.stdout


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_revision() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=True,
        )
        return result.stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None
