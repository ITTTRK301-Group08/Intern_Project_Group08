<<<<<<< HEAD
import logging
=======
"""Test cổng consent và quyền sở hữu của nghiệp vụ phân tích (M4).

Các test ở đây chỉ kiểm tra những trường hợp bị từ chối trước khi tác vụ AI
được đăng ký. Luồng xử lý nền thành công được kiểm tra riêng trong
``test_analysis_pipeline.py``.
"""

import fitz
>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1

from sqlalchemy import event, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.analysis import Analysis, AnalysisSkillGap
from app.models.career import CareerRole, Skill
from app.models.cv import CV
<<<<<<< HEAD
from app.models.profile_data import CareerRoleSkill, ProfileSkill
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.services import ai_service, analysis_service
=======
from app.services import analysis_service
>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1


def register_and_login(
    client, email: str = "consent@example.com", password: str = "StrongPass123"
):
<<<<<<< HEAD
    reg = client.post(
        "/api/v1/auth/register", json={"email": email, "password": password}
    )
=======
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": password})
>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1
    assert reg.status_code == 201
    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert login.status_code == 200
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def valid_payload(
    cv_id=None, career_role_id=1, accepted=True, purpose_version="v1"
):
    payload = {
        "ai_consent": {"accepted": accepted, "purpose_version": purpose_version},
    }
    if cv_id is not None:
        payload["cv_id"] = cv_id
    if career_role_id is not None:
        payload["career_role_id"] = career_role_id
    return payload


<<<<<<< HEAD
def create_target_role(db_session, *, with_skills=True):
    python = Skill(name="Python")
    sql = Skill(name="SQL")
    role = CareerRole(
        name="Backend Developer",
        slug="backend-developer-test",
        level="Junior",
        is_active=True,
    )
    db_session.add_all([python, sql, role])
    db_session.flush()
    if with_skills:
        db_session.add_all(
            [
                CareerRoleSkill(
                    career_role_id=role.id,
                    skill_id=python.id,
                    required_level=4,
                    is_required=True,
                    weight=1.5,
                ),
                CareerRoleSkill(
                    career_role_id=role.id,
                    skill_id=sql.id,
                    required_level=2,
                    is_required=True,
                    weight=1,
                ),
            ]
        )
    db_session.commit()
    return role.id, {"Python": python.id, "SQL": sql.id}


def create_profile(db_session, email, skill_levels=None, *, bio=None):
    user = db_session.scalar(select(User).where(User.email == email))
    profile = StudentProfile(user_id=user.id, full_name="Test Student", bio=bio)
    db_session.add(profile)
    db_session.flush()
    for skill_name, level in (skill_levels or {}).items():
        skill = db_session.scalar(select(Skill).where(Skill.name == skill_name))
        db_session.add(
            ProfileSkill(profile_id=profile.id, skill_id=skill.id, level=level)
        )
    db_session.commit()
    return profile.id


def create_cv(db_session, email, text):
    user = db_session.scalar(select(User).where(User.email == email))
    cv = CV(
        user_id=user.id,
        file_name="test.pdf",
        file_path="test.pdf",
        mime_type="application/pdf",
        file_size=100,
        extracted_text=text,
        is_active=True,
    )
    db_session.add(cv)
    db_session.commit()
    return cv.id


def use_test_background_sessions(db_session, monkeypatch):
    factory = sessionmaker(
        bind=db_session.get_bind(),
        autoflush=False,
        expire_on_commit=False,
    )
    monkeypatch.setattr(analysis_service, "SessionLocal", factory)


def install_ai_spy(monkeypatch):
=======
def _install_ai_spy(monkeypatch):
    """Ghi nhận và báo lỗi nếu lớp AI bị gọi khi yêu cầu đã bị từ chối."""
