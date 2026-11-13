"""Prompt đánh giá mức kỹ năng hiện tại cho báo cáo M4.

Module chỉ dựng nội dung prompt, không truy vấn database và không gọi AI.
Backend giữ quyền quyết định ``gap_score`` và ``readiness_score``; AI chỉ
được phép trả mức hiện tại cùng bằng chứng cho từng kỹ năng.
"""

from __future__ import annotations

from dataclasses import dataclass

SKILL_GAP_SYSTEM_INSTRUCTION = (
    "Bạn là chuyên gia tuyển dụng và đánh giá năng lực kỹ thuật. "
    "Nhiệm vụ của bạn là đối chiếu dữ liệu CV/hồ sơ với danh sách kỹ năng "
    "được cung cấp. Chỉ đánh giá dựa trên bằng chứng thực tế trong dữ liệu; "
    "không suy đoán, không bịa bằng chứng, không tự tính điểm sẵn sàng. "
    "Chỉ trả về JSON hợp lệ theo đúng cấu trúc được yêu cầu."
)

# Giới hạn độ dài văn bản CV gửi AI để tránh vượt hạn mức token và giảm dữ liệu thừa.
MAX_CV_TEXT_CHARS = 12000


@dataclass(frozen=True)
class SkillAnalysisContext:
    """Thông tin tối thiểu của một kỹ năng được đưa vào prompt."""

    skill_id: int
    name: str
    required_level: int
    is_required: bool
    weight: float


def build_profile_summary(
    *,
    major: str | None,
    university: str | None,
    career_goal: str | None,
    bio: str | None,
    strengths: list[str],
    self_assessed_skills: list[tuple[str, int]],
) -> str:
    """Dựng phần mô tả hồ sơ, chỉ gồm dữ liệu cần cho việc đánh giá.

    Không đưa họ tên, email hay token vào prompt.
    """
    lines: list[str] = []
    if major:
        lines.append(f"- Ngành học: {major.strip()}")
    if university:
        lines.append(f"- Trường: {university.strip()}")
    if career_goal:
        lines.append(f"- Mục tiêu nghề nghiệp: {career_goal.strip()}")
    if bio:
        lines.append(f"- Giới thiệu bản thân: {bio.strip()}")
    if strengths:
        lines.append(f"- Điểm mạnh: {', '.join(item.strip() for item in strengths if item.strip())}")
    if self_assessed_skills:
        lines.append(
            "- Kỹ năng tự đánh giá: "
            + ", ".join(f"{name} ({level}/5)" for name, level in self_assessed_skills)
        )
    return "\n".join(lines) or "Không có dữ liệu hồ sơ khai báo."


def build_skill_gap_prompt(
    *,
    career_role_name: str,
    career_role_level: str,
    career_role_description: str | None,
    skills: list[SkillAnalysisContext],
    cv_text: str | None,
    profile_summary: str,
) -> str:
    """Dựng prompt đánh giá mức kỹ năng hiện tại cho từng kỹ năng."""
    description = (career_role_description or "Không có mô tả chi tiết.").strip()
    skill_lines = "\n".join(
        f"- skill_id={skill.skill_id} | {skill.name} | mức yêu cầu "
        f"{skill.required_level}/5 | trọng số {skill.weight:g} | "
        f"{'bắt buộc' if skill.is_required else 'tham khảo'}"
        for skill in skills
    )

    cv_content = (cv_text or "").strip()
    if len(cv_content) > MAX_CV_TEXT_CHARS:
        cv_content = cv_content[:MAX_CV_TEXT_CHARS] + "\n...[nội dung CV đã được rút gọn]"
    if not cv_content:
        cv_content = "Không có CV. Chỉ sử dụng dữ liệu hồ sơ khai báo bên dưới."

    return f"""Hãy đánh giá mức kỹ năng hiện tại của sinh viên cho từng kỹ năng dưới đây.

Thông tin vị trí mục tiêu:
- Tên vị trí: {career_role_name}
- Cấp độ: {career_role_level}
- Mô tả: {description}

Danh sách kỹ năng cần đánh giá:
{skill_lines}

Dữ liệu hồ sơ khai báo:
{profile_summary}

Nội dung CV (nếu có):
\"\"\"
{cv_content}
\"\"\"

Yêu cầu bắt buộc:
1. Trả đúng một đánh giá cho mỗi skill_id trong danh sách; không thêm, không bớt, không trùng skill_id.
2. current_level là số nguyên từ 0 đến 5, phản ánh mức hiện tại dựa trên bằng chứng.
3. Chỉ dùng bằng chứng xuất hiện trong CV hoặc hồ sơ. Nếu không tìm thấy bằng chứng cho một kỹ năng, đặt has_evidence=false và current_level=0.
4. Khi has_evidence=true, trích ngắn gọn bằng chứng cụ thể vào trường evidence.
5. recommendation là gợi ý cải thiện ngắn gọn, thực tế; có thể null nếu kỹ năng đã đạt yêu cầu.
6. Không tính gap_score, không tính điểm sẵn sàng, không bịa điểm số ngoài thang 0-5.
7. Viết nhận xét và gợi ý bằng tiếng Việt; giữ nguyên thuật ngữ kỹ thuật tiếng Anh khi cần.
8. Chỉ trả về JSON đúng cấu trúc sau, không thêm trường khác:
{{
  "summary": "Nhận xét tổng quan ngắn gọn",
  "assessments": [
    {{
      "skill_id": 1,
      "current_level": 3,
      "has_evidence": true,
      "evidence": "Bằng chứng trích từ CV/hồ sơ",
      "recommendation": "Gợi ý cải thiện"
    }}
  ]
}}
"""
