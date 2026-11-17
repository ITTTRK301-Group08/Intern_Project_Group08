"""Schema phản hồi phiên phỏng vấn thử và kết quả chấm điểm."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.auth import ApiResponse


class InterviewCareerRoleRead(BaseModel):
    """Thông tin tối thiểu của vị trí nghề nghiệp trong phiên phỏng vấn."""

    id: int
    name: str
    level: str

    model_config = ConfigDict(from_attributes=True)


class InterviewAnswerRead(BaseModel):
    """Câu trả lời đã lưu cùng điểm và nhận xét của AI."""

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
    """Phiên phỏng vấn đã được tạo cùng đúng 3 câu hỏi."""

    id: int
    status: str
    career_role: InterviewCareerRoleRead | None
    questions: list[InterviewQuestionRead]
    total_score: float | None = None
    completed_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterviewSessionSummaryRead(BaseModel):
    """Một phiên phỏng vấn trong danh sách lịch sử."""

    id: int
    career_role_id: int | None = None
    career_role_name: str | None = None
    status: str
    question_count: int = 0
    answered_count: int = 0
    total_score: float | None = None
    created_at: datetime
    completed_at: datetime | None = None


class InterviewSessionListData(BaseModel):
    """Danh sách phiên phỏng vấn có phân trang."""

    items: list[InterviewSessionSummaryRead] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 10
    total_pages: int = 1


class InterviewAnswerResultRead(BaseModel):
    """Kết quả sau khi lưu câu trả lời và điểm AI."""

    answer: InterviewAnswerRead
    session_status: str
    question_count: int
    answered_count: int


class InterviewCompletionRead(BaseModel):
    """Kết quả hoàn thành phiên phỏng vấn."""

    id: int
    status: str
    total_score: float
    completed_at: datetime
    question_count: int
    answered_count: int


InterviewSessionResponse = ApiResponse[InterviewSessionRead]
InterviewSessionDetailResponse = ApiResponse[InterviewSessionRead]
InterviewSessionListResponse = ApiResponse[InterviewSessionListData]
InterviewQuestionsResponse = ApiResponse[list[InterviewQuestionRead]]
InterviewAnswerResultResponse = ApiResponse[InterviewAnswerResultRead]
InterviewCompletionResponse = ApiResponse[InterviewCompletionRead]
