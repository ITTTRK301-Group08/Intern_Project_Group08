"""Schema phản hồi phiên phỏng vấn thử."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.auth import ApiResponse


class InterviewCareerRoleRead(BaseModel):
    """Thông tin tối thiểu của vị trí nghề nghiệp trong phiên phỏng vấn."""

    id: int
    name: str
    level: str

    model_config = ConfigDict(from_attributes=True)


class InterviewQuestionRead(BaseModel):
    """Câu hỏi phỏng vấn kèm năng lực và tiêu chí đánh giá."""

    id: int
    question_order: int
    question_text: str
    competency: str
    evaluation_criteria: list[str]

    model_config = ConfigDict(from_attributes=True)


class InterviewSessionRead(BaseModel):
    """Phiên phỏng vấn đã được tạo cùng đúng 3 câu hỏi."""

    id: int
    status: str
    career_role: InterviewCareerRoleRead | None
    questions: list[InterviewQuestionRead]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


InterviewSessionResponse = ApiResponse[InterviewSessionRead]
