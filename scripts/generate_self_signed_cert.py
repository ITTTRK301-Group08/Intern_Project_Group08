"""Tạo chứng chỉ tự ký cho môi trường chạy thử HTTPS.

Không cần openssl: dùng thư viện cryptography đã có trong requirements.txt.
Chứng chỉ chỉ dành cho staging/demo; production phải dùng CA tin cậy (Let's Encrypt).
"""

from __future__ import annotations

import argparse
import ipaddress
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CERT_DIR = ROOT / "deploy" / "certs"
DEFAULT_DOMAINS = ("localhost", "127.0.0.1")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _alternative_names(domains: list[str]) -> x509.SubjectAlternativeName:
    names: list[x509.GeneralName] = []
    for value in domains:
        try:
            names.append(x509.IPAddress(ipaddress.ip_address(value)))
        except ValueError:
            names.append(x509.DNSName(value))
    if not names:
        names.append(x509.DNSName("localhost"))
    return x509.SubjectAlternativeName(names)


def generate_cert(
    out_dir: Path,
    domains: list[str],
    days: int = 365,
    *,
    force: bool = False,
) -> tuple[Path, Path]:
    """Tạo fullchain.pem và privkey.pem; trả về (cert_path, key_path)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cert_path = out_dir / "fullchain.pem"
    key_path = out_dir / "privkey.pem"

    if cert_path.is_file() and key_path.is_file() and not force:
        raise FileExistsError(
            f"Chứng chỉ đã tồn tại trong {out_dir}. Dùng --force nếu muốn tạo lại."
        )

    if not domains:
        domains = list(DEFAULT_DOMAINS)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, domains[0])]
    )
    now = datetime.now(timezone.utc)

    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=days))
        .add_extension(_alternative_names(domains), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False
        )
        .sign(key, hashes.SHA256())
    )

    cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    if hasattr(key_path, "chmod"):
        try:
            key_path.chmod(0o600)
        except OSError:
            pass  # Windows không hỗ trợ đầy đủ mode POSIX
    return cert_path, key_path


def ensure_cert(
    out_dir: Path,
    domains: list[str] | None = None,
    days: int = 365,
) -> tuple[Path, Path]:
    """Dùng lại chứng chỉ nếu hợp lệ, ngược lại tạo mới."""
    out_dir = Path(out_dir)
    cert_path = out_dir / "fullchain.pem"
    key_path = out_dir / "privkey.pem"
    if cert_path.is_file() and key_path.is_file():
        return cert_path, key_path
    return generate_cert(out_dir, list(domains or DEFAULT_DOMAINS), days, force=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir", type=Path, default=DEFAULT_CERT_DIR, help="Thư mục chứa chứng chỉ"
    )
    parser.add_argument(
        "--domains",
        nargs="+",
        default=list(DEFAULT_DOMAINS),
        help="Tên miền/IP đưa vào SAN (ví dụ localhost 127.0.0.1 staging.local)",
    )
    parser.add_argument("--days", type=int, default=365, help="Số ngày hiệu lực")
    parser.add_argument("--force", action="store_true", help="Ghi đè chứng chỉ cũ")
    args = parser.parse_args()

    cert_path, key_path = generate_cert(
        args.out_dir, args.domains, args.days, force=args.force
    )
    print(f"Đã tạo chứng chỉ tự ký:\n  cert: {cert_path}\n  key:  {key_path}")
    print(f"SAN: {', '.join(args.domains)} | hiệu lực {args.days} ngày")
    print(
        "Lưu ý: trình duyệt sẽ cảnh báo 'Not secure'. Hãy cài cert vào trusted root "
        "cho máy thử nghiệm, hoặc dùng CA thật ở production."
    )


if __name__ == "__main__":
    try:
        main()
    except FileExistsError as error:
        print(f"LỖI: {error}", file=sys.stderr)
        raise SystemExit(1) from error
