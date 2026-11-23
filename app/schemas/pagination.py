"""Schema phân trang dùng chung cho các API danh sách.

Giữ đúng cấu trúc ``items/total/page/page_size/total_pages`` đã dùng ở
``interview_history`` và ``dashboard`` để response Admin nhất quán với phần
còn lại của hệ thống.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 10
    total_pages: int = 1
