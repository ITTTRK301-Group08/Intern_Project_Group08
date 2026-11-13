"""Schema cơ sở dùng chung cho dữ liệu JSON có cấu trúc của AI."""

from pydantic import BaseModel, ConfigDict


class AIStructuredResponse(BaseModel):
    """Lớp cơ sở cho mọi schema đầu ra có cấu trúc của AI.

    Các schema nghiệp vụ nên kế thừa lớp này để thống nhất quy tắc xác thực:
    - Từ chối các trường lạ do AI tự thêm vào (`extra="forbid"`).
    - Tự động cắt khoảng trắng thừa ở hai đầu chuỗi.

    Nếu một nghiệp vụ cần chấp nhận trường bổ sung, có thể ghi đè
    `model_config` ngay trong schema con.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
