"""Prompt sinh bộ 3 câu hỏi phỏng vấn thử theo vị trí nghề nghiệp.

Module này chỉ chứa nội dung prompt và hàm dựng prompt; không truy vấn
database và không gọi SDK AI. Nhờ đó prompt được bảo trì độc lập với
Interview Service.
"""

from __future__ import annotations

from dataclasses import dataclass

MOCK_INTERVIEW_SYSTEM_INSTRUCTION = (
    "Bạn là chuyên gia tuyển dụng và phỏng vấn kỹ thuật. "
    "Nhiệm vụ của bạn là tạo câu hỏi phỏng vấn thực tế, rõ ràng và bám sát "
    "vị trí nghề nghiệp cùng danh sách kỹ năng được cung cấp. "
    "Chỉ trả về JSON hợp lệ theo đúng cấu trúc được yêu cầu, không kèm giải thích."
)

INTERVIEW_GRADING_SYSTEM_INSTRUCTION = (
    "Bạn là chuyên gia phỏng vấn kỹ thuật công bằng và khách quan. "
    "Nhiệm vụ của bạn là chấm điểm câu trả lời theo đúng tiêu chí được cung cấp, "
    "đưa phản hồi cải thiện cụ thể và mang tính xây dựng. "
    "Không bịa thông tin, không đánh giá ngoài phạm vi câu hỏi. "
    "Chỉ trả về JSON hợp lệ theo đúng cấu trúc được yêu cầu."
)


@dataclass(frozen=True)
class InterviewSkillContext:
    """Thông tin kỹ năng tối thiểu được đưa vào prompt."""

    name: str
    required_level: int
    is_required: bool


def build_mock_interview_prompt(
    *,
    career_role_name: str,
    career_role_level: str,
    career_role_description: str | None,
    skills: list[InterviewSkillContext],
) -> str:
    """Dựng prompt sinh đúng 3 câu hỏi phỏng vấn cho một vị trí.

    Chỉ dữ liệu catalog công khai được đưa vào prompt; không có thông tin
    người dùng, CV, token hay API Key.
    """
    description = (career_role_description or "Không có mô tả chi tiết.").strip()
    skill_lines = "\n".join(
        f"- {skill.name} (mức yêu cầu {skill.required_level}/5, "
        f"{'bắt buộc' if skill.is_required else 'tham khảo'})"
        for skill in skills
    )

    return f"""Hãy tạo bộ câu hỏi phỏng vấn thử cho vị trí nghề nghiệp dưới đây.

Thông tin vị trí:
- Tên vị trí: {career_role_name}
- Cấp độ: {career_role_level}
- Mô tả: {description}

Danh sách kỹ năng liên quan:
{skill_lines}

Yêu cầu bắt buộc:
1. Sinh chính xác 3 câu hỏi, không thiếu và không thừa.
2. Câu hỏi phải phù hợp với vị trí và cấp độ đã cung cấp.
3. Không lặp lại nội dung hoặc ý chính giữa các câu hỏi.
4. Mỗi câu hỏi phải gắn với một năng lực cụ thể cần đánh giá.
5. Mỗi câu hỏi phải có ít nhất một tiêu chí đánh giá rõ ràng, có thể dùng để chấm điểm.
6. Câu hỏi phải thực tế, phù hợp với buổi phỏng vấn tuyển dụng.
7. Chỉ sử dụng các kỹ năng đã được liệt kê; không tự bịa thêm kỹ năng.
8. Không sinh câu trả lời mẫu, không sinh đáp án.
9. Viết câu hỏi và tiêu chí đánh giá bằng tiếng Việt; giữ nguyên thuật ngữ kỹ thuật tiếng Anh khi cần.
10. Chỉ trả về JSON đúng cấu trúc sau, không thêm trường khác:
{{
  "questions": [
    {{
      "question_text": "Nội dung câu hỏi",
      "competency": "Năng lực được đánh giá",
      "evaluation_criteria": ["Tiêu chí 1", "Tiêu chí 2"]
    }}
  ]
}}
"""


def build_interview_grading_prompt(
    *,
    question_text: str,
    competency: str,
    evaluation_criteria: list[str],
    answer_text: str,
) -> str:
    """Dựng prompt chấm điểm một câu trả lời phỏng vấn.

    Chỉ nội dung câu hỏi, tiêu chí và câu trả lời được gửi đi; không có
    thông tin định danh người dùng hay token.
    """
    criteria_lines = "\n".join(
        f"- {criterion.strip()}" for criterion in evaluation_criteria if criterion.strip()
    )
    return f"""Hãy chấm điểm câu trả lời phỏng vấn dưới đây.

Câu hỏi:
{question_text.strip()}

Năng lực cần đánh giá:
{competency.strip()}

Tiêu chí chấm điểm:
{criteria_lines}

Câu trả lời của sinh viên:
\"\"\"
{answer_text.strip()}
\"\"\"

Yêu cầu bắt buộc:
1. Chấm điểm theo thang 0 đến 100, là số thực có tối đa 2 chữ số thập phân.
2. Điểm phải phản ánh mức đáp ứng các tiêu chí ở trên, không dựa vào độ dài câu trả lời.
3. Phản hồi phải nêu điểm mạnh, điểm còn thiếu và gợi ý cải thiện cụ thể.
4. Không bịa thông tin không có trong câu trả lời.
5. Viết phản hồi bằng tiếng Việt; giữ nguyên thuật ngữ kỹ thuật tiếng Anh khi cần.
6. Chỉ trả về JSON đúng cấu trúc sau, không thêm trường khác:
{{
  "score": 75.5,
  "feedback": "Nhận xét và gợi ý cải thiện"
}}
"""
