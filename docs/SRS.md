# Đặc tả yêu cầu phần mềm (SRS) — Career Mentor MVP

**Phiên bản:** 1.0  
**Cơ sở đối chiếu:** mã nguồn nhánh `master`, commit `473df9a`  
**Phạm vi:** MVP định hướng nghề nghiệp cho sinh viên CNTT và phân hệ quản trị.

## 1. Mục tiêu và đối tượng

Career Mentor giúp sinh viên tự đánh giá mức độ phù hợp với vị trí nghề nghiệp, phân tích khoảng cách kỹ năng từ CV/hồ sơ, tạo lộ trình học tập và luyện phỏng vấn. Quản trị viên duy trì danh mục nghề nghiệp, tài nguyên học tập và tài khoản người dùng.

- **Sinh viên:** tài khoản vai trò `student`, sử dụng các chức năng cá nhân sau khi đăng nhập.
- **Quản trị viên:** tài khoản vai trò `admin`, được cấp bằng bootstrap CLI hoặc quản trị hiện hữu; quản lý nội dung và người dùng.
- **Khách chưa đăng nhập:** xem trang khám phá/danh mục công khai; đăng ký và đăng nhập.

## 2. Yêu cầu chức năng

### 2.1 Luồng Sinh viên

| ID | Yêu cầu | Điều kiện/kết quả mong đợi |
|---|---|---|
| ST-01 | Đăng ký, đăng nhập, đăng xuất và xem tài khoản hiện tại. | Đăng ký công khai chỉ tạo vai trò `student`; đăng nhập trả access/refresh token; đăng xuất thu hồi refresh session. |
| ST-02 | Gia hạn phiên đăng nhập. | Refresh token được xoay vòng; token tái sử dụng có thể làm thu hồi toàn bộ session family. |
| ST-03 | Xem và cập nhật hồ sơ. | Hồ sơ lưu họ tên, ngành học, trường, mục tiêu, giới thiệu, điểm mạnh và tự đánh giá kỹ năng. |
| ST-04 | Khám phá danh mục nghề nghiệp. | Xem nhóm nghề, vị trí, kỹ năng yêu cầu và tài nguyên học tập đã duyệt/đang hoạt động. |
| ST-05 | Tải lên và quản lý CV PDF. | CV thuộc người dùng hiện tại; hệ thống lưu tệp, trích xuất văn bản và hỗ trợ xem/xóa mềm. Giới hạn và kiểm tra định dạng theo API. |
| ST-06 | Phân tích mức độ sẵn sàng và khoảng cách kỹ năng. | Chọn vị trí mục tiêu, dùng CV hoặc hồ sơ có dữ liệu, chấp thuận AI consent theo phiên bản được hỗ trợ; yêu cầu được nhận xử lý nền, cho phép theo dõi trạng thái/báo cáo/lịch sử. |
| ST-07 | Tạo và cập nhật lộ trình học tập. | Tạo từ báo cáo phân tích; xem lộ trình/nhiệm vụ và đánh dấu nhiệm vụ hoàn thành. Mốc nghiệp vụ MVP hướng tới 30 ngày; mô hình lưu tuần 1–8. |
| ST-08 | Luyện phỏng vấn thử. | Chọn vị trí, chấp thuận AI consent, tạo phiên có 3 câu hỏi; nộp câu trả lời, nhận điểm/nhận xét và hoàn thành phiên để tính điểm tổng. Phiên bỏ dở cũ có cơ chế tự chuyển abandoned. |
| ST-09 | Theo dõi Dashboard. | Xem điểm readiness, radar kỹ năng, lịch sử readiness, tiến độ lộ trình và lịch sử phỏng vấn. |

### 2.2 Luồng Quản trị viên

| ID | Yêu cầu | Điều kiện/kết quả mong đợi |
|---|---|---|
| AD-01 | Xem thống kê hệ thống. | Số người dùng/tài khoản hoạt động/khóa, phân tích, phỏng vấn, danh mục và tài nguyên chờ duyệt được trả về từ dữ liệu lưu trữ. |
| AD-02 | Tra cứu và xem chi tiết người dùng. | Có tìm kiếm, lọc vai trò/trạng thái và phân trang; dữ liệu nhạy cảm như password hash không xuất hiện trong response. |
| AD-03 | Khóa/mở khóa tài khoản. | Trạng thái người dùng được cập nhật; người dùng bị khóa không đăng nhập và không sử dụng API bảo vệ; Admin không tự khóa chính mình. |
| AD-04 | Quản lý nhóm nghề. | Xem danh sách/chi tiết, tạo, sửa và xóa theo quy tắc phụ thuộc danh mục. |
| AD-05 | Quản lý vị trí nghề nghiệp. | CRUD, gán nhóm/ngạch nghề, cấu hình các kỹ năng yêu cầu, mức yêu cầu và trọng số; hỗ trợ bật/tắt. Xóa vị trí được thực hiện theo kiểu vô hiệu hóa. |
| AD-06 | Quản lý kỹ năng. | Tạo/sửa/vô hiệu hóa và bật lại kỹ năng. |
| AD-07 | Quản lý và kiểm duyệt tài nguyên học tập. | Tạo/sửa, duyệt `pending`/`approved`/`rejected`, bật/tắt; tài nguyên công khai phải được duyệt và đang hoạt động. |

