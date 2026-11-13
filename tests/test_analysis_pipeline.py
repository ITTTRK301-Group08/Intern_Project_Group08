"""Integration test cho pipeline phân tích kỹ năng chạy nền của M4.

Test dùng SQLite in-memory, database test được chia sẻ cho tác vụ nền qua
``analysis_service._session_factory`` và provider AI giả; không gọi Gemini.
"""

import json
from datetime import date

import pytest
from sqlalchemy.orm import sessionmaker

from app.models.analysis import Analysis, AnalysisSkillGap
from app.models.career import CareerRole, Skill
from app.models.profile_data import CareerRoleSkill
from app.services import analysis_service
from app.services.ai import AIService, AITimeoutError, BaseAIProvider


class FakeProvider(BaseAIProvider):
    """Provider giả trả về lần lượt kết quả hoặc exception đã định trước."""

    name = "fake"

    def __init__(self, outcomes):
        self._outcomes = list(outcomes)
        self.calls = 0
        self.last_prompt = None

    async def generate(self, *, prompt, response_schema=None, system_instruction=None):
        self.calls += 1
        self.last_prompt = prompt
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def register_and_login(
    client,
    email: str = "pipeline@example.com",
    password: str = "StrongPass123",
) -> tuple[dict[str, str], int]:
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert reg.status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}, reg.json()["data"]["user"]["id"]


def seed_role(db_session, skills: list[tuple[str, int, float]]):
    """Tạo vị trí cùng danh sách kỹ năng ``(tên, mức yêu cầu, trọng số)``."""
    role = CareerRole(
        name="Backend Developer",
        slug="backend-developer",
        level="Intern",
        description="Mô tả vị trí Backend Developer",
        is_active=True,
    )
    db_session.add(role)
    db_session.flush()

    skill_ids: list[int] = []
    for name, required_level, weight in skills:
        skill = Skill(name=name)
        db_session.add(skill)
        db_session.flush()
        db_session.add(
            CareerRoleSkill(
                career_role_id=role.id,
                skill_id=skill.id,
                required_level=required_level,
                is_required=True,
                weight=weight,
            )
        )
        skill_ids.append(skill.id)

    db_session.commit()
    return role.id, skill_ids


def analysis_payload(role_id: int, cv_id: int | None = None) -> dict:
    payload = {
        "career_role_id": role_id,
        "ai_consent": {"accepted": True, "purpose_version": "v1"},
    }
    if cv_id is not None:
        payload["cv_id"] = cv_id
    return payload


def ai_response(
    summary: str,
    assessments: list[dict],
) -> str:
    return json.dumps(
        {"summary": summary, "assessments": assessments},
        ensure_ascii=False,
    )


def use_test_database(monkeypatch, db_session) -> None:
    """Cho tác vụ nền dùng đúng database SQLite in-memory của test."""
    engine = db_session.get_bind()
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(analysis_service, "_session_factory", factory)


def install_fake_ai(monkeypatch, *outcomes) -> FakeProvider:
    provider = FakeProvider(outcomes)
    service = AIService(provider, max_retries=0)
    monkeypatch.setattr(analysis_service, "get_ai_service", lambda: service)
    return provider


def load_analysis(db_session, analysis_id: int) -> Analysis:
    """Đọc lại báo cáo từ database, bỏ qua identity map cũ của test."""
    db_session.expire_all()
    analysis = db_session.get(Analysis, analysis_id)
    assert analysis is not None
    return analysis


def test_pipeline_completes_and_computes_scores(client, db_session, monkeypatch):
    headers, user_id = register_and_login(client)
    role_id, skill_ids = seed_role(
        db_session,
        [("Python", 4, 1.0), ("SQL", 2, 1.0)],
    )
    use_test_database(monkeypatch, db_session)
    provider = install_fake_ai(
        monkeypatch,
        ai_response(
            "Đã đối chiếu CV với vị trí mục tiêu.",
            [
                {
                    "skill_id": skill_ids[0],
                    "current_level": 2,
                    "has_evidence": True,
                    "evidence": "Đã dùng Python trong đồ án.",
                    "recommendation": "Luyện thêm kiến trúc backend.",
                },
                {
                    "skill_id": skill_ids[1],
                    "current_level": 3,
                    "has_evidence": True,
                    "evidence": "Đã dùng SQL cho đồ án.",
                    "recommendation": None,
                },
            ],
        ),
    )

    response = client.post(
        "/api/v1/analyses",
        headers=headers,
        json=analysis_payload(role_id),
    )

    assert response.status_code == 202
    body = response.json()
    assert body["success"] is True
    created = body["data"]
    assert created["id"] > 0
    # Response được serialize trước khi tác vụ nền chạy.
    assert created["status"] == "processing"
    analysis_id = created["id"]

    analysis = load_analysis(db_session, analysis_id)
    assert analysis.user_id == user_id
    assert analysis.career_role_id == role_id
    assert analysis.status == "completed"
    assert analysis.failure_reason is None
    assert analysis.market_source == analysis_service.MARKET_SOURCE
    assert analysis.benchmark_date == date.today()
    assert analysis.completed_at is not None
    # (1.0 * 2/4 + 1.0 * min(3/2, 1)) / 2 * 100 = 75.0
    assert float(analysis.readiness_score) == pytest.approx(75.0)

    gaps = (
        db_session.query(AnalysisSkillGap)
        .filter_by(analysis_id=analysis_id)
        .order_by(AnalysisSkillGap.skill_id)
        .all()
    )
    assert len(gaps) == 2
    by_skill = {gap.skill_id: gap for gap in gaps}
    assert by_skill[skill_ids[0]].current_level == 2
    assert by_skill[skill_ids[0]].required_level == 4
    assert float(by_skill[skill_ids[0]].gap_score) == pytest.approx(2.0)
    assert by_skill[skill_ids[0]].has_evidence is True
    assert by_skill[skill_ids[0]].evidence == "Đã dùng Python trong đồ án."
    assert float(by_skill[skill_ids[1]].gap_score) == pytest.approx(0.0)

    assert provider.calls == 1
    assert "Backend Developer" in provider.last_prompt


