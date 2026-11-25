"""Sao lưu MySQL + thư mục uploads/cvs cho Career Mentor.

Ví dụ:
    python scripts/db_backup.py
    python scripts/db_backup.py --retention 14 --output-root D:\backups

Mỗi lần chạy tạo một thư mục backups/YYYYMMDD_HHMMSS gồm:
    database.sql.gz   - dump schema + dữ liệu (không gồm CREATE DATABASE)
    uploads.tar.gz    - toàn bộ file CV đã upload
    manifest.json     - timestamp, checksum SHA-256, số bảng, revision git
"""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import sys
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.db_common import (  # noqa: E402
    find_mysql_client,
    get_database_info,
    git_revision,
    mysql_defaults_file,
    run_command,
    sha256_file,
)

DEFAULT_OUTPUT = ROOT / "backups"
DEFAULT_UPLOADS = ROOT / "uploads"


def collect_stats(info) -> dict[str, object]:
    """Lấy số bảng và phiên bản Alembic để đối chiếu khi khôi phục."""
    engine = create_engine(info.url)
    try:
        with engine.connect() as connection:
            tables = [
                row[0]
                for row in connection.execute(
                    text(
                        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                        "WHERE TABLE_SCHEMA = :db AND TABLE_TYPE = 'BASE TABLE' "
                        "ORDER BY TABLE_NAME"
                    ),
                    {"db": info.database},
                )
            ]
            alembic_version = None
            if "alembic_version" in tables:
                alembic_version = connection.execute(
                    text("SELECT version_num FROM alembic_version LIMIT 1")
                ).scalar()
    finally:
        engine.dispose()
    return {
        "table_count": len(tables),
        "tables": tables,
        "alembic_version": alembic_version,
    }


def dump_database(info, mysqldump: str, destination: Path) -> None:
    """Gọi mysqldump, ghi thẳng ra file rồi nén gzip."""
    with tempfile.TemporaryDirectory() as temporary:
        raw_dump = Path(temporary) / "dump.sql"
        options = [
            "--single-transaction",
            "--quick",
            "--routines",
            "--events",
            "--triggers",
            "--hex-blob",
            "--default-character-set=utf8mb4",
            "--set-gtid-purged=OFF",
            "--no-tablespaces",
        ]
        with mysql_defaults_file(info) as defaults:
            command = [
                mysqldump,
                f"--defaults-extra-file={defaults}",
                *options,
                info.database,
            ]
            with raw_dump.open("w", encoding="utf-8") as output:
                run_command(command, stdout_file=output)

        with raw_dump.open("rb") as source, gzip.open(destination, "wb", 6) as target:
            shutil.copyfileobj(source, target, length=1024 * 1024)


def verify_dump(destination: Path) -> None:
    """Đảm bảo dump không rỗng và có cả phần header lẫn footer."""
    with gzip.open(destination, "rb") as handle:
        head = handle.read(64 * 1024)
        handle.seek(0, 2)
        size = handle.tell()
        handle.seek(max(0, size - 64 * 1024))
        tail = handle.read()
    if size == 0:
        raise RuntimeError("File dump rỗng")
    content = (head + tail).decode("utf-8", errors="replace")
    if "CREATE TABLE" not in content or "Dump completed" not in content:
        raise RuntimeError("Dump không hợp lệ: thiếu CREATE TABLE hoặc Dump completed")


def archive_uploads(uploads_root: Path, destination: Path) -> int:
    """Đóng gọi uploads/cvs; trả về số file CV."""
    cvs_root = uploads_root / "cvs"
    count = 0
    with tarfile.open(destination, "w:gz") as archive:
        if cvs_root.is_dir():
            for path in sorted(cvs_root.rglob("*")):
                if path.is_file():
                    archive.add(path, arcname=str(Path("cvs") / path.relative_to(cvs_root)))
                    count += 1
    return count


def prune_old_backups(output_root: Path, keep: int) -> list[Path]:
    """Chỉ xoá các thư mục backup có manifest.json, giữ lại `keep` bản mới nhất."""
    if keep <= 0:
        return []
    candidates = sorted(
        path
        for path in output_root.iterdir()
        if path.is_dir()
        and (path / "manifest.json").is_file()
        and len(path.name) == 15
        and path.name[8] == "_"
    )
    removed = candidates[:-keep]
    for path in removed:
        shutil.rmtree(path)
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--uploads-root", type=Path, default=DEFAULT_UPLOADS)
    parser.add_argument("--retention", type=int, default=7, help="Số bản giữ lại (0 = không xoá)")
    parser.add_argument("--mysqldump", help="Đường dẫn tới mysqldump")
    parser.add_argument("--skip-uploads", action="store_true")
    args = parser.parse_args()

    info = get_database_info()
    mysqldump = find_mysql_client("mysqldump", args.mysqldump)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = args.output_root / timestamp
    destination.mkdir(parents=True, exist_ok=False)

    print(f"Đang sao lưu MySQL {info.host}:{info.port}/{info.database} ...")
    stats = collect_stats(info)
    sql_path = destination / "database.sql.gz"
    dump_database(info, mysqldump, sql_path)
    verify_dump(sql_path)
    print(f"  OK database.sql.gz ({stats['table_count']} bảng, alembic={stats['alembic_version']})")

    files: dict[str, dict[str, object]] = {
        "database.sql.gz": {
            "sha256": sha256_file(sql_path),
            "bytes": sql_path.stat().st_size,
        }
    }

    upload_count = 0
    if not args.skip_uploads:
        uploads_path = destination / "uploads.tar.gz"
        upload_count = archive_uploads(args.uploads_root, uploads_path)
        files["uploads.tar.gz"] = {
            "sha256": sha256_file(uploads_path),
            "bytes": uploads_path.stat().st_size,
        }
        print(f"  OK uploads.tar.gz ({upload_count} file CV)")

    manifest = {
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "database": info.database,
        "host": info.host,
        "port": info.port,
        "user": info.user,
        "git_revision": git_revision(),
        "stats": stats,
        "upload_file_count": upload_count,
        "files": files,
        "restore_command": (
            f"python scripts/db_restore.py --backup-dir {destination} --drop-target --yes"
        ),
    }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    removed = prune_old_backups(args.output_root, args.retention)
    print(f"Hoàn tất bản sao lưu: {destination}")
    if removed:
        print(f"Đã xoá {len(removed)} bản cũ theo retention={args.retention}")
    print("Khôi phục: python scripts/db_restore.py --backup-dir <thư mục này> --drop-target --yes")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, FileNotFoundError, ValueError) as error:
        print(f"LỖI: {error}", file=sys.stderr)
        raise SystemExit(1) from error
