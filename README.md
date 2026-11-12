# AI Career Mentor

## Initial installation

Use Python 3.11+ and MySQL 8.x (InnoDB, `utf8mb4`). The existing application
dependencies are listed in `requirements.txt`; no extra package is required for
catalog data or administration.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `DATABASE_URL` in `.env` to your MySQL database, including
`?charset=utf8mb4`. Generate a private random `SECRET_KEY` with
`python -c "import secrets; print(secrets.token_urlsafe(32))"` and set it in
`.env`. Set `CORS_ALLOWED_ORIGINS` to a JSON list of exact frontend origins
(for example `["https://your-frontend.example"]`) when the frontend is hosted on
a different origin; wildcard origins are not accepted. Never commit `.env`.

The API uses bcrypt-hashed passwords and short-lived HS256 Bearer tokens.
Login returns a short-lived access token and a 14-day refresh token. The refresh
token is opaque, stored only as a SHA-256 hash in MySQL, and rotated every time
`POST /api/v1/auth/refresh` is used. Reusing an old token revokes its session
family. `POST /api/v1/auth/logout` revokes the submitted refresh token; the
already-issued access token remains usable until its short expiry. The browser
automatically refreshes protected API requests after an access-token `401`.

Public registration always creates a student; Admin rights are checked against
the current database role on every request. API successes and errors use a
consistent JSON envelope, retaining `detail` on errors for existing clients.
In production, `SECRET_KEY` must be explicitly configured.

Run the database migration; it creates the learning-resource table and seeds
career categories, roles, role-skill requirements, skills, and curated learning
links. Then create the administrator. The command prompts for the email and
reads the password without echoing it, so do not put the password in `.env` or
on the command line.

```powershell
python -m alembic upgrade head
python -m app.bootstrap_admin
python -m uvicorn app.main:app --reload
```

Choose an Admin password of 8–72 UTF-8 bytes and confirm it at the prompt. The
bootstrap command is safe to repeat for an existing Admin account; it refuses
to promote an existing student account.

## Data discovery and administration

- `/` and `/explore`: browse career paths, required skills, and learning links.
- `/api/v1/catalog/categories`, `/roles`, `/skills`, `/resources`: public,
  read-only catalog APIs.
- `/api/v1/admin/catalog`: Admin-only catalog overview.
- `/api/v1/admin/career-categories`, `/career-roles`, `/skills`, `/resources`:
  Admin-only create, update, and delete APIs. Interactive API documentation is
  at `/docs`; authenticate with an Admin access token to use these endpoints.

Registering through the public auth API always creates a student account.
Admin access is granted only through the bootstrap command or an existing
administrator process.

## Skill-gap analysis

`POST /api/v1/analyses` accepts a CV (optional when a student profile exists),
a target `career_role_id`, and the existing explicit consent object. It returns
`202 Accepted` with an analysis ID and status URL. Poll
`GET /api/v1/analyses/{id}` with the same Bearer token until the status is
`completed` or `failed`.

The worker compares profile skill levels with each role requirement. A skill
mentioned in extracted CV, profile bio, or strengths counts as evidence at
level 1 only; proficiency must come from the user's self-assessment. If both
sources are selected, the higher explicit profile level is used. Readiness is
the rounded, weight-adjusted percentage of target levels achieved. The result,
score, and per-skill snapshots are committed together. Processing is in-process
with FastAPI background tasks, so a durable external queue is needed before
multi-worker production deployment.

Apply pending schema changes before using the endpoint:

```powershell
python -m alembic upgrade head
```

## Giao diện đăng nhập / đăng ký

Hai trang giao diện tương ứng UI-01 trong SRS:

- `/register`: biểu mẫu email, mật khẩu (8–72 ký tự) và nhập lại mật khẩu.
  Đăng ký thành công sẽ tự động đăng nhập và chuyển tới `/profile`.
- `/login`: biểu mẫu email và mật khẩu; đăng nhập thành công lưu access token
  vào `localStorage` (khóa `acm_access_token`) rồi chuyển tới `next` hoặc
  `/explore`.
- Nav của các trang hiển thị `Đăng nhập` khi chưa có phiên và `Đăng xuất` khi
  đã đăng nhập. `/profile`, `/cv`, `/analysis`, `/interview` chuyển về `/login`
  nếu chưa có token hoặc token đã hết hạn (401).

Access token dùng chung với các trang hiện có nên không cần dán token thủ công.
FR-AUTH-06 (refresh token, thu hồi token phía máy chủ) vẫn ở mức Could và chưa
triển khai; đăng xuất hiện chỉ xóa token trong trình duyệt.

## Phân tích khoảng cách kỹ năng (M4)

Trang `/analysis` hiện thực UI-05: chọn CV/hồ sơ và vị trí nghề nghiệp, đồng ý
gửi dữ liệu cho AI, theo dõi trạng thái và xem báo cáo. API tương ứng:

- `POST /api/v1/analyses` trả `202 Accepted` kèm `id` và trạng thái
  `processing`; quá trình phân tích chạy nền bằng `BackgroundTasks`.
