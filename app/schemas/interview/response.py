"""Schema phản hồi cho nghiệp vụ phỏng vấn thử."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.auth import ApiResponse


class InterviewCareerRoleRead(BaseModel):
    """Thông tin tối thiểu của vị trí nghề nghiệp trong phiên phỏng vấn."""

    id: int
    name: str
    level: str

    model_config = ConfigDict(from_attributes=True)


class InterviewAnswerRead(BaseModel):
    """Câu trả lời kèm điểm và phản hồi cải thiện."""

    id: int
    question_id: int
    answer_text: str
    score: float
    feedback: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterviewQuestionRead(BaseModel):
    """Câu hỏi phỏng vấn kèm năng lực, tiêu chí và câu trả lời (nếu có)."""

    id: int
    question_order: int
    question_text: str
    competency: str
    evaluation_criteria: list[str]
    answer: InterviewAnswerRead | None = None

    model_config = ConfigDict(from_attributes=True)


class InterviewSessionRead(BaseModel):
    """Phiên phỏng vấn cùng danh sách câu hỏi theo thứ tự."""

    id: int
    status: str
    career_role: InterviewCareerRoleRead | None
    total_score: float | None
    questions: list[InterviewQuestionRead]
    created_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class InterviewSummaryRead(BaseModel):
    """Thông tin tổng quan của một phiên trong lịch sử."""

    id: int
    status: str
    career_role: InterviewCareerRoleRead | None
    total_score: float | None
    created_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class InterviewHistoryData(BaseModel):
    """Danh sách phiên phỏng vấn của người dùng hiện tại."""

    interviews: list[InterviewSummaryRead]
    total: int


class InterviewQuestionsData(BaseModel):
    """Danh sách câu hỏi theo thứ tự của một phiên."""

    session_id: int
    questions: list[InterviewQuestionRead]


InterviewSessionResponse = ApiResponse[InterviewSessionRead]
InterviewSummaryResponse = ApiResponse[InterviewSummaryRead]
InterviewAnswerResponse = ApiResponse[InterviewAnswerRead]
InterviewHistoryResponse = ApiResponse[InterviewHistoryData]
InterviewQuestionsResponse = ApiResponse[InterviewQuestionsData]