## 3. Phân quyền và bảo vệ dữ liệu

- Mọi API quản trị dưới `/api/v1/admin` yêu cầu đăng nhập và `require_admin`; UI `/admin` là giao diện tĩnh, quyền thật được kiểm tra tại API.
- API sinh viên đọc/ghi dữ liệu theo `current_user` từ JWT; người dùng không được truy cập CV, phân tích, lộ trình hoặc phiên phỏng vấn của người khác.
- Đăng ký công khai không cho chọn vai trò Admin. Vai trò hợp lệ bị giới hạn `student` hoặc `admin`.
- Tài khoản không hoạt động bị từ chối đăng nhập và request được bảo vệ.
- Mật khẩu được băm; refresh token chỉ lưu dạng hash; secret production phải cấu hình riêng.
- AI consent được backend xác minh, không tin cậy metadata chỉ do frontend gửi.
- Không gửi API key lên frontend; AI key chỉ được cấu hình phía server. CV chứa dữ liệu cá nhân cần được bảo vệ khi lưu, sao lưu và chia sẻ.

## 4. Yêu cầu phi chức năng/giới hạn MVP

- Backend FastAPI; dữ liệu production hướng tới MySQL 8/InnoDB/utf8mb4, SQLAlchemy và Alembic.
- Giao diện HTML/CSS/JavaScript thuần, được phục vụ cùng FastAPI.
- AI dùng Google Gemini qua lớp dịch vụ chung; chức năng AI thật cần API key, model và kết nối mạng hợp lệ. Không có key thì có thể khởi động, nhưng không thể nghiệm thu phân tích/phỏng vấn AI thật.
- API validation lỗi trả HTTP 422; lỗi quyền thường trả 401/403; có `/health` phục vụ healthcheck và `/docs` cho OpenAPI.
- Bộ test hiện có dùng SQLite in-memory và mock AI; kết quả test không thay thế nghiệm thu MySQL/Gemini thực.

## 5. Tiêu chí nghiệm thu MVP

1. **Sinh viên:** đăng ký → đăng nhập → cập nhật hồ sơ → xem danh mục → tải CV → đồng ý AI và phân tích → xem kết quả/skill gap → tạo lộ trình → hoàn thành một nhiệm vụ → luyện phỏng vấn đủ 3 câu → xem điểm và Dashboard.
2. **Admin:** bootstrap/đăng nhập Admin → xem thống kê → tra cứu người dùng → khóa/mở khóa tài khoản thử → tạo/cập nhật dữ liệu nhóm nghề, vị trí, kỹ năng → tạo tài nguyên và duyệt → xác nhận nội dung công khai phản ánh trạng thái duyệt.
3. **Phân quyền:** học viên gọi API Admin nhận 403; dữ liệu của người dùng khác không đọc/sửa được; tài khoản bị khóa bị chặn; đăng ký công khai không tạo Admin.
4. **Dữ liệu:** migration đi tới `f7a8b9c0d1e2`; dữ liệu catalog/tài nguyên mẫu có sẵn; thao tác tạo và cập nhật có thể đọc lại sau khi request hoàn tất.
5. **Khởi động:** Uvicorn phục vụ `/health` (200), trang chủ, `/admin` và `/docs`; log không có lỗi runtime trong suốt demo.
6. **AI thật:** kiểm tra với Gemini API key hợp lệ; xác nhận consent bắt buộc, output có cấu trúc và kết quả được lưu. Không dùng test mock để tuyên bố đã nghiệm thu nhà cung cấp AI.
7. **Kiểm thử:** `python -m pytest -q` kết thúc exit code 0; nghiệm thu môi trường dùng dữ liệu demo riêng, không dùng dữ liệu thật của sinh viên.

## 6. Ngoài phạm vi xác nhận trong MVP

Không có bằng chứng trong repository để kết luận hiệu năng tải lớn, SLA/HA, khôi phục backup định kỳ đã diễn tập, hoặc tính đúng đắn/độ thiên lệch của đánh giá AI trên dữ liệu thật. Các mục này cần môi trường và kế hoạch kiểm thử riêng.