- `GET /api/v1/analyses`: lịch sử báo cáo của chính người dùng.
- `GET /api/v1/analyses/{id}`: chi tiết báo cáo kèm danh sách kỹ năng.
- `GET /api/v1/analyses/{id}/status`: trạng thái `processing`, `completed`
  hoặc `failed` (kèm `failure_reason` khi lỗi).
- `GET /api/v1/analyses/{id}/skills`: điểm kỹ năng và khuyến nghị.

Backend tự tính `gap_score = max(0, required_level - current_level)` và
`readiness_score` theo SRS 6.3; AI chỉ trả mức hiện tại và bằng chứng. Kỹ năng
không có bằng chứng được ghi nhận `current_level = 0`, `has_evidence = false`
nhưng vẫn giữ trọng số. Mọi endpoint đều yêu cầu Bearer token và chỉ trả dữ
liệu thuộc sở hữu của người dùng hiện tại.

## Phỏng vấn thử (M6)

Trang `/interview` hiện thực UI-07 theo luồng tuần tự từng câu hỏi. API:

- `POST /api/v1/interviews` sinh đúng 3 câu hỏi; chỉ lưu phiên khi AI trả đủ
  dữ liệu hợp lệ, ngược lại rollback toàn bộ.
- `GET /api/v1/interviews/{id}/questions`: danh sách câu hỏi.
- `POST /api/v1/interviews/{id}/answers`: lưu câu trả lời, chấm điểm 0–100 và
  phản hồi; gửi trùng một câu trả về `409`.
- `POST /api/v1/interviews/{id}/complete`: chỉ hoàn thành khi đủ 3 câu; tổng
  điểm là trung bình cộng điểm các câu.
- `GET /api/v1/interviews` và `GET /api/v1/interviews/{id}`: lịch sử và chi
  tiết phiên.

Phiên `in_progress` quá 24 giờ (hoặc khi người dùng tạo phiên mới cùng vị trí)
được đánh dấu `abandoned` theo FR-INT-08/BR-07 khi đọc hoặc tạo phiên; hệ thống
không chạy scheduler riêng.

## Cấu hình dịch vụ AI (Gemini)

Lớp hạ tầng AI dùng chung cấp `AIService`/`GeminiProvider` cho các nghiệp vụ
Skill Gap Analysis (M4) và Mock Interview (M6). Hai nghiệp vụ này không gọi
trực tiếp SDK Gemini.

Thêm các biến sau vào `.env` (không commit `.env`):

```dotenv
AI_PROVIDER=gemini
GEMINI_API_KEY=<API Key lấy tại https://aistudio.google.com/apikey>
GEMINI_MODEL=gemini-3.5-flash
AI_TIMEOUT=30
AI_MAX_RETRIES=2
```

- `AI_PROVIDER`: hiện chỉ hỗ trợ `gemini`. Giá trị khác sẽ phát sinh
  `AIConfigurationError`.
- `GEMINI_API_KEY`: bắt buộc khi thực sự gọi AI; không bắt buộc để khởi động
  ứng dụng hoặc chạy unit test.
- `GEMINI_MODEL`: tên model Gemini cần sử dụng; không được để trống khi gọi AI.
- `AI_TIMEOUT`: thời gian chờ mỗi request, tính bằng giây.
- `AI_MAX_RETRIES`: số lần retry tối đa cho lỗi tạm thời (mạng, 5xx, 429,
  timeout). Lỗi cấu hình, xác thực, request sai và dữ liệu không hợp lệ không
  được retry.

Các module nghiệp vụ nên dùng:

```python
from app.services.ai import AIResponseValidationError, create_ai_service

ai_service = create_ai_service()
result = await ai_service.generate_structured(
    prompt=prompt,
    response_schema=SomePydanticSchema,
)
```

Không gọi trực tiếp `google.genai` trong router hoặc business service.

`GeminiProvider` tự chuyển JSON Schema của Pydantic sang dạng Gemini chấp nhận:
loại bỏ `additionalProperties`/`additional_properties`, `exclusiveMinimum`/
`exclusiveMaximum` và toàn bộ ràng buộc số lượng/độ dài (`minItems`,
`maxItems`, `minLength`, `maxLength`, `minimum`, `maximum`, ...) vì model trả
`400 INVALID_ARGUMENT` khi gặp chúng. Schema gốc của Pydantic không bị sửa và
`AIService` vẫn xác thực đầy đủ mọi ràng buộc sau khi nhận phản hồi.

### Chạy unit test AI

Unit test dùng mock hoàn toàn, không gọi Gemini thật và không cần
`GEMINI_API_KEY`:

```powershell
python -m pytest tests/test_ai_config.py tests/test_ai_provider.py tests/test_ai_service.py -q
```

Kiểm tra phản hồi Gemini thật là opt-in; cấu hình `GEMINI_API_KEY` và
`GEMINI_MODEL` trong `.env`, sau đó chạy lệnh sau trong PowerShell. Lệnh này
gửi request bên ngoài và có thể tiêu thụ quota API:

```powershell
$env:RUN_GEMINI_LIVE_TESTS = "1"
python -m pytest tests/integration/test_gemini_live.py -q
```

Nếu không bật `RUN_GEMINI_LIVE_TESTS=1`, test live sẽ được bỏ qua.

Chạy toàn bộ test suite:

```powershell
python -m pytest -q
```
