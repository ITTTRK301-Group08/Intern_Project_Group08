# Kịch bản Demo, Checklist nghiệm thu và Backlog — MVP

**Phiên bản:** 1.0 · Đối chiếu code `master` tại `473df9a`

## 1. Trạng thái xác minh trước demo

| Hạng mục | Kết quả hiện tại | Ghi chú |
|---|---|---|
| Nhánh và worktree | `master`, clean trước khi cập nhật hồ sơ | Commit tham chiếu `473df9a`. |
| Test tự động | **322 passed**, `python -m pytest -q`, exit code 0 | Test dùng SQLite in-memory/mocks; không chứng minh MySQL/Gemini thật. |
| Migration graph | **PASS — một head:** `f7a8b9c0d1e2` | Alembic history/heads đọc được. `alembic current` chưa chạy được: `DATABASE_URL` chưa cấu hình; Docker daemon cũng không khả dụng để dựng MySQL. |
| Khởi động ứng dụng | **PASS — local smoke** | Uvicorn với SQLite ephemeral đã trả `GET /health` 200 và `/docs` 200. |
| Giao diện/luồng trong HTTP app | Có UI student/Admin; E2E integration test hiện có kiểm tra luồng toàn trình | Trang chủ cần probe lại trong môi trường demo nếu cần xác nhận trình duyệt. |
| Docker staging | **Chưa xác minh** | `docker info` thất bại; daemon không khả dụng tại thời điểm kiểm tra. |
| Gemini thật | **Chưa xác minh** | Cần `GEMINI_API_KEY` hợp lệ, model/cấu hình và mạng ngoài. |

## 2. Chuẩn bị trước buổi demo

### Môi trường và dữ liệu

- [ ] Python 3.11+ (README yêu cầu); tạo virtualenv và cài `requirements.txt`.
- [ ] MySQL 8.x sẵn sàng, database/collation utf8mb4; kiểm tra kết nối từ `DATABASE_URL`.
- [ ] `.env` được tạo từ `.env.example`; tạo `SECRET_KEY` ngẫu nhiên riêng (ít nhất 32 bytes), cấu hình DB; cấu hình Gemini nếu demo AI thật.
- [ ] Chạy `python -m alembic upgrade head`; xác nhận revision `f7a8b9c0d1e2` bằng `python -m alembic current`.
- [ ] Seed danh mục và tài nguyên mẫu được tạo bởi migration; xác nhận có role hoạt động với required skills và resource đã duyệt.
- [ ] Tạo Admin bằng `python -m app.bootstrap_admin` trong terminal tương tác; dùng mật khẩu thử nghiệm an toàn, không ghi vào tài liệu.
- [ ] Chuẩn bị email sinh viên demo; đăng ký tài khoản trong giao diện.
- [ ] Nếu không bật AI thật: nói rõ phần AI chỉ được mô phỏng trong automated tests; không trình bày dữ liệu mock như kết quả Gemini thật.
- [ ] Kiểm tra `/health`, `/docs`, trang chủ và `/admin`; chuẩn bị browser profile riêng hoặc cửa sổ ẩn danh để đổi user.

## 3. Kịch bản demo gợi ý (15–20 phút)

### A. Khách và sinh viên (8–10 phút)

