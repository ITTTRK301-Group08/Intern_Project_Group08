#!/bin/sh
set -eu

# Chờ MySQL sẵn sàng trước khi migrate (compose đã có healthcheck, thêm lớp này
# để chạy docker run thủ công vẫn ổn).
python - <<'PY'
import os
import sys
import time

import pymysql

host = os.environ.get("MYSQL_HOST", "db")
port = int(os.environ.get("MYSQL_PORT", "3306"))
user = os.environ.get("MYSQL_USER", "root")
password = os.environ.get("MYSQL_ROOT_PASSWORD", "")

for attempt in range(60):
    try:
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            charset="utf8mb4",
            connect_timeout=3,
        )
        connection.close()
        print(f"MySQL sẵn sàng sau {attempt + 1} lần thử", flush=True)
        break
    except Exception as exc:  # noqa: BLE001 - chỉ log, sau đó thử lại
        if attempt == 59:
            print(f"Không kết nối được MySQL: {exc}", file=sys.stderr, flush=True)
            raise SystemExit(1)
        time.sleep(2)
PY

echo "Áp dụng Alembic migration ..."
python -m alembic upgrade head

exec "$@"
