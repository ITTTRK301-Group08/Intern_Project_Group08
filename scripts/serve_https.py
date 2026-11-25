"""Chạy FastAPI trực tiếp qua HTTPS (dùng khi máy không có Docker).

Ví dụ:
    python scripts/serve_https.py --port 8443 --domains localhost 127.0.0.1

Chứng chỉ tự ký được tạo tự động trong deploy/certs nếu chưa có.
Với Docker dùng docker-compose.yml + deploy/nginx.conf để nginx terminating TLS.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_self_signed_cert import DEFAULT_CERT_DIR, ensure_cert  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8443)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--cert-dir", type=Path, default=DEFAULT_CERT_DIR)
    parser.add_argument(
        "--domains",
        nargs="+",
        default=["localhost", "127.0.0.1"],
        help="Tên miền/IP trong SAN của chứng chỉ",
    )
    parser.add_argument("--log-level", default="info")
    args = parser.parse_args()

    cert_path, key_path = ensure_cert(args.cert_dir, args.domains, args.days)
    os.environ.setdefault("ENVIRONMENT", "staging")

    scheme = "https://localhost" if args.host == "127.0.0.1" else f"https://{args.host}"
    shown_port = "" if args.port == 443 else f":{args.port}"
    print(f"Staging HTTPS: {scheme}{shown_port}/health")
    print(f"Docs:          {scheme}{shown_port}/docs")
    print(f"Cert:          {cert_path}")
    print("Chứng chỉ tự ký: trình duyệt sẽ hỏi xác nhận ở lần đầu truy cập.")

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        ssl_certfile=str(cert_path),
        ssl_keyfile=str(key_path),
        workers=args.workers,
        proxy_headers=True,
        forwarded_allow_ips="*",
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