1. Mở `/` hoặc `/explore`, duyệt nhóm nghề/vị trí và tài nguyên đã duyệt.
2. Đăng ký sinh viên tại `/register`, đăng nhập ở `/login`; xác nhận vai trò student.
3. Mở `/profile`, nhập tên, ngành/trường, vị trí mục tiêu, điểm mạnh và tự đánh giá kỹ năng; lưu rồi tải lại xác nhận persistence.
4. Mở `/cv`, tải CV PDF hợp lệ; xem nội dung trích xuất và lịch sử CV. Thử xem CV thuộc user khác nếu có dữ liệu kiểm thử (mong đợi bị từ chối).
5. Mở `/analysis`, chọn role và nguồn dữ liệu, xác nhận consent AI. Chờ status hoàn tất; trình bày readiness score, evidence, gap và gợi ý. Nếu Gemini không khả dụng, dừng ở bước nêu hạn chế, không tuyên bố AI đã chạy.
6. Mở `/roadmap`, tạo từ analysis, duyệt nhiệm vụ từng tuần và đánh dấu một nhiệm vụ hoàn thành; refresh để chứng minh được lưu.
7. Mở `/interview`, tạo phiên, trả lời ba câu hỏi, xem phản hồi/điểm và kết quả tổng.
8. Mở `/dashboard`; đối chiếu readiness, radar kỹ năng, tiến độ plan và lịch sử interview vừa tạo.

### B. Quản trị viên (5–7 phút)

1. Đăng xuất sinh viên, đăng nhập tài khoản Admin đã bootstrap; vào `/admin`.
2. Trình bày thống kê tổng, danh sách/tìm kiếm người dùng và chi tiết người dùng.
3. Tạo/cập nhật nhóm nghề, kỹ năng và vị trí; gắn required skills với mức yêu cầu/trọng số.
4. Tạo resource demo ở trạng thái chờ duyệt, kiểm tra trạng thái `pending`, duyệt sang `approved`; quay lại catalog công khai xác nhận resource xuất hiện.
5. Khóa tài khoản sinh viên thử nghiệm; xác minh đăng nhập/API bị chặn; mở khóa lại. Không khóa Admin đang dùng.
6. Gọi thử API Admin bằng token student hoặc mở `/admin` khi đang đăng nhập student: UI/API không được trao quyền; API mong đợi 403.

## 4. Checklist ký nghiệm thu

| # | Tiêu chí quan sát được | Kết quả | Bằng chứng/ghi chú |
|---|---|---|---|
| 1 | Student register/login, chỉ tạo role student | ☐ Đạt ☐ Không đạt | |
| 2 | Hồ sơ cập nhật và đọc lại được | ☐ Đạt ☐ Không đạt | |
| 3 | Catalog công khai chỉ hiển thị role/skill/resource hợp lệ | ☐ Đạt ☐ Không đạt | |
| 4 | Tải CV PDF, trích xuất và giới hạn quyền sở hữu | ☐ Đạt ☐ Không đạt | |
| 5 | AI consent được yêu cầu ở backend; phân tích trả status/report | ☐ Đạt ☐ Không đạt ☐ Chưa demo AI thật | |
| 6 | Lộ trình gắn với analysis; cập nhật item phản ánh trên Dashboard | ☐ Đạt ☐ Không đạt | |
| 7 | Phiên phỏng vấn có 3 câu, lưu câu trả lời, điểm và tổng kết | ☐ Đạt ☐ Không đạt ☐ Chưa demo AI thật | |
| 8 | Student bị chặn API Admin; dữ liệu user được cô lập | ☐ Đạt ☐ Không đạt | |
| 9 | Admin xem stats/users, CRUD catalog, review resource, khóa/mở khóa | ☐ Đạt ☐ Không đạt | |
| 10 | Migration hiện hành, Uvicorn health, `/docs`, log không lỗi | ☐ Đạt ☐ Không đạt | |
| 11 | Test suite exit code 0 | ☐ Đạt ☐ Không đạt | 322 passed trong lần rà soát hiện tại |
| 12 | Bàn giao source code và ba tài liệu trong `docs/` | ☐ Đạt ☐ Không đạt | |

**Người nghiệm thu:** ____________________  **Ngày:** __________  
**Kết luận:** ☐ Chấp nhận MVP ☐ Chấp nhận có điều kiện ☐ Chưa chấp nhận  
**Tồn tại/điều kiện:** ______________________________________________________

## 5. Backlog tổng hợp

“Đã triển khai” nghĩa là logic/route và test/source liên quan có mặt trong repository, không đồng nghĩa đã nghiệm thu trên staging hay với Gemini thật.