>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1
    calls = []

    def spy(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
<<<<<<< HEAD
        raise AssertionError("Local skill analysis must not call an AI provider")
=======
        raise AssertionError("AI provider must not be called when a gate rejects")
>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1

    monkeypatch.setattr(analysis_service, "get_ai_service", spy)
    return calls


def test_requires_jwt(client, monkeypatch):
<<<<<<< HEAD
    calls = install_ai_spy(monkeypatch)
    response = client.post("/api/v1/analyses", json=valid_payload())
    assert response.status_code == 401
=======
    calls = _install_ai_spy(monkeypatch)
    res = client.post("/api/v1/analyses", json=valid_payload(career_role_id=1))
    assert res.status_code == 401
>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1
    assert calls == []


def test_invalid_token_rejected(client, monkeypatch):
    calls = install_ai_spy(monkeypatch)
    response = client.post(
        "/api/v1/analyses",
        headers={"Authorization": "Bearer invalid"},
        json=valid_payload(career_role_id=1),
    )
    assert response.status_code == 401
    assert calls == []


def test_target_role_is_required(client):
    headers = register_and_login(client)
    payload = valid_payload()
    del payload["career_role_id"]
    response = client.post("/api/v1/analyses", headers=headers, json=payload)
    assert response.status_code == 422
    assert response.json()["success"] is False


def test_missing_consent_rejected(client, monkeypatch):
    headers = register_and_login(client)
<<<<<<< HEAD
    calls = install_ai_spy(monkeypatch)
    response = client.post("/api/v1/analyses", headers=headers, json={"career_role_id": 1})
    assert response.status_code == 422
=======
    calls = _install_ai_spy(monkeypatch)
    res = client.post(
        "/api/v1/analyses",
        headers=headers,
        json={"cv_id": 1, "career_role_id": 1},
    )
    assert res.status_code == 422
    assert calls == []


def test_missing_career_role_rejected(client, monkeypatch):
    headers = register_and_login(client)
    calls = _install_ai_spy(monkeypatch)
    res = client.post(
        "/api/v1/analyses",
        headers=headers,
        json={"ai_consent": {"accepted": True, "purpose_version": "v1"}},
    )
    assert res.status_code == 422
>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1
    assert calls == []


def test_consent_not_accepted_rejected(client, monkeypatch):
    headers = register_and_login(client)
<<<<<<< HEAD
    calls = install_ai_spy(monkeypatch)
    response = client.post(
        "/api/v1/analyses",
        headers=headers,
        json=valid_payload(accepted=False),
    )
    assert response.status_code == 403
    assert response.json()["detail"]["data"]["code"] == "AI_CONSENT_REQUIRED"
=======
    calls = _install_ai_spy(monkeypatch)
    res = client.post(
        "/api/v1/analyses",
        headers=headers,
        json=valid_payload(career_role_id=1, accepted=False),
    )
    assert res.status_code == 403
    body = res.json()
    assert body["detail"]["data"]["code"] == "AI_CONSENT_REQUIRED"
>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1
    assert calls == []


def test_consent_version_mismatch_rejected(client, monkeypatch):
    headers = register_and_login(client)
    calls = install_ai_spy(monkeypatch)
    response = client.post(
        "/api/v1/analyses",
        headers=headers,
        json=valid_payload(career_role_id=1, purpose_version="v999"),
    )
    assert response.status_code == 422
    assert response.json()["detail"]["data"]["code"] == "AI_CONSENT_VERSION_UNSUPPORTED"
    assert calls == []


def test_cannot_access_other_users_cv(client, db_session, monkeypatch):
    headers_a = register_and_login(client, "a_consent@example.com")
    headers_b = register_and_login(client, "b_consent@example.com")
<<<<<<< HEAD
    role_id, _ = create_target_role(db_session)
    cv_id = create_cv(db_session, "a_consent@example.com", "Python SQL")
    calls = install_ai_spy(monkeypatch)
    response = client.post(
        "/api/v1/analyses",
        headers=headers_b,
        json=valid_payload(cv_id=cv_id, career_role_id=role_id),
    )
    assert response.status_code == 403
    assert response.json()["detail"]["data"]["code"] == "CV_FORBIDDEN"
=======
    cv_id_a = create_cv(client, headers_a, "a.pdf")
    calls = _install_ai_spy(monkeypatch)
    res = client.post(
        "/api/v1/analyses",
        headers=headers_b,
        json=valid_payload(cv_id=cv_id_a, career_role_id=1),
    )
    assert res.status_code == 403
    assert res.json()["detail"]["data"]["code"] == "CV_FORBIDDEN"
>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1
    assert calls == []
    assert db_session.query(Analysis).count() == 0


def test_cv_not_found_rejected(client):
    headers = register_and_login(client)
<<<<<<< HEAD
    response = client.post(
        "/api/v1/analyses",
        headers=headers,
        json=valid_payload(cv_id=999999, career_role_id=1),
    )
    assert response.status_code == 404
    assert response.json()["detail"]["data"]["code"] == "CV_NOT_FOUND"


def test_cv_without_extractable_text_is_rejected(client, db_session):
    headers = register_and_login(client, "empty_cv@example.com")
    role_id, _ = create_target_role(db_session)
    cv_id = create_cv(db_session, "empty_cv@example.com", "")
    response = client.post(
        "/api/v1/analyses",
        headers=headers,
        json=valid_payload(cv_id=cv_id, career_role_id=role_id),
    )
    assert response.status_code == 422
    assert response.json()["detail"]["data"]["code"] == "CV_NO_EXTRACTABLE_TEXT"


def test_inactive_cv_rejected(client, db_session):
    headers = register_and_login(client, "inactive_cv@example.com")
    role_id, _ = create_target_role(db_session)
    cv_id = create_cv(db_session, "inactive_cv@example.com", "Python SQL")
    cv = db_session.get(CV, cv_id)
    cv.is_active = False
    db_session.commit()
    response = client.post(
        "/api/v1/analyses",
        headers=headers,
        json=valid_payload(cv_id=cv_id, career_role_id=role_id),
    )
    assert response.status_code == 404
    assert response.json()["detail"]["data"]["code"] == "CV_NOT_FOUND"


def test_role_not_found_and_role_without_skills_rejected(client, db_session):
    headers = register_and_login(client)
    nonexistent = client.post(
        "/api/v1/analyses",
        headers=headers,
        json=valid_payload(career_role_id=999999),
    )
    assert nonexistent.status_code == 404
    assert nonexistent.json()["detail"]["data"]["code"] == "CAREER_ROLE_NOT_FOUND"

    role_id, _ = create_target_role(db_session, with_skills=False)
    empty_role = client.post(
        "/api/v1/analyses",
        headers=headers,
        json=valid_payload(career_role_id=role_id),
    )
    assert empty_role.status_code == 422
    assert empty_role.json()["detail"]["data"]["code"] == "CAREER_ROLE_HAS_NO_SKILLS"


def test_requires_cv_or_profile(client, db_session):
    headers = register_and_login(client, "no_source@example.com")
    role_id, _ = create_target_role(db_session)
    response = client.post(
        "/api/v1/analyses",
        headers=headers,
        json=valid_payload(career_role_id=role_id),
    )
    assert response.status_code == 422
    assert response.json()["detail"]["data"]["code"] == "ANALYSIS_SOURCE_REQUIRED"


def test_analysis_is_accepted_and_persists_weighted_profile_and_cv_result(
    client, db_session, monkeypatch
):
    headers = register_and_login(client, "combined@example.com")
    role_id, skill_ids = create_target_role(db_session)
    create_profile(
        db_session,
        "combined@example.com",
        {"Python": 3},
    )
    cv_id = create_cv(db_session, "combined@example.com", "Experienced with SQL.")
    use_test_background_sessions(db_session, monkeypatch)
    calls = install_ai_spy(monkeypatch)

    accepted = client.post(
        "/api/v1/analyses",
        headers=headers,
        json=valid_payload(cv_id=cv_id, career_role_id=role_id),
    )
    assert accepted.status_code == 202
    accepted_data = accepted.json()["data"]
    assert accepted_data["status"] == "pending"
    assert accepted_data["status_url"] == f"/api/v1/analyses/{accepted_data['id']}"
=======
    calls = _install_ai_spy(monkeypatch)
    res = client.post(
        "/api/v1/analyses",
        headers=headers,
        json=valid_payload(cv_id=999999, career_role_id=1),
    )
    assert res.status_code == 404
    assert res.json()["detail"]["data"]["code"] == "CV_NOT_FOUND"
    assert calls == []


def test_inactive_cv_rejected(client, db_session, monkeypatch):
    headers = register_and_login(client, "inactive_cv@example.com")
    cv_id = create_cv(client, headers, "inactive.pdf")
    cv = db_session.query(CV).filter_by(id=cv_id).first()
    cv.is_active = False
    db_session.commit()
    calls = _install_ai_spy(monkeypatch)
    res = client.post(
        "/api/v1/analyses",
        headers=headers,
        json=valid_payload(cv_id=cv_id, career_role_id=1),
    )
    assert res.status_code == 404
    assert res.json()["detail"]["data"]["code"] == "CV_NOT_FOUND"
>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1
    assert calls == []

    result_response = client.get(accepted_data["status_url"], headers=headers)
    assert result_response.status_code == 200
    result = result_response.json()["data"]
    assert result["status"] == "completed"
    assert result["source_type"] == "cv_and_profile"
    assert result["readiness_score"] == 69
    assert result["completed_at"] is not None
    assert "69/100" in result["summary"]
    gaps = {gap["skill_name"]: gap for gap in result["skill_gaps"]}
    assert gaps["Python"]["current_level"] == 3
    assert gaps["Python"]["target_level"] == 4
    assert gaps["Python"]["gap"] == 1
    assert gaps["Python"]["weight"] == 1.5
    assert gaps["SQL"]["current_level"] == 1
    assert gaps["SQL"]["target_level"] == 2
    assert gaps["SQL"]["gap"] == 1

    saved = db_session.get(Analysis, accepted_data["id"])
    assert saved.status == "completed"
    assert saved.readiness_score == 69
    assert len(saved.skill_gaps) == 2
    assert {gap.skill_id for gap in saved.skill_gaps} == set(skill_ids.values())


def test_cv_only_analysis_counts_skill_mentions_as_level_one(
    client, db_session, monkeypatch
):
    headers = register_and_login(client, "cv_only@example.com")
    role_id, _ = create_target_role(db_session)
    cv_id = create_cv(db_session, "cv_only@example.com", "Built small projects with Python.")
    use_test_background_sessions(db_session, monkeypatch)

    accepted = client.post(
        "/api/v1/analyses",
        headers=headers,
        json=valid_payload(cv_id=cv_id, career_role_id=role_id),
    )
    assert accepted.status_code == 202
    result = client.get(accepted.json()["data"]["status_url"], headers=headers).json()["data"]
    gaps = {gap["skill_name"]: gap for gap in result["skill_gaps"]}
    assert result["source_type"] == "cv"
    assert gaps["Python"]["current_level"] == 1
    assert gaps["SQL"]["current_level"] == 0
    assert result["readiness_score"] == 19


def test_current_level_above_target_is_preserved_in_result(
    client, db_session, monkeypatch
):
    headers = register_and_login(client, "overqualified@example.com")
    role_id, _ = create_target_role(db_session)
    create_profile(db_session, "overqualified@example.com", {"Python": 5})
    use_test_background_sessions(db_session, monkeypatch)

    accepted = client.post(
        "/api/v1/analyses",
        headers=headers,
        json=valid_payload(career_role_id=role_id),
    )
    result = client.get(
        accepted.json()["data"]["status_url"], headers=headers
    ).json()["data"]
    python_gap = next(
        item for item in result["skill_gaps"] if item["skill_name"] == "Python"
    )
    assert result["readiness_score"] == 75
    assert python_gap["current_level"] == 5
    assert python_gap["target_level"] == 4
    assert python_gap["gap"] == 0


def test_analysis_result_is_private_to_its_owner(client, db_session, monkeypatch):
    owner_headers = register_and_login(client, "owner@example.com")
    other_headers = register_and_login(client, "other@example.com")
    role_id, _ = create_target_role(db_session)
    create_profile(db_session, "owner@example.com", {"Python": 2})
    use_test_background_sessions(db_session, monkeypatch)
    accepted = client.post(
        "/api/v1/analyses",
        headers=owner_headers,
        json=valid_payload(career_role_id=role_id),
    )
    analysis_id = accepted.json()["data"]["id"]

    forbidden = client.get(
        f"/api/v1/analyses/{analysis_id}", headers=other_headers
    )
    assert forbidden.status_code == 404
    own_result = client.get(
        f"/api/v1/analyses/{analysis_id}", headers=owner_headers
    )
    assert own_result.status_code == 200
    assert own_result.json()["data"]["status"] == "completed"


def test_failed_background_analysis_does_not_save_partial_results(
    client, db_session, monkeypatch, caplog
):
    headers = register_and_login(client, "failed@example.com")
    role_id, _ = create_target_role(db_session)
    create_profile(db_session, "failed@example.com", {"Python": 3})
    use_test_background_sessions(db_session, monkeypatch)

    def fail_calculation(*args, **kwargs):
        raise RuntimeError("calculation failure")

    monkeypatch.setattr(analysis_service, "calculate_readiness", fail_calculation)
    with caplog.at_level(logging.ERROR):
        accepted = client.post(
            "/api/v1/analyses",
            headers=headers,
            json=valid_payload(career_role_id=role_id),
        )
    assert accepted.status_code == 202
    analysis_id = accepted.json()["data"]["id"]
    result = client.get(f"/api/v1/analyses/{analysis_id}", headers=headers).json()["data"]
    assert result["status"] == "failed"
    assert result["readiness_score"] is None
    assert result["skill_gaps"] == []
    assert "calculation failure" in caplog.text


def test_result_and_skill_gaps_roll_back_together_on_commit_failure(
    client, db_session, monkeypatch, caplog
):
    headers = register_and_login(client, "transaction@example.com")
    role_id, _ = create_target_role(db_session)
    create_profile(db_session, "transaction@example.com", {"Python": 3})
    use_test_background_sessions(db_session, monkeypatch)
    def reject_gap_commit(session):
        if any(isinstance(item, AnalysisSkillGap) for item in session.new):
            raise RuntimeError("forced result commit failure")

    event.listen(Session, "before_commit", reject_gap_commit)
    try:
        with caplog.at_level(logging.ERROR):
            accepted = client.post(
                "/api/v1/analyses",
                headers=headers,
                json=valid_payload(career_role_id=role_id),
            )
    finally:
        event.remove(Session, "before_commit", reject_gap_commit)

    assert accepted.status_code == 202
    analysis_id = accepted.json()["data"]["id"]
    result = client.get(
        f"/api/v1/analyses/{analysis_id}", headers=headers
    ).json()["data"]
    assert result["status"] == "failed"
    assert result["readiness_score"] is None
    assert result["skill_gaps"] == []
    saved = db_session.get(Analysis, analysis_id)
    assert saved.status == "failed"
    assert saved.readiness_score is None
    assert db_session.query(AnalysisSkillGap).filter_by(analysis_id=analysis_id).count() == 0
    assert "forced result commit failure" in caplog.text


def test_consent_check_runs_before_cv_ownership(client, db_session, monkeypatch):
    headers_a = register_and_login(client, "owner_a@example.com")
    headers_b = register_and_login(client, "owner_b@example.com")
    role_id, _ = create_target_role(db_session)
    cv_id = create_cv(db_session, "owner_a@example.com", "Python SQL")
    calls = install_ai_spy(monkeypatch)
    ownership_called = {"value": False}
    original = analysis_service.get_owned_active_cv

    def ownership_spy(*args, **kwargs):
        ownership_called["value"] = True
        return original(*args, **kwargs)

    monkeypatch.setattr(analysis_service, "get_owned_active_cv", ownership_spy)
    response = client.post(
        "/api/v1/analyses",
        headers=headers_b,
<<<<<<< HEAD
        json=valid_payload(cv_id=cv_id, career_role_id=role_id, accepted=False),
=======
        json=valid_payload(cv_id=cv_id_a, career_role_id=1, accepted=False),
>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1
    )
    assert response.status_code == 403
    assert response.json()["detail"]["data"]["code"] == "AI_CONSENT_REQUIRED"
    assert ownership_called["value"] is False
    assert calls == []


def test_extra_consent_fields_rejected(client, monkeypatch):
    headers = register_and_login(client)
<<<<<<< HEAD
    calls = install_ai_spy(monkeypatch)
    payload = valid_payload()
=======
    calls = _install_ai_spy(monkeypatch)
    payload = valid_payload(career_role_id=1)
>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1
    payload["ai_consent"]["unexpected"] = "x"
    response = client.post("/api/v1/analyses", headers=headers, json=payload)
    assert response.status_code == 422
    assert calls == []
