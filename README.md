# Career Mentor — Hệ thống Định hướng Nghề nghiệp & Phân tích Kỹ năng AI

**Career Mentor** là ứng dụng web hỗ trợ sinh viên CNTT khám phá lộ trình nghề nghiệp, tải lên và phân tích CV bằng AI (Google Gemini), đánh giá khoảng cách kỹ năng (Skill Gap), xây dựng lộ trình học tập cá nhân hóa 30 ngày, luyện phỏng vấn thử (Mock Interview) và theo dõi mức độ sẵn sàng nghề nghiệp trên Dashboard.

> **Triển khai staging (Docker + HTTPS), sao lưu và khôi phục dữ liệu:** xem chi tiết tại [`DEPLOYMENT.md`](DEPLOYMENT.md).

---

## 1. Công nghệ & Kiến trúc hệ thống

- **Backend:** FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, PyMuPDF (`fitz`).
- **Cơ sở dữ liệu:** MySQL 8.x (`InnoDB`, `utf8mb4`).
- **Bảo mật & Phiên đăng nhập:** Mật khẩu băm bằng `bcrypt`, xác thực JWT (`HS256`) kết hợp Refresh Token (lưu dưới dạng hash `SHA-256` trong DB, hỗ trợ xoay vòng token và thu hồi phiên phía máy chủ).
- **Dịch vụ AI:** Tích hợp lớp AI dùng chung qua Google Gemini (`google-genai`), ép khuôn đầu ra JSON theo Pydantic Schema, có cơ chế timeout, retry và kiểm soát chấp thuận người dùng (AI Consent).
- **Frontend:** HTML5, CSS3, JavaScript thuần với các giao diện tương tác trực tiếp cùng hệ thống API RESTful.

---

## 2. Cài đặt & Khởi chạy cục bộ

Yêu cầu **Python 3.11+** và **MySQL 8.x** (`utf8mb4`). Các thư viện cần thiết được liệt kê trong `requirements.txt`.

### Bước 1: Tạo môi trường ảo và cài đặt thư viện

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

### Bước 2: Cấu hình biến môi trường (`.env`)

Mở file `.env` (tuyệt đối không commit file này lên Git) và cập nhật các thông số:

1. **Kết nối cơ sở dữ liệu & Bảo mật:**
   - `DATABASE_URL`: chuỗi kết nối MySQL kèm `?charset=utf8mb4` (ví dụ: `mysql+pymysql://root:<password>@localhost:3306/ai_career_mentor?charset=utf8mb4`).
   - `SECRET_KEY`: tạo khóa bí mật ngẫu nhiên bằng lệnh:
     ```powershell
     python -c "import secrets; print(secrets.token_urlsafe(32))"
     ```
   - `ACCESS_TOKEN_EXPIRE_MINUTES`: thời hạn Access Token (mặc định `30` phút).
   - `REFRESH_TOKEN_EXPIRE_DAYS`: thời hạn Refresh Token (mặc định `14` ngày).
   - `CORS_ALLOWED_ORIGINS`: danh sách JSON các origin frontend được phép truy cập (ví dụ `["https://your-frontend.example"]`), không chấp nhận ký tự đại diện `*`.
2. **Cấu hình dịch vụ AI (Google Gemini):**
   ```dotenv
   AI_PROVIDER=gemini
   GEMINI_API_KEY=<API Key lấy tại https://aistudio.google.com/apikey>
   GEMINI_MODEL=gemini-2.5-flash
   AI_TIMEOUT=30
   AI_MAX_RETRIES=2
   ```
   - `AI_PROVIDER`: hiện hỗ trợ `gemini` (giá trị khác sẽ báo `AIConfigurationError`).
   - `GEMINI_API_KEY`: bắt buộc khi gọi AI thật; không bắt buộc khi chỉ khởi động ứng dụng hoặc chạy unit test.
   - `AI_TIMEOUT`: thời gian chờ tối đa cho mỗi request (giây).
   - `AI_MAX_RETRIES`: số lần thử lại tối đa đối với lỗi tạm thời (mạng, 5xx, 429, timeout); lỗi cấu hình hoặc dữ liệu không hợp lệ sẽ không retry.

### Bước 3: Khởi tạo cơ sở dữ liệu, tài khoản Admin và chạy server