| Mã | Hạng mục | Trạng thái theo code | Việc còn lại/điều kiện nghiệm thu |
|---|---|---|---|
| BL-01 | Auth, JWT, refresh rotation, logout, role/status guard | Đã triển khai; có test | Demo đăng nhập thực và kiểm tra refresh/revoke trên DB mục tiêu. |
| BL-02 | Hồ sơ sinh viên, điểm mạnh và tự đánh giá kỹ năng | Đã triển khai; có test | Xác nhận với browser và dữ liệu MySQL demo. |
| BL-03 | Catalog nghề, role, skill và resource đã duyệt | Đã triển khai; migration seed có mặt | Kiểm tra seed sau `upgrade head`; duyệt resource Admin và xác nhận public. |
| BL-04 | Upload CV PDF, extraction, ownership và soft delete | Đã triển khai; có test | Kiểm tra PDF thực, dung lượng/loại file và persistence uploads trong môi trường demo. |
| BL-05 | AI skill-gap analysis, consent, background state/report | Đã triển khai; test mock | Chưa nghiệm thu Gemini thật; cần API key/model, kiểm tra timeout/retry và output thực. |
| BL-06 | Lộ trình sinh từ analysis, tuần/nhiệm vụ, tiến độ | Đã triển khai; test mock AI/persistence | Chạy đầy đủ trên DB demo; xác nhận trải nghiệm tuần và trạng thái. |
| BL-07 | Phỏng vấn, ba câu hỏi, chấm điểm, lịch sử, auto-abandon | Đã triển khai; có test service/API | Chưa nghiệm thu với Gemini thật; kiểm tra ngưỡng thời gian abandonment và persistence trên MySQL. |
| BL-08 | Dashboard readiness/radar/learning/interview | Đã triển khai; có test | Đối chiếu dữ liệu sau hành trình end-to-end trên instance demo. |
| BL-09 | Admin stats, user search/detail, lock/unlock | Đã triển khai; có test | Demo Admin với tài khoản riêng; xác nhận không tự khóa tài khoản đang dùng. |
| BL-10 | Admin CRUD nhóm nghề/role/skill/resource + moderation | Đã triển khai; test quản trị | Demo các thao tác ghi và trạng thái catalog public. |
| BL-11 | Alembic migrations/compatibility/seed | 25 revisions; graph một head `f7a8b9c0d1e2` | **Chưa chạy `current`/`upgrade head` trên DB thật** vì `DATABASE_URL` chưa cấu hình và Docker daemon không khả dụng; cần kiểm tra trên DB sạch và DB legacy cần hỗ trợ. |
| BL-12 | Docker Compose + Nginx HTTPS staging | Cấu hình trong repo | Chưa được chạy vì Docker daemon không hoạt động; cần deploy/smoke test staging và HTTPS. |
| BL-13 | Bộ test repository | 322 passed tại môi trường rà soát | Bổ sung/ghi nhận browser acceptance test và integration test trên MySQL/Gemini nếu tiêu chí bàn giao yêu cầu. |
| BL-14 | Runbook và tài liệu bàn giao | README/DEPLOYMENT tồn tại; SRS/System Design/Demo checklist-backlog mới cập nhật | Chủ dự án điền kết quả ký nghiệm thu và URL/chi tiết môi trường demo nội bộ. |

## 6. Điều kiện kết thúc buổi demo

- [ ] Không có blocker P0/P1 trong luồng đã demo.
- [ ] Các tiêu chí 1–4, 6, 8–12 ở checklist được ký đạt; tiêu chí AI được đánh dấu riêng nếu chưa dùng Gemini thật.
- [ ] Ghi rõ version/revision DB, cấu hình AI có/không, lỗi còn lại và người phụ trách backlog.
- [ ] Không đưa `.env`, mật khẩu, API key, CV cá nhân hoặc backup chứa dữ liệu thật vào gói bàn giao.