def test_pipeline_forces_zero_for_skill_without_evidence(
    client, db_session, monkeypatch
):
    headers, _ = register_and_login(client, "noevidence@example.com")
    role_id, skill_ids = seed_role(
        db_session,
        [("Python", 4, 1.0), ("SQL", 4, 3.0)],
    )
    use_test_database(monkeypatch, db_session)
    install_fake_ai(
        monkeypatch,
        ai_response(
            "Thiếu bằng chứng cho một kỹ năng.",
            [
                {
                    "skill_id": skill_ids[0],
                    "current_level": 5,
                    "has_evidence": False,
                    "evidence": "Không có bằng chứng.",
                    "recommendation": "Bổ sung dự án thực tế.",
                },
                {
                    "skill_id": skill_ids[1],
                    "current_level": 2,
                    "has_evidence": True,
                    "evidence": "Có dự án SQL.",
                    "recommendation": None,
                },
            ],
        ),
    )

    response = client.post(
        "/api/v1/analyses", headers=headers, json=analysis_payload(role_id)
    )
    assert response.status_code == 202

    analysis = load_analysis(db_session, response.json()["data"]["id"])
    assert analysis.status == "completed"

    gaps = {
        gap.skill_id: gap
        for gap in db_session.query(AnalysisSkillGap)
        .filter_by(analysis_id=analysis.id)
        .all()
    }
    # Kỹ năng không có bằng chứng bị buộc current_level = 0.
    assert gaps[skill_ids[0]].current_level == 0
    assert gaps[skill_ids[0]].has_evidence is False
    assert float(gaps[skill_ids[0]].gap_score) == pytest.approx(4.0)

    # (1.0 * 0 + 3.0 * 0.5) / 4 * 100 = 37.5
    assert float(analysis.readiness_score) == pytest.approx(37.5)


def test_required_level_zero_counts_as_fully_ready(client, db_session, monkeypatch):
    headers, _ = register_and_login(client, "zerorequired@example.com")
    role_id, skill_ids = seed_role(db_session, [("Git", 0, 1.0)])
    use_test_database(monkeypatch, db_session)
    install_fake_ai(
        monkeypatch,
        ai_response(
            "Kỹ năng không bắt buộc ở mức cao.",
            [
                {
                    "skill_id": skill_ids[0],
                    "current_level": 0,
                    "has_evidence": False,
                    "evidence": None,
                    "recommendation": None,
                }
            ],
        ),
    )

    response = client.post(
        "/api/v1/analyses", headers=headers, json=analysis_payload(role_id)
    )
    assert response.status_code == 202

    analysis = load_analysis(db_session, response.json()["data"]["id"])
    assert analysis.status == "completed"
    assert float(analysis.readiness_score) == pytest.approx(100.0)


def test_invalid_ai_assessment_set_marks_failed_without_partial_results(
    client, db_session, monkeypatch
):
    headers, _ = register_and_login(client, "invalidai@example.com")
    role_id, skill_ids = seed_role(
        db_session,
        [("Python", 4, 1.0), ("SQL", 3, 1.0)],
    )
    use_test_database(monkeypatch, db_session)
    install_fake_ai(
        monkeypatch,
        ai_response(
            "Thiếu đánh giá.",
            [
                {
                    "skill_id": skill_ids[0],
                    "current_level": 3,
                    "has_evidence": True,
                    "evidence": "Có bằng chứng.",
                    "recommendation": None,
                }
            ],
        ),
    )

    response = client.post(
        "/api/v1/analyses", headers=headers, json=analysis_payload(role_id)
    )
    assert response.status_code == 202

    analysis = load_analysis(db_session, response.json()["data"]["id"])
    assert analysis.status == "failed"
    assert analysis.failure_reason == analysis_service.INVALID_AI_RESULT
    assert analysis.readiness_score is None
    assert (
        db_session.query(AnalysisSkillGap).filter_by(analysis_id=analysis.id).count()
        == 0
    )