Chạy migration để tạo toàn bộ bảng dữ liệu và nạp sẵn danh mục nghề nghiệp, kỹ năng, tài nguyên học tập mẫu; sau đó khởi tạo tài khoản Quản trị viên:

```powershell
python -m alembic upgrade head
python -m app.bootstrap_admin
python -m uvicorn app.main:app --reload
```

> **Lưu ý khi tạo Admin:** Lệnh `python -m app.bootstrap_admin` sẽ yêu cầu nhập email và mật khẩu (8–72 UTF-8 bytes, ẩn khi gõ). Không ghi mật khẩu Admin vào `.env` hay truyền qua tham số dòng lệnh. Lệnh này an toàn khi chạy lặp lại cho tài khoản Admin đã có và từ chối tự động nâng quyền tài khoản học viên.

---

## 3. Xác thực, Phân quyền & Quản lý phiên

- **Đăng ký & Vai trò:** Đăng ký công khai (`/api/v1/auth/register`) luôn tạo tài khoản học viên (`student`). Quyền quản trị (`admin`) được kiểm tra trực tiếp từ cột vai trò trong cơ sở dữ liệu trên mỗi request và chỉ được cấp qua lệnh bootstrap hoặc quản trị viên.
- **Cơ chế Access Token & Refresh Token:**
  - Khi đăng nhập (`POST /api/v1/auth/login`), hệ thống cấp một **Access Token** ngắn hạn và một **Refresh Token** (mặc định 14 ngày, lưu trong DB dưới dạng hash `SHA-256`).
  - `POST /api/v1/auth/refresh`: xoay vòng Refresh Token hợp lệ và cấp Access Token mới; nếu phát hiện tái sử dụng Refresh Token đã xoay vòng, toàn bộ chuỗi phiên (session family) sẽ bị thu hồi ngay lập tức.
  - `POST /api/v1/auth/logout`: thu hồi phiên đăng nhập phía máy chủ, đồng thời xóa token phía trình duyệt.
  - Trên giao diện web, khi gặp mã lỗi `401`, frontend tự động gọi `/api/v1/auth/refresh` một lần trước khi chuyển hướng người dùng về `/login`.
- **Khóa / Mở khóa tài khoản:** Quản trị viên có thể vô hiệu hóa hoặc kích hoạt lại tài khoản người dùng qua phân hệ `/admin`. Tài khoản bị khóa (`is_active = false`) bị chặn đăng nhập và chặn mọi API được bảo vệ (`403 Forbidden`).

---

## 4. Các màn hình giao diện & Nhóm API chính

### Giao diện người dùng (Frontend)
- `/` và `/explore`: Khám phá danh mục nhóm nghề, vị trí nghề nghiệp (Intern/Fresher/Junior), kỹ năng chuẩn kèm trọng số và tài nguyên học tập đã kiểm duyệt.
- `/register` và `/login`: Đăng ký tài khoản mới và đăng nhập (tự động điều hướng Admin về `/admin`, học viên về `/explore` hoặc `/profile`).
- `/profile`: Quản lý hồ sơ cá nhân, ngành học, trường, điểm mạnh, tự đánh giá kỹ năng và vị trí mục tiêu.
- `/cv`: Tải lên CV định dạng PDF (tối đa 5MB), trích xuất nội dung văn bản bằng PyMuPDF, cảnh báo PDF ảnh quét và hỗ trợ xóa mềm CV.
- `/analysis`: Chạy phân tích khoảng cách kỹ năng bằng AI từ CV hoặc Hồ sơ (bắt buộc xác nhận AI Consent) và xem báo cáo chi tiết + lịch sử phân tích.
- `/roadmap`: Xem và tương tác với lộ trình học tập cá nhân hóa 30 ngày (chia 4 tuần), đánh dấu hoàn thành nhiệm vụ và truy cập tài nguyên học tập chuẩn.
- `/interview`: Luyện phỏng vấn thử AI theo vị trí mục tiêu (sinh bộ 3 câu hỏi, chấm điểm thang 0–100 kèm nhận xét chi tiết và tự động đóng phiên bỏ dở quá 24 giờ).
- `/dashboard`: Bảng điều khiển tổng hợp điểm sẵn sàng nghề nghiệp, biểu đồ Radar kỹ năng, lịch sử tiến bộ, tiến độ lộ trình và lịch sử phỏng vấn.
- `/admin`: Phân hệ quản trị dành riêng cho Admin (tự động chặn `403` nếu truy cập bằng tài khoản học viên), quản lý vị trí nghề nghiệp, nhóm nghề, kỹ năng, kiểm duyệt tài nguyên học tập, thống kê hệ thống và khóa/mở khóa người dùng.

