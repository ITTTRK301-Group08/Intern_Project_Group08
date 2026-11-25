# Chạy hệ thống để demo MVP

Hướng dẫn dưới đây chạy FastAPI/Uvicorn trên Windows với MySQL 8. Các lệnh chạy trong thư mục gốc repository bằng PowerShell.

## 1. Cài đặt môi trường Python

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Mở `.env` và đặt các giá trị phù hợp:

```dotenv
ENVIRONMENT=development
DATABASE_URL=mysql+pymysql://root:<password-url-encoded>@localhost:3306/ai_career_mentor?charset=utf8mb4
SECRET_KEY=<giá trị ngẫu nhiên tối thiểu 32 bytes>
CORS_ALLOWED_ORIGINS=[]
AI_PROVIDER=gemini
GEMINI_API_KEY=<Gemini API key nếu demo chức năng AI thật>
GEMINI_MODEL=gemini-2.5-flash
```

Tạo secret an toàn (sao chép kết quả vào `.env`, không commit file này):

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Nếu chưa tạo schema database, tạo database MySQL trước:

```powershell
mysql -u root -p -e "CREATE DATABASE ai_career_mentor CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"
```

Nếu password có ký tự đặc biệt trong URL, percent-encode password. `GEMINI_API_KEY` không cần để app khởi động nhưng phải hợp lệ để gọi Gemini thật. Không dùng API key thật ở frontend.

## 2. Migration và dữ liệu mẫu

```powershell
python -m alembic upgrade head
python -m alembic current
python -m alembic heads
```

Revision hiện tại: `f7a8b9c0d1e2`. Migration chain có revision seed catalog/vị trí/kỹ năng/tài nguyên học tập mẫu. Chưa có tài khoản demo mặc định và không nên seed người dùng bằng mật khẩu cố định.

## 3. Tạo Admin và khởi động API/UI

Trong terminal tương tác, tạo Admin lần đầu (nhập email, mật khẩu hai lần; mật khẩu được ẩn):

```powershell
python -m app.bootstrap_admin
```

Khởi động server:

```powershell
python -m uvicorn app.main:app --reload
```

Mở các URL:

- `http://127.0.0.1:8000/` — Explore
- `http://127.0.0.1:8000/register` — tự đăng ký tài khoản Sinh viên
- `http://127.0.0.1:8000/login` — đăng nhập
- `http://127.0.0.1:8000/admin` — giao diện Admin (đăng nhập Admin)
- `http://127.0.0.1:8000/health` — phải trả HTTP 200 và `{"ok":true}`
- `http://127.0.0.1:8000/docs` — Swagger/OpenAPI

Đăng ký user demo qua giao diện, không cần lệnh seed riêng. Dùng trình duyệt profile/ẩn danh khác hoặc logout để luân phiên giữa tài khoản Sinh viên và Admin.

## 4. Trình tự demo nhanh

1. Sinh viên: đăng ký/đăng nhập → cập nhật `/profile` → khám phá catalog → tải PDF ở `/cv`.
2. Phân tích: vào `/analysis`, chọn role và nguồn CV/hồ sơ, chấp thuận AI consent. Chức năng này cần Gemini API key thật để tạo kết quả thật.
3. Học tập: từ report tạo `/roadmap`, cập nhật tiến độ một nhiệm vụ.
4. Phỏng vấn: `/interview`, trả lời đủ ba câu; cần AI để tạo câu hỏi/chấm điểm thật.
5. Dashboard: kiểm tra kết quả tổng hợp ở `/dashboard`.
6. Admin: logout student, login Admin → thống kê/người dùng/danh mục/tài nguyên; duyệt tài nguyên rồi quay lại Explore xác nhận.
7. Kiểm tra phân quyền: student không được gọi API `/api/v1/admin/*` (mong đợi 403); mở khóa lại user demo nếu vừa khóa.

## 5. Kiểm tra tự động và giới hạn xác minh

```powershell
python -m pytest -q
```

Bộ test repository hiện chạy trên SQLite in-memory và mock các lời gọi AI; lần rà soát ngày 2026-11-25 trên commit `473df9a` có **322 passed**. Đây không phải bằng chứng Gemini thật hoặc MySQL staging đã hoạt động.

Nếu máy có Docker và muốn chạy staging HTTPS, theo hướng dẫn tại [`../DEPLOYMENT.md`](../DEPLOYMENT.md). Trong lần rà soát, `alembic current` dừng trước khi kết nối vì `DATABASE_URL` chưa được cấu hình; Docker daemon cũng không khả dụng. Cần người vận hành cấu hình MySQL/`.env`, chạy `upgrade head`, Compose healthcheck và kịch bản demo trên MySQL/staging trước khi ký nghiệm thu.