def test_ai_timeout_marks_failed_safely(client, db_session, monkeypatch):
    headers, _ = register_and_login(client, "timeout@example.com")
    role_id, _ = seed_role(db_session, [("Python", 4, 1.0)])
    use_test_database(monkeypatch, db_session)
    install_fake_ai(monkeypatch, AITimeoutError("timeout"))

    response = client.post(
        "/api/v1/analyses", headers=headers, json=analysis_payload(role_id)
    )
    assert response.status_code == 202

    analysis = load_analysis(db_session, response.json()["data"]["id"])
    assert analysis.status == "failed"
    assert analysis.failure_reason == "AI_TIMEOUT"


def test_history_detail_status_and_skills_endpoints(
    client, db_session, monkeypatch
):
    headers, _ = register_and_login(client, "endpoints@example.com")
    role_id, skill_ids = seed_role(db_session, [("Python", 4, 1.0)])
    use_test_database(monkeypatch, db_session)
    install_fake_ai(
        monkeypatch,
        ai_response(
            "Hoàn tất.",
            [
                {
                    "skill_id": skill_ids[0],
                    "current_level": 2,
                    "has_evidence": True,
                    "evidence": "Có bằng chứng.",
                    "recommendation": "Luyện thêm.",
                }
            ],
        ),
    )

    created = client.post(
        "/api/v1/analyses", headers=headers, json=analysis_payload(role_id)
    )
    analysis_id = created.json()["data"]["id"]

    history = client.get("/api/v1/analyses", headers=headers)
    assert history.status_code == 200
    history_data = history.json()["data"]
    assert history_data["total"] == 1
    assert history_data["analyses"][0]["id"] == analysis_id

    detail = client.get(f"/api/v1/analyses/{analysis_id}", headers=headers)
    assert detail.status_code == 200
    assert len(detail.json()["data"]["skill_gaps"]) == 1

    status_res = client.get(f"/api/v1/analyses/{analysis_id}/status", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["data"]["status"] == "completed"

    skills = client.get(f"/api/v1/analyses/{analysis_id}/skills", headers=headers)
    assert skills.status_code == 200
    skills_data = skills.json()["data"]
    assert skills_data["analysis_id"] == analysis_id
    assert len(skills_data["skills"]) == 1


def test_other_user_cannot_read_analysis(client, db_session, monkeypatch):
    owner_headers, _ = register_and_login(client, "owner_pipeline@example.com")
    other_headers, _ = register_and_login(client, "other_pipeline@example.com")
    role_id, skill_ids = seed_role(db_session, [("Python", 4, 1.0)])
    use_test_database(monkeypatch, db_session)
    install_fake_ai(
        monkeypatch,
        ai_response(
            "Hoàn tất.",
            [
                {
                    "skill_id": skill_ids[0],
                    "current_level": 2,
                    "has_evidence": True,
                    "evidence": "Có bằng chứng.",
                    "recommendation": None,
                }
            ],
        ),
    )

    created = client.post(
        "/api/v1/analyses", headers=owner_headers, json=analysis_payload(role_id)
    )
    analysis_id = created.json()["data"]["id"]

    for path in (
        f"/api/v1/analyses/{analysis_id}",
        f"/api/v1/analyses/{analysis_id}/status",
        f"/api/v1/analyses/{analysis_id}/skills",
    ):
        response = client.get(path, headers=other_headers)
        assert response.status_code == 404

    other_history = client.get("/api/v1/analyses", headers=other_headers)
    assert other_history.status_code == 200
    assert other_history.json()["data"]["total"] == 0


def test_career_role_not_found_rejected(client, db_session, monkeypatch):
    headers, _ = register_and_login(client, "norole@example.com")
    calls = install_fake_ai(monkeypatch, ai_response("Không gọi.", []))

    response = client.post(
        "/api/v1/analyses", headers=headers, json=analysis_payload(999999)
    )
    assert response.status_code == 404
    assert response.json()["detail"]["data"]["code"] == "ANALYSIS_CAREER_ROLE_NOT_FOUND"
    assert calls.calls == 0


def test_inactive_career_role_rejected(client, db_session, monkeypatch):
    headers, _ = register_and_login(client, "inactiverole@example.com")
    role = CareerRole(
        name="Old Role",
        slug="old-role",
        level="Intern",
        is_active=False,
    )
    db_session.add(role)
    db_session.commit()
    calls = install_fake_ai(monkeypatch, ai_response("Không gọi.", []))

    response = client.post(
        "/api/v1/analyses", headers=headers, json=analysis_payload(role.id)
    )
    assert response.status_code == 409
    assert response.json()["detail"]["data"]["code"] == "ANALYSIS_CAREER_ROLE_INACTIVE"
    assert calls.calls == 0


def test_career_role_without_skills_rejected(client, db_session, monkeypatch):
    headers, _ = register_and_login(client, "noskills@example.com")
    role_id, _ = seed_role(db_session, [])
    calls = install_fake_ai(monkeypatch, ai_response("Không gọi.", []))

    response = client.post(
        "/api/v1/analyses", headers=headers, json=analysis_payload(role_id)
    )
    assert response.status_code == 422
    assert response.json()["detail"]["data"]["code"] == "ANALYSIS_ROLE_SKILLS_REQUIRED"
    assert calls.calls == 0