### Nhóm API chính (xem tài liệu Swagger tại `/docs`)
- **Xác thực (`/api/v1/auth`):** `POST /register`, `POST /login`, `POST /refresh`, `POST /logout`, `GET /me`.
- **Hồ sơ & CV (`/api/v1/profile`, `/api/v1/cvs`):** Xem/cập nhật hồ sơ cá nhân; tải lên, xem danh sách, chi tiết và xóa CV.
- **Danh mục công khai (`/api/v1/catalog`, `/api/v1/careers`):** Tra cứu nhóm nghề, vị trí, kỹ năng yêu cầu và tài nguyên đã được duyệt (`approved`).
- **Phân tích AI (`/api/v1/analyses`):**
  - `POST /api/v1/analyses`: Tiếp nhận yêu cầu phân tích (trả về `202 Accepted` và xử lý nền).
  - `GET /api/v1/analyses?page=1&page_size=10`: Lịch sử phân tích của sinh viên hiện tại.
  - `GET /api/v1/analyses/{analysis_id}/status`: Kiểm tra trạng thái (`pending`, `processing`, `completed`, `failed`).
  - `GET /api/v1/analyses/{analysis_id}` & `/{analysis_id}/skills`: Xem điểm sẵn sàng, tóm tắt, bằng chứng trích xuất và khuyến nghị từng kỹ năng.
- **Lộ trình học tập (`/api/v1/learning-plans`):** Tạo lộ trình 30 ngày từ báo cáo phân tích, cập nhật trạng thái lộ trình và tiến độ từng nhiệm vụ.
- **Phỏng vấn thử (`/api/v1/interviews`):** Tạo phiên phỏng vấn, lấy câu hỏi, nộp câu trả lời để AI chấm điểm và hoàn thành phiên để tính điểm trung bình.
- **Dashboard (`/api/v1/dashboard`):** `/summary`, `/skill-radar`, `/readiness-history`, `/learning-progress`, `/interview-history`.
- **Quản trị (`/api/v1/admin`):** Quản lý danh mục (hỗ trợ ẩn mềm theo trạng thái), kiểm duyệt tài nguyên (`pending`/`approved`/`rejected`), thống kê hệ thống (`/stats`) và quản lý trạng thái người dùng (`/users`).

> **Quy ước sử dụng dịch vụ AI trong mã nguồn:** Các module nghiệp vụ gọi lớp dịch vụ dùng chung qua `create_ai_service()` / `get_ai_service().generate_structured(...)` trong `app/services/ai`, không gọi trực tiếp SDK `google.genai` tại router hoặc service nghiệp vụ.

---

## 5. Kiểm thử tự động (Pytest)

Toàn bộ bộ kiểm thử dùng SQLite in-memory và mock AI provider, không gọi Gemini thật và không yêu cầu `GEMINI_API_KEY`:

- Chạy kiểm thử lớp dịch vụ AI:
  ```powershell
  python -m pytest tests/test_ai_config.py tests/test_ai_provider.py tests/test_ai_service.py -q
  ```
- Chạy unit test tầng Service (tính điểm, phân quyền, phỏng vấn) & kiểm thử toàn luồng E2E:
  ```powershell
  python -m pytest tests/test_service_unit.py tests/test_e2e_user_journey.py -q
  ```
- Chạy toàn bộ test suite của dự án:
  ```powershell
  python -m pytest -q
  ```

---

## 6. Triển khai chạy thử HTTPS, Sao lưu & Khôi phục

Xem hướng dẫn chi tiết từng bước tại [`DEPLOYMENT.md`](DEPLOYMENT.md) để đóng gói bằng Docker Compose, chạy qua Nginx + HTTPS, sao lưu định kỳ và khôi phục dữ liệu (MySQL và thư mục CV đã tải lên).
