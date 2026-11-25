"""End-to-End Integration Tests: Register -> Profile -> CV -> AI Analysis -> Roadmap -> Mock Interview -> Dashboard."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pymupdf as fitz
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.models.career import CareerCategory, CareerRole, Skill
from app.models.learning_resource import LearningResource
from app.models.profile_data import CareerRoleSkill
from app.models.user import User
from app.schemas.analysis_ai import AnalysisAIResponse, AnalysisSkillAssessment
from app.schemas.interview.ai_response import (
    InterviewAnswerScoreAI,
    InterviewGenerationAIResponse,
    InterviewQuestionAI,
)
from app.services import (
    analysis_service,
    cv_service,
    interview_service,
    learning_plan_service,
)


def _make_pdf_bytes(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def _seed_catalog(db_session) -> tuple[CareerRole, Skill, Skill, LearningResource]:
    cat = CareerCategory(name="Software Development", slug="software-dev-e2e")
    db_session.add(cat)
    db_session.flush()

    role = CareerRole(
        category_id=cat.id,
        name="Backend Developer",
        slug="backend-dev-e2e",
        level="Junior",
        description="Develop scalable backend APIs",
        is_active=True,
    )
    skill_py = Skill(name="Python", is_active=True)
    skill_sql = Skill(name="SQL", is_active=True)
    db_session.add_all([role, skill_py, skill_sql])
    db_session.flush()

    db_session.add_all(
        [
            CareerRoleSkill(
                career_role_id=role.id,
                skill_id=skill_py.id,
                required_level=4,
                weight=2.0,
                is_required=True,
            ),
            CareerRoleSkill(
                career_role_id=role.id,
                skill_id=skill_sql.id,
                required_level=4,
                weight=1.0,
                is_required=True,
            ),
        ]
    )
    db_session.flush()

    res_sql = LearningResource(
        slug="sql-mastery-e2e",
        skill_id=skill_sql.id,
        title="SQL Optimization Course",
        provider="PostgreSQL Academy",
        url="https://example.com/sql-course",
        resource_type="course",
        description="Learn indexing and query tuning.",
        language="vi",
        is_free=True,
        approval_status="approved",
        is_active=True,
    )
    res_py = LearningResource(
        slug="python-backend-e2e",
        skill_id=skill_py.id,
        title="FastAPI & Python Architecture",
        provider="RealPython",
        url="https://example.com/python-fastapi",
        resource_type="course",
        description="Production API patterns.",
        language="vi",
        is_free=True,
        approval_status="approved",
        is_active=True,
    )
    db_session.add_all([res_sql, res_py])
    db_session.commit()
    return role, skill_py, skill_sql, res_sql


def test_full_user_journey_from_registration_to_mock_interview_and_admin_guard(
    client,
    db_session,
    monkeypatch,
    tmp_path: Path,
):
    """Kiểm thử toàn bộ quy trình khép kín:
    Đăng ký -> Đăng nhập -> Hồ sơ -> Tải CV -> Phân tích AI -> Lộ trình -> Phỏng vấn thử -> Dashboard -> Phân quyền Admin.
    """
    monkeypatch.setattr(cv_service, "UPLOAD_ROOT", tmp_path)
    role, skill_py, skill_sql, res_sql = _seed_catalog(db_session)

    # 1. Đăng ký & Đăng nhập tài khoản học viên
    reg_res = client.post(
        "/api/v1/auth/register",
        json={"email": "journey.student@example.com", "password": "Password123!"},
    )
    assert reg_res.status_code == 201
    student_id = reg_res.json()["data"]["user"]["id"]
    assert reg_res.json()["data"]["user"]["role"] == "student"

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "journey.student@example.com", "password": "Password123!"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["data"]["email"] == "journey.student@example.com"

    # Học viên bị chặn khi gọi API Admin
    assert client.get("/api/v1/admin/stats", headers=headers).status_code == 403
    assert client.get("/api/v1/admin/users", headers=headers).status_code == 403

    # 2. Cập nhật Hồ sơ sinh viên & vị trí mục tiêu
    profile_res = client.put(
        "/api/v1/profile/me",
        headers=headers,
        json={
            "full_name": "Nguyen Van Journey",
            "major": "Software Engineering",
            "university": "HCMUT",
            "target_role_id": role.id,
            "career_goal": "Become a Junior Backend Developer",
        },
    )
    assert profile_res.status_code == 200
    assert profile_res.json()["data"]["target_role_id"] == role.id

    # 3. Tải lên CV PDF
    cv_evidence_py = "Built FastAPI REST services with Python 3.12."
    cv_evidence_sql = "Designed normalized MySQL tables and basic SQL queries."
    pdf_bytes = _make_pdf_bytes(f"{cv_evidence_py}\n{cv_evidence_sql}")
    cv_upload_res = client.post(
        "/api/v1/cvs",
        headers=headers,
        files={"file": ("backend_cv.pdf", pdf_bytes, "application/pdf")},
    )
    assert cv_upload_res.status_code == 201
    cv_id = cv_upload_res.json()["data"]["cv"]["id"]

    cv_detail_res = client.get(f"/api/v1/cvs/{cv_id}", headers=headers)
    assert cv_detail_res.status_code == 200
    assert "FastAPI" in cv_detail_res.json()["data"]["cv"]["extracted_text"]

    # 4. Phân tích khoảng cách kỹ năng bằng AI (có Consent & grounded evidence)
    TestingSessionLocal = sessionmaker(
        bind=db_session.get_bind(), autoflush=False, autocommit=False
    )
    monkeypatch.setattr(analysis_service, "SessionLocal", TestingSessionLocal)

    class FakeAnalysisAI:
        async def generate_structured(self, **kwargs):
            return AnalysisAIResponse(
                skills=[
                    AnalysisSkillAssessment(
                        skill_id=skill_py.id,
                        current_level=4,  # Đạt chuẩn 4/4 (weight 2.0 -> 100%)
                        evidence=cv_evidence_py,
                        recommendation="Duy trì kiến thức Python async.",
                    ),
                    AnalysisSkillAssessment(
                        skill_id=skill_sql.id,
                        current_level=2,  # Thiếu 2/4 (weight 1.0 -> 50%)
                        evidence=cv_evidence_sql,
                        recommendation="Luyện thêm tối ưu truy vấn và indexing SQL.",
                    ),
                ]
            )

    monkeypatch.setattr(analysis_service, "get_ai_service", FakeAnalysisAI)

    analysis_create = client.post(
        "/api/v1/analyses",
        headers=headers,
        json={
            "cv_id": cv_id,
            "career_role_id": role.id,
            "ai_consent": {"accepted": True, "purpose_version": "v1"},
        },
    )
    assert analysis_create.status_code == 202
    analysis_id = analysis_create.json()["data"]["id"]

    status_res = client.get(f"/api/v1/analyses/{analysis_id}/status", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["data"]["status"] == "completed"

    report_res = client.get(f"/api/v1/analyses/{analysis_id}", headers=headers)
    assert report_res.status_code == 200
    report_data = report_res.json()["data"]
    # Readiness = ((2.0 * 1.0 + 1.0 * 0.5) / 3.0) * 100 = 83.3 -> round int = 83
    assert report_data["readiness_score"] == 83

    skills_res = client.get(f"/api/v1/analyses/{analysis_id}/skills", headers=headers)
    assert skills_res.status_code == 200
    assert len(skills_res.json()["data"]) == 2

    # 5. Tạo Lộ trình học tập 30 ngày & Cập nhật tiến độ nhiệm vụ
    class FakePlanSelectorAI:
        async def generate_structured(self, *, prompt, response_schema, system_instruction):
            payload = json.loads(prompt)
            return response_schema.model_validate(
                {
                    "selections": [
                        {
                            "skill_id": task["skill_id"],
                            "week_number": task["week_number"],
                            "resource_id": res_sql.id
                            if task["skill_id"] == skill_sql.id
                            else None,
                        }
                        for task in payload["tasks"]
                    ]
                }
            )

    monkeypatch.setattr(learning_plan_service, "get_ai_service", FakePlanSelectorAI)

    plan_create = client.post(
        "/api/v1/learning-plans",
        headers=headers,
        json={"analysis_id": analysis_id},
    )
    assert plan_create.status_code == 201
    plan_data = plan_create.json()["data"]
    plan_id = plan_data["id"]
    items = plan_data["items"]
    assert len(items) > 0

    # Đánh dấu hoàn thành 1 nhiệm vụ đầu tiên
    first_item_id = items[0]["id"]
    item_patch = client.patch(
        f"/api/v1/learning-plans/{plan_id}/items/{first_item_id}",
        headers=headers,
        json={"is_completed": True},
    )
    assert item_patch.status_code == 200
    assert item_patch.json()["data"]["is_completed"] is True

    # 6. Phỏng vấn thử (Tạo phiên -> Lấy câu hỏi -> Trả lời -> Chấm điểm -> Hoàn thành)
    class FakeInterviewAI:
        async def generate_structured(self, *, prompt, response_schema, system_instruction):
            if response_schema is InterviewGenerationAIResponse:
                return InterviewGenerationAIResponse(
                    questions=[
                        InterviewQuestionAI(
                            question_text=f"E2E Question {i}: Explain backend concept {i}.",
                            competency="Backend Architecture",
                            evaluation_criteria=["Correctness", "Clarity"],
                        )
                        for i in range(1, 4)
                    ]
                )
            if response_schema is InterviewAnswerScoreAI:
                if "E2E Question 1" in prompt:
                    return InterviewAnswerScoreAI(score=Decimal("80.00"), feedback="Trả lời đúng trọng tâm.")
                if "E2E Question 2" in prompt:
                    return InterviewAnswerScoreAI(score=Decimal("90.00"), feedback="Ví dụ thực tế xuất sắc.")
                return InterviewAnswerScoreAI(score=Decimal("85.00"), feedback="Tư duy hệ thống tốt.")
            raise AssertionError(f"Unexpected schema {response_schema}")

    monkeypatch.setattr(interview_service, "get_ai_service", FakeInterviewAI)

    iv_create = client.post(
        "/api/v1/interviews",
        headers=headers,
        json={
            "career_role_id": role.id,
            "ai_consent": {"accepted": True, "purpose_version": "v1"},
        },
    )
    assert iv_create.status_code == 201
    session_id = iv_create.json()["data"]["id"]

    q_res = client.get(f"/api/v1/interviews/{session_id}/questions", headers=headers)
    assert q_res.status_code == 200
    questions = q_res.json()["data"]
    assert len(questions) == 3

    for idx, question in enumerate(questions, start=1):
        ans_res = client.post(
            f"/api/v1/interviews/{session_id}/answers",
            headers=headers,
            json={
                "question_id": question["id"],
                "answer_text": f"My comprehensive answer for question {idx}.",
            },
        )
        assert ans_res.status_code == 201
        assert ans_res.json()["data"]["answered_count"] == idx

    complete_res = client.post(
        f"/api/v1/interviews/{session_id}/complete",
        headers=headers,
    )
    assert complete_res.status_code == 200
    assert complete_res.json()["data"]["status"] == "completed"
    # Average of 80.00, 90.00, 85.00 = 85.00
    assert Decimal(str(complete_res.json()["data"]["total_score"])) == Decimal("85.00")

    # 7. Kiểm tra Dashboard tổng hợp phản ánh toàn bộ kết quả
    summary_res = client.get("/api/v1/dashboard/summary", headers=headers)
    assert summary_res.status_code == 200
    summary = summary_res.json()["data"]
    assert summary["readiness_score"] == 83.0
    assert summary["total_analyses"] == 1
    assert summary["total_interviews"] == 1
    assert summary["active_plan"]["completed_tasks"] == 1

    radar_res = client.get("/api/v1/dashboard/skill-radar", headers=headers)
    assert radar_res.status_code == 200
    assert len(radar_res.json()["data"]["skills"]) == 2

    progress_res = client.get("/api/v1/dashboard/learning-progress", headers=headers)
    assert progress_res.status_code == 200
    assert progress_res.json()["data"]["has_active_plan"] is True
    assert progress_res.json()["data"]["plan"]["completed_tasks"] == 1

    history_res = client.get("/api/v1/dashboard/readiness-history", headers=headers)
    assert history_res.status_code == 200
    assert len(history_res.json()["data"]["points"]) == 1
    assert history_res.json()["data"]["points"][0]["score"] == 83

    iv_hist_res = client.get("/api/v1/dashboard/interview-history", headers=headers)
    assert iv_hist_res.status_code == 200
    assert iv_hist_res.json()["data"]["total"] == 1
    assert float(iv_hist_res.json()["data"]["items"][0]["total_score"]) == 85.0

    # 8. Admin đăng nhập, kiểm tra stats và khóa tài khoản học viên
    admin = User(
        email="e2e.admin@example.com",
        password_hash=hash_password("AdminPass123!"),
        role="admin",
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "e2e.admin@example.com", "password": "AdminPass123!"},
    )
    assert admin_login.status_code == 200
    admin_headers = {
        "Authorization": f"Bearer {admin_login.json()['data']['access_token']}"
    }

    stats_res = client.get("/api/v1/admin/stats", headers=admin_headers)
    assert stats_res.status_code == 200
    assert stats_res.json()["data"]["total_users"] >= 2

    lock_res = client.put(
        f"/api/v1/admin/users/{student_id}/status",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert lock_res.status_code == 200
    assert lock_res.json()["data"]["is_active"] is False

    # Học viên bị khóa không thể đăng nhập hoặc gọi API nữa
    blocked_login = client.post(
        "/api/v1/auth/login",
        json={"email": "journey.student@example.com", "password": "Password123!"},
    )
    assert blocked_login.status_code == 403
    assert client.get("/api/v1/dashboard/summary", headers=headers).status_code == 403
