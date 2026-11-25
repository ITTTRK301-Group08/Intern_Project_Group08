# DEPLOYMENT & RUNBOOK — Career Mentor (Intern_Project_Group08)

Tài liệu này là phần **task cuối**: đóng gói FastAPI + MySQL, chạy thử bắt buộc
qua **HTTPS**, thiết lập **sao lưu** và **hướng dẫn khôi phục dữ liệu**.

---

## 1. Kiến trúc triển khai

```
Trình duyệt / client
        │  HTTPS (TLS 1.2/1.3)
        ▼
   nginx :443  ── redirect 80 → 443
        │  HTTP nội bộ
        ▼
FastAPI (uvicorn) :8000  ── SQLAlchemy/PyMySQL ──▶ MySQL 8 :3306
        │                                             │
        └── uploads/cvs (file CV)                     └── db_data volume
```

- **Staging**: chứng chỉ tự ký (self-signed) do `scripts/generate_self_signed_cert.py`
  tạo ra; trình duyệt sẽ cảnh báo lần đầu — đây là hành vi mong đợi.
- **Production**: thay `deploy/certs` bằng chứng chỉ CA thật (Let's Encrypt...).
- Dữ liệu gồm **2 phần bắt buộc**: bảng trong MySQL **và** file CV trong
  `uploads/cvs`. Backup/restore phải xử lý cả hai.

---

## 2. Chuẩn bị cấu hình

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Trong `.env` (không commit):

```dotenv
ENVIRONMENT=staging
SECRET_KEY=<python -c "import secrets; print(secrets.token_urlsafe(32))">
MYSQL_DATABASE=ai_career_mentor
MYSQL_ROOT_PASSWORD=<mật khẩu mạnh>
# URL cho app chạy trên máy host (không Docker):
DATABASE_URL=mysql+pymysql://root:<password>@localhost:3306/ai_career_mentor?charset=utf8mb4
# URL cho app chạy TRONG container (host là "db"):
DATABASE_URL_CONTAINER=mysql+pymysql://root:<password>@db:3306/ai_career_mentor?charset=utf8mb4
CORS_ALLOWED_ORIGINS=[]
```

> Nếu mật khẩu có ký tự đặc biệt (`@ : / #`), phải **percent-encode** trong URL
> (ví dụ `@` → `%40`). `SECRET_KEY` tối thiểu 32 bytes và không được để giá trị mẫu.

---

## 3. Đóng gói & chạy staging bằng Docker Compose (khuyến nghị)

### 3.1 Tạo chứng chỉ HTTPS

```powershell
python scripts/generate_self_signed_cert.py `
  --out-dir deploy/certs `
  --domains localhost 127.0.0.1 staging.local `
  --days 365
```

Kết quả: `deploy/certs/fullchain.pem` và `deploy/certs/privkey.pem`.
Thư mục `deploy/certs/` đã nằm trong `.gitignore`.

### 3.2 Build & khởi chạy

```powershell
docker compose build
docker compose up -d
docker compose ps
docker compose logs -f api
```

Compose dựng 3 service: `db` (MySQL 8, volume `db_data`), `api` (ảnh từ
`Dockerfile`, tự chạy `alembic upgrade head` qua `docker-entrypoint.sh`),
`nginx` (TLS, expose `80`/`443`). File CV nằm trong volume `uploads_data`.

### 3.3 Tạo tài khoản Admin

```powershell
docker compose exec api python -m app.bootstrap_admin
```

Lệnh hỏi email và mật khẩu (không echo); chạy lại được cho Admin đã tồn tại.

### 3.4 Truy cập

| Đường dẫn | Kết quả mong đợi |
| --- | --- |
| `https://localhost/health` | `{"ok":true}` |
| `https://localhost/` | giao diện Explore |
| `https://localhost/docs` | Swagger UI |
| `http://localhost/health` | `301` → `https://...` |

Dừng dịch vụ: `docker compose stop` (giữ dữ liệu).
**Cẩn thận:** `docker compose down -v` sẽ xoá volume MySQL và CV.

---

## 4. Chạy thử HTTPS không dùng Docker (máy hiện tại)

Khi máy không có Docker, uvicorn có thể tự terminating TLS — vẫn đáp ứng yêu
cầu chạy thử HTTPS.

```powershell
# 1) Đảm bảo schema mới nhất
python -m alembic upgrade head

# 2) Chạy HTTPS (tạo cert tự động nếu chưa có)
python scripts/serve_https.py --port 8443 --domains localhost 127.0.0.1
```

Mở `https://localhost:8443/health` → chọn **Advanced → Proceed** do cert tự ký.

Kiểm tra nhanh bằng PowerShell:

```powershell
Invoke-WebRequest https://localhost:8443/health -SkipCertificateCheck |
  Select-Object StatusCode, Content
```

Kiểm tra đầy đủ hơn bằng Python:

```powershell
python -c "import httpx; c=httpx.Client(verify=False); [print(u, c.get('https://localhost:8443'+u).status_code) for u in ['/health','/','/docs','/api/v1/catalog/categories']]"
```

---

## 5. Kiểm tra "app chạy mượt, không lỗi phát sinh"

| Kiểm tra | Lệnh | Kết quả kỳ vọng |
| --- | --- | --- |
| Unit + E2E | `python -m pytest -q` | `321 passed` (sau khi merge nhánh service-unit-and-e2e-tests) |
| Migration | `python -m alembic current` | đúng head `f7a8b9c0d1e2` |
| Health | `GET /health` qua HTTPS | `200`, `{"ok":true}` |
| Tài liệu API | `GET /docs` qua HTTPS | `200` |
| Catalog | `GET /api/v1/catalog/categories` | `200`, `success=true` |
| Auth | `POST /api/v1/auth/register`, `/login`, `/refresh`, `GET /me`, `/logout` | `201/200`, có token |
| Log | `docker compose logs api` / terminal uvicorn | không có `ERROR`, `TRACEBACK` |

Ví dụ smoke test auth qua HTTPS (dùng user thử nghiệm):

```powershell
python -c "import httpx; b='https://localhost:8443'; c=httpx.Client(verify=False); r=c.post(b+'/api/v1/auth/login',json={'email':'student@example.com','password':'...'}); print(r.status_code); t=r.json()['data']['access_token']; print(c.get(b+'/api/v1/auth/me',headers={'Authorization':'Bearer '+t}).status_code)"
```

> Lỗi AI `404 model not found` thường do `GEMINI_MODEL` sai; dùng
> `gemini-2.5-flash`. Không gọi Gemini thật khi chạy unit test (đã mock).

---

## 6. Quy trình sao lưu

### 6.1 Chạy sao lưu

```powershell
python scripts/db_backup.py --retention 14
```

Script tự đọc `DATABASE_URL` từ `.env`, tự tìm `mysqldump` (PATH, biến
`MYSQL_CLIENT_DIR`, hoặc đường dẫn cài đặt MySQL thường gặp trên Windows).

Mỗi lần chạy tạo `backups/YYYYMMDD_HHMMSS/`:

| File | Nội dung |
| --- | --- |
| `database.sql.gz` | Toàn bộ schema + dữ liệu MySQL (`utf8mb4`, `--single-transaction`, routines/triggers/events). Không chứa `CREATE DATABASE` để restore sang DB khác được. |
| `uploads.tar.gz` | Toàn bộ `uploads/cvs/*.pdf`. |
| `manifest.json` | Thời gian, user/host DB, số bảng, phiên bản Alembic, git revision, **SHA-256 từng file**. |

Sau khi dump, script tự kiểm tra file không rỗng, có `CREATE TABLE` và
`Dump completed`, rồi xoá các bản cũ theo `--retention` (mặc định 7, `0` = giữ hết).

Chỉ định client/thư mục khác:

```powershell
python scripts/db_backup.py --mysqldump "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe"
python scripts/db_backup.py --output-root D:\backups --skip-uploads
```

### 6.2 Lên lịch tự động

**Windows Task Scheduler** — tạo Basic Task, action `Start a program`:

- Program: `powershell`
- Arguments:

```powershell
-NoProfile -Command "Set-Location 'C:\Users\Cong anh\Intern_Project_Group08'; .\.venv\Scripts\python.exe scripts\db_backup.py --retention 14"
```

**Linux/macOS cron** (chạy 02:00 mỗi ngày):

```cron
0 2 * * * cd /opt/career-mentor && ./.venv/bin/python scripts/db_backup.py --retention 14 >> backups/backup.log 2>&1
```

### 6.3 Chép bản sao ra nơi khác (khuyến nghị)

```powershell
robocopy "C:\Users\Cong anh\Intern_Project_Group08\backups" "D:\backup_offsite\career-mentor" /E
# Linux: rsync -avz backups/ user@backup-host:/backups/career-mentor/
```

Lưu ý: bản dump chứa dữ liệu cá nhân (email, CV). Nên lưu ở ổ/network drive
được mã hoá và giới hạn quyền truy cập.

---

## 7. Hướng dẫn khôi phục dữ liệu

### 7.1 Nguyên tắc

1. **Dừng ứng dụng** trước khi restore để tránh ghi thêm vào DB.
2. **Sao lưu trạng thái hiện tại** trước khi restore (`db_backup.py`), phòng khi
   bản sao lưu chọn sai.
3. **Thử restore sang DB riêng** trước, kiểm tra xong mới restore vào DB chính.
4. Script yêu cầu `--yes` khi tạo/xoá DB đích; mặc định **từ chối** ghi vào DB
   đã có bảng nếu không có `--drop-target`.

### 7.2 Kiểm tra bản sao lưu trên DB riêng (khuyến nghị)

```powershell
python scripts/db_restore.py `
  --backup-dir backups\20261125_090000 `
  --target-db ai_career_mentor_restore_test `
  --drop-target --yes
```

Script sẽ: verify SHA-256 → tạo DB đích (utf8mb4) → nạp SQL → đối chiếu số bảng
và `alembic_version` → giải nén CV vào `uploads/cvs`. Sau khi kiểm tra, xoá DB
riêng:

```powershell
python -c "from sqlalchemy import create_engine,text; e=create_engine('mysql+pymysql://root:<password>@localhost:3306'); c=e.connect(); c.execute(text('DROP DATABASE ai_career_mentor_restore_test')); c.close()"
```

### 7.3 Khôi phục DB chính (chạy local / host MySQL)

```powershell
# Dừng uvicorn hoặc: docker compose stop api nginx
python scripts/db_backup.py --retention 0   # backup "hiện trạng" trước khi restore

python scripts/db_restore.py `
  --backup-dir backups\20261125_090000 `
  --drop-target --yes
```

Chỉ bỏ `--drop-target` nếu DB đích đang rỗng (script sẽ tự tạo).
Dùng `--skip-uploads` nếu chỉ muốn khôi phục DB.

### 7.4 Khôi phục khi dùng Docker Compose

Volume DB của compose không publish ra host, nên chạy restore **bên trong container**:

```powershell
docker compose stop api nginx

# SQL
docker compose cp backups\20261125_090000\database.sql.gz db:/tmp/database.sql.gz
docker compose exec db sh -c 'gunzip -c /tmp/database.sql.gz | mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"'

# File CV
docker compose cp backups\20261125_090000\uploads.tar.gz api:/tmp/uploads.tar.gz
docker compose exec api sh -c 'cd /app && tar xzf /tmp/uploads.tar.gz'

docker compose start api nginx
docker compose exec api python -m alembic current
```

> Nếu `gunzip` không có trong image `mysql:8.0`, chạy
> `docker compose exec db sh -c 'apt-get update && apt-get install -y gzip'`
> hoặc giải nén trên host rồi `docker compose cp database.sql db:/tmp/...`.

### 7.5 Sau khi khôi phục

```powershell
python -m alembic current
python -m pytest -q
# HTTPS smoke test như mục 5
```

Nếu `alembic_version` của bản restore cũ hơn head, chạy
`python -m alembic upgrade head` (local) hoặc
`docker compose exec api python -m alembic upgrade head`.

### 7.6 Kịch bản thường gặp

| Tình huống | Việc cần làm |
| --- | --- |
| Deploy lỗi, muốn rollback code | `git checkout <commit cũ>` → build lại image → restart; **không cần restore DB** nếu schema không đổi. |
| Ghi nhầm dữ liệu / xoá nhầm user | Restore bản gần nhất theo mục 7.2 → 7.3. |
| MySQL corruption / mất volume | Tạo volume mới (`docker compose down -v` — **mất hết** nếu chưa có backup) → `up -d` → restore mục 7.4. |
| Chỉ mất file CV | Tải `uploads.tar.gz` giải nén đè vào `uploads/` (hoặc lệnh 7.4 phần CV). |

---

## 8. Khắc phục sự cố nhanh

| Triệu chứng | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| Trình duyệt chữ "Not secure" | Cert tự ký staging | Cài `fullchain.pem` vào Trusted Root (theo domain trong SAN) hoặc dùng CA thật. |
| `502/503` từ nginx | `api` chưa healthy | `docker compose logs api`; kiểm tra migration và `DATABASE_URL_CONTAINER`. |
| `mysqldump: command not found` | Client không có trong PATH | `--mysqldump <đường dẫn>` hoặc đặt `MYSQL_CLIENT_DIR`. |
| `Access denied for user` | Sai mật khẩu/option file | Kiểm tra `password` trong option file tạm; script không ghi password ra command line. |
| `Table already exists` khi restore | DB đích còn dữ liệu | Thêm `--drop-target --yes` (xóa DB đích trước khi nạp). |
| CORS lỗi trên frontend khác origin | `CORS_ALLOWED_ORIGINS=[]` | Đặt JSON list exact origin, ví dụ `["https://staging.example.com"]`. |
| AI trả lỗi model | `GEMINI_MODEL` sai | Đặt `gemini-2.5-flash`; kiểm tra `GEMINI_API_KEY`. |

---

## 9. Checklist nghiệm thu task cuối

- [x] Dockerfile + docker-compose.yml đóng gói FastAPI, MySQL 8, nginx.
- [x] Chạy thử bắt buộc qua HTTPS (nginx :443 hoặc uvicorn TLS :8443).
- [x] HTTP tự redirect sang HTTPS; TLS 1.2/1.3; header bảo mật cơ bản.
- [x] Migration tự động lúc khởi động; bootstrap Admin có hướng dẫn.
- [x] Sao lưu MySQL **+ file CV**, có SHA-256, retention, tự kiểm tra dump.
- [x] Khôi phục có xác nhận, kiểm tra checksum, thử trên DB riêng, checklist sau restore.
- [x] `python -m pytest -q` → 321 passed sau khi pull `feature/service-unit-and-e2e-tests`; README sạch lỗi merge conflict/stale docs.

---

## 10. Bảo mật

- Không commit `.env`, `deploy/certs/`, `backups/`, `*.pem`, `*.key` (đã có trong `.gitignore`).
- `privkey.pem` chmod `600` trên Linux/macOS.
- Xoay `SECRET_KEY` và `MYSQL_ROOT_PASSWORD` khi kết thúc chạy thử.
- Header HSTS trong file nginx chỉ nên dùng với chứng chỉ thật; với self-signed,
  trình duyệt vẫn yêu cầu xác nhận thủ công.
