"""Khôi phục MySQL + uploads/cvs từ một bản sao lưu của db_backup.py.

Ví dụ khôi phục sang DB riêng để kiểm tra trước khi thay chính:
    python scripts/db_restore.py --backup-dir backups/20261125_090000 \
        --target-db ai_career_mentor_restore_test --drop-target --yes

Sau khi kiểm tra xong mới khôi phục vào DB chính:
    python scripts/db_restore.py --backup-dir backups/20261125_090000 \
        --drop-target --yes
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.db_common import (  # noqa: E402
    find_mysql_client,
    get_database_info,
    mysql_defaults_file,
    run_command,
    sha256_file,
)

DEFAULT_UPLOADS = ROOT / "uploads"
SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9_]+$")


def load_manifest(backup_dir: Path) -> dict:
    manifest_path = backup_dir / "manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"Không tìm thấy manifest.json trong {backup_dir}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def verify_backup(backup_dir: Path, manifest: dict) -> None:
    files = manifest.get("files") or {}
    if "database.sql.gz" not in files:
        raise RuntimeError("Backup thiếu database.sql.gz")
    for name, metadata in files.items():
        path = backup_dir / name
        if not path.is_file():
            raise RuntimeError(f"Backup thiếu file {name}")
        actual = sha256_file(path)
        if actual != metadata.get("sha256"):
            raise RuntimeError(f"Checksum không khớp cho {name}: {actual}")
        print(f"  OK {name} (sha256 {actual[:12]}...)")


def prepare_database(info, target: str, drop: bool, yes: bool) -> None:
    if not SAFE_IDENTIFIER.fullmatch(target):
        raise RuntimeError(f"Tên database không hợp lệ: {target!r}")
    engine = create_engine(info.url)
    try:
        with engine.begin() as connection:
            exists = connection.execute(
                text("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = :db"),
                {"db": target},
            ).scalar()
            table_count = 0
            if exists:
                table_count = connection.execute(
                    text(
                        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES "
                        "WHERE TABLE_SCHEMA = :db AND TABLE_TYPE = 'BASE TABLE'"
                    ),
                    {"db": target},
                ).scalar_one()

            if exists and table_count and not drop:
                raise RuntimeError(
                    f"Database {target} đang có {table_count} bảng. "
                    "Dùng --drop-target để thay thế hoàn toàn (sẽ mất dữ liệu cũ)."
                )
            if (drop or not exists) and not yes:
                raise RuntimeError("Cần truyền --yes để xác nhận ghi đè/tạo database")

            if drop:
                connection.execute(text(f"DROP DATABASE IF EXISTS `{target}`"))
            if drop or not exists:
                connection.execute(
                    text(
                        f"CREATE DATABASE `{target}` "
                        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                    )
                )
                print(f"  Đã tạo database {target} (utf8mb4)")
    finally:
        engine.dispose()


def restore_database(info, backup_dir: Path, target: str, mysql: str) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        sql_path = Path(temporary) / "dump.sql"
        with gzip.open(backup_dir / "database.sql.gz", "rb") as source:
            with sql_path.open("wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
        with mysql_defaults_file(info, database=target) as defaults:
            command = [
                mysql,
                f"--defaults-extra-file={defaults}",
                "--default-character-set=utf8mb4",
                target,
            ]
            with sql_path.open("r", encoding="utf-8") as source:
                run_command(command, stdin_file=source)


def verify_database(info, target: str, manifest: dict) -> None:
    url = info.url.set(database=target)
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            tables = [
                row[0]
                for row in connection.execute(
                    text(
                        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                        "WHERE TABLE_SCHEMA = :db AND TABLE_TYPE = 'BASE TABLE'"
                    ),
                    {"db": target},
                )
            ]
            expected = int(manifest.get("stats", {}).get("table_count") or 0)
            if expected and len(tables) < expected:
                raise RuntimeError(
                    f"Khôi phục chưa đủ bảng: có {len(tables)}, kỳ vọng {expected}"
                )
            version = None
            if "alembic_version" in tables:
                version = connection.execute(
                    text("SELECT version_num FROM alembic_version LIMIT 1")
                ).scalar()
            expected_version = manifest.get("stats", {}).get("alembic_version")
            if expected_version and version != expected_version:
                print(
                    f"  CẢNH BÁO: alembic_version={version}, backup={expected_version}",
                    file=sys.stderr,
                )
            print(
                f"  OK database {target}: {len(tables)} bảng, alembic_version={version}"
            )
    finally:
        engine.dispose()


def restore_uploads(backup_dir: Path, uploads_root: Path) -> None:
    archive_path = backup_dir / "uploads.tar.gz"
    if not archive_path.is_file():
        return
    uploads_root.mkdir(parents=True, exist_ok=True)
    restored = 0
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            name = member.name.replace("\\", "/")
            parts = name.split("/")
            if name.startswith("/") or ".." in parts or not (
                name == "cvs" or name.startswith("cvs/")
            ):
                raise RuntimeError(f"Đường dẫn không an toàn trong archive: {name!r}")
            if not member.isfile():
                continue
            target = uploads_root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is not None:
                target.write_bytes(source.read())
                restored += 1
    print(f"  OK uploads/cvs: khôi phục {restored} file")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument("--target-db", help="Mặc dùng tên DB trong manifest")
    parser.add_argument("--drop-target", action="store_true", help="Xoá DB đích trước khi restore")
    parser.add_argument("--yes", action="store_true", help="Xác nhận ghi đè dữ liệu")
    parser.add_argument("--mysql", help="Đường dẫn tới mysql client")
    parser.add_argument("--uploads-root", type=Path, default=DEFAULT_UPLOADS)
    parser.add_argument("--skip-uploads", action="store_true")
    args = parser.parse_args()

    backup_dir = args.backup_dir.resolve()
    if not backup_dir.is_dir():
        raise RuntimeError(f"Không tìm thấy thư mục backup {backup_dir}")

    manifest = load_manifest(backup_dir)
    target = args.target_db or manifest.get("database")
    if not target:
        raise RuntimeError("Manifest không có tên database; hãy truyền --target-db")

    info = get_database_info()
    if target != info.database:
        print(f"LƯU Ý: đang khôi phục sang {target!r} (DB chính là {info.database!r})")

    print("Kiểm tra checksum bản sao lưu ...")
    verify_backup(backup_dir, manifest)

    print("Chuẩn bị database đích ...")
    prepare_database(info, target, args.drop_target, args.yes)

    print("Đang khôi phục dữ liệu SQL ...")
    mysql = find_mysql_client("mysql", args.mysql)
    restore_database(info, backup_dir, target, mysql)
    verify_database(info, target, manifest)

    if not args.skip_uploads:
        print("Đang khôi phục file CV ...")
        restore_uploads(backup_dir, args.uploads_root)

    print(f"HOÀN TẤT: {backup_dir} -> {target}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, FileNotFoundError, ValueError, json.JSONDecodeError) as error:
        print(f"LỖI: {error}", file=sys.stderr)
        raise SystemExit(1) from error
