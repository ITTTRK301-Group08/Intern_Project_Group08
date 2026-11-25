import pymupdf as fitz

from app.models.analysis import Analysis, AnalysisSkillGap
from app.models.career import CareerRole, Skill
from app.models.cv import CV
from app.models.profile_data import CareerRoleSkill, ProfileSkill
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.schemas.analysis_ai import AnalysisAIResponse, AnalysisSkillAssessment
from app.services import analysis_service
from app.services.ai import AIRateLimitError


def register_and_login(client, email: str = "consent@example.com", password: str = "StrongPass123"):
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert reg.status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def make_pdf_bytes(text: str = "Consent CV content") -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def create_cv(client, headers, name: str = "cv.pdf") -> int:
    pdf = make_pdf_bytes()
    res = client.post("/api/v1/cvs", headers=headers, files={"file": (name, pdf, "application/pdf")})
    assert res.status_code == 201
    return res.json()["data"]["cv"]["id"]


def create_role(db_session, slug: str = "analysis-role") -> tuple[int, int]:
    skill = Skill(name="Python")
    role = CareerRole(name="Analysis Role", slug=slug, level="Junior")
    db_session.add_all([skill, role])
    db_session.flush()
    db_session.add(
        CareerRoleSkill(
            career_role_id=role.id,
            skill_id=skill.id,
            required_level=4,
            is_required=True,
        )
    )
    db_session.commit()
    return role.id, skill.id


def valid_payload(cv_id=None, career_role_id=None, accepted=True, purpose_version="v1"):
    payload = {
        "ai_consent": {"accepted": accepted, "purpose_version": purpose_version},
    }
    if cv_id is not None:
        payload["cv_id"] = cv_id
    if career_role_id is not None:
        payload["career_role_id"] = career_role_id
    return payload


def _install_ai_spy(monkeypatch):
    calls = []

    class SpyService:
        async def generate_structured(self, **kwargs):
            calls.append(kwargs)
            raise AssertionError("AI provider should not be called for rejected requests")

    def spy():
        return SpyService()

    monkeypatch.setattr(analysis_service, "get_ai_service", spy)
    return calls


def _install_ai_result(monkeypatch, db_session, skill_id: int, evidence: str):
    calls = []

    class FakeAIService:
        async def generate_structured(self, **kwargs):
            calls.append(kwargs)
            return AnalysisAIResponse(
                skills=[
                    AnalysisSkillAssessment(
                        skill_id=skill_id,
                        current_level=3,
                        evidence=evidence,
                        recommendation="Thực hành thêm với dự án nhỏ.",
                    )
                ]
            )

    monkeypatch.setattr(analysis_service, "get_ai_service", FakeAIService)
    monkeypatch.setattr(analysis_service, "SessionLocal", lambda: db_session)
    return calls


def _install_profile_ai_result(monkeypatch, db_session, skill_id: int):
    calls = []

    class FakeAIService:
        async def generate_structured(self, **kwargs):
            calls.append(kwargs)
            return AnalysisAIResponse(
                skills=[
                    AnalysisSkillAssessment(
                        skill_id=skill_id,
                        current_level=0,
                        evidence=None,
                        recommendation="Duy trì và bổ sung ví dụ dự án.",
                    )
                ]
            )

    monkeypatch.setattr(analysis_service, "get_ai_service", FakeAIService)
    monkeypatch.setattr(analysis_service, "SessionLocal", lambda: db_session)
    return calls


def test_requires_jwt(client, monkeypatch):
    calls = _install_ai_spy(monkeypatch)
    res = client.post("/api/v1/analyses", json=valid_payload())
    assert res.status_code == 401
    assert calls == []


def test_invalid_token_rejected(client, monkeypatch):
    calls = _install_ai_spy(monkeypatch)
    res = client.post(
        "/api/v1/analyses",
        headers={"Authorization": "Bearer invalid"},
        json=valid_payload(),
    )
    assert res.status_code == 401
    assert calls == []


def test_missing_consent_rejected(client, monkeypatch):
    headers = register_and_login(client)
    calls = _install_ai_spy(monkeypatch)
    res = client.post("/api/v1/analyses", headers=headers, json={"cv_id": 1})
    assert res.status_code == 422
    assert calls == []


def test_consent_not_accepted_rejected(client, monkeypatch):
    headers = register_and_login(client)
    calls = _install_ai_spy(monkeypatch)
    res = client.post("/api/v1/analyses", headers=headers, json=valid_payload(accepted=False))
    assert res.status_code == 403
    body = res.json()
    assert body["detail"]["data"]["code"] == "AI_CONSENT_REQUIRED"
    assert calls == []


def test_consent_version_mismatch_rejected(client, monkeypatch):
    headers = register_and_login(client)
    calls = _install_ai_spy(monkeypatch)
    res = client.post(
        "/api/v1/analyses",
        headers=headers,
        json=valid_payload(purpose_version="v999"),
    )
    assert res.status_code == 422
    body = res.json()
    assert body["detail"]["data"]["code"] == "AI_CONSENT_VERSION_UNSUPPORTED"
    assert calls == []


def test_cannot_access_other_users_cv(client, monkeypatch):
    headers_a = register_and_login(client, "a_consent@example.com")
    headers_b = register_and_login(client, "b_consent@example.com")
    cv_id_a = create_cv(client, headers_a, "a.pdf")
    calls = _install_ai_spy(monkeypatch)
    res = client.post("/api/v1/analyses", headers=headers_b, json=valid_payload(cv_id=cv_id_a))
    assert res.status_code == 403
    assert res.json()["detail"]["data"]["code"] == "CV_FORBIDDEN"
    assert calls == []


def test_cv_not_found_rejected(client, monkeypatch):
    headers = register_and_login(client)
    calls = _install_ai_spy(monkeypatch)
    res = client.post("/api/v1/analyses", headers=headers, json=valid_payload(cv_id=999999))
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
    res = client.post("/api/v1/analyses", headers=headers, json=valid_payload(cv_id=cv_id))
    assert res.status_code == 404
    assert res.json()["detail"]["data"]["code"] == "CV_NOT_FOUND"
    assert calls == []


def test_valid_consent_creates_report_and_runs_analysis(client, db_session, monkeypatch):
    headers = register_and_login(client)
    cv_id = create_cv(client, headers)
    role_id, skill_id = create_role(db_session)
    calls = _install_ai_result(monkeypatch, db_session, skill_id, "Consent CV content")
    res = client.post(
        "/api/v1/analyses",
        headers=headers,
        json=valid_payload(cv_id=cv_id, career_role_id=role_id),
    )
    assert res.status_code == 202
    response_data = res.json()["data"]
    assert response_data["status"] == "pending"
    analysis = db_session.query(Analysis).filter_by(id=response_data["id"]).one()
    first_analysis_id = analysis.id
    assert analysis.status == "completed"
    assert analysis.readiness_score == 75
    assert analysis.completed_at is not None
    gap = db_session.query(AnalysisSkillGap).filter_by(analysis_id=first_analysis_id).one()
    assert gap.skill_id == skill_id
    assert gap.current_level == 3
    assert gap.target_level == 4
    assert gap.evidence == "Consent CV content"
    assert calls and "Consent CV content" in calls[0]["prompt"]

    second_response = client.post(
        "/api/v1/analyses",
        headers=headers,
        json=valid_payload(cv_id=cv_id, career_role_id=role_id),
    )
    assert second_response.status_code == 202
    assert second_response.json()["data"]["id"] != first_analysis_id
    history = client.get("/api/v1/analyses", headers=headers)
    assert history.json()["data"]["total"] == 2

def test_analysis_completes_with_fallback_when_ai_is_rate_limited(
    client, db_session, monkeypatch
):
    headers = register_and_login(client, "rate_limited@example.com")
    cv_id = create_cv(client, headers)
    role_id, skill_id = create_role(db_session, "rate-limit-role")

    class RateLimitedAIService:
        async def generate_structured(self, **kwargs):
            raise AIRateLimitError("quota exhausted")

    monkeypatch.setattr(analysis_service, "get_ai_service", RateLimitedAIService)
    monkeypatch.setattr(analysis_service, "SessionLocal", lambda: db_session)

    response = client.post(
        "/api/v1/analyses",
        headers=headers,
        json=valid_payload(cv_id=cv_id, career_role_id=role_id),
    )
    assert response.status_code == 202
    analysis_id = response.json()["data"]["id"]
    analysis = db_session.query(Analysis).filter_by(id=analysis_id).one()
    assert analysis.status == "completed"
    assert analysis.completed_at is not None

    gap = db_session.query(AnalysisSkillGap).filter_by(analysis_id=analysis_id).one()
    assert gap.skill_id == skill_id
    assert gap.current_level == 0
    assert gap.has_evidence is False
    assert gap.evidence is None


def test_profile_analysis_uses_self_assessment_and_preserves_overqualified_score(
    client, db_session, monkeypatch
):
    headers = register_and_login(client, "profile_analysis@example.com")
    user_id = db_session.query(User).filter_by(email="profile_analysis@example.com").one().id
    role_id, skill_id = create_role(db_session, "profile-analysis-role")
    profile = StudentProfile(user_id=user_id, full_name="Test Student", bio="Backend projects")
    db_session.add(profile)
    db_session.flush()
    db_session.add(ProfileSkill(profile_id=profile.id, skill_id=skill_id, level=5))
    db_session.commit()
    calls = _install_profile_ai_result(monkeypatch, db_session, skill_id)

    response = client.post(
        "/api/v1/analyses",
        headers=headers,
        json=valid_payload(career_role_id=role_id),
    )
    assert response.status_code == 202
    analysis = db_session.query(Analysis).filter_by(id=response.json()["data"]["id"]).one()
    gap = db_session.query(AnalysisSkillGap).filter_by(analysis_id=analysis.id).one()
    assert analysis.status == "completed"
    assert analysis.readiness_score == 100
    assert gap.current_level == 5
    assert gap.target_level == 4
    assert gap.evidence == "Mức tự đánh giá trong hồ sơ: 5/5"
    assert calls


def test_unverifiable_ai_skill_evidence_fails_without_saving_a_score(
    client, db_session, monkeypatch
):
    headers = register_and_login(client, "ungrounded_analysis@example.com")
    cv_id = create_cv(client, headers)
    role_id, skill_id = create_role(db_session, "ungrounded-analysis-role")
    calls = _install_ai_result(monkeypatch, db_session, skill_id, "Not present in the CV")

    response = client.post(
        "/api/v1/analyses",
        headers=headers,
        json=valid_payload(cv_id=cv_id, career_role_id=role_id),
    )
    assert response.status_code == 202
    analysis = db_session.query(Analysis).filter_by(id=response.json()["data"]["id"]).one()
    assert analysis.status == "failed"
    assert analysis.readiness_score is None
    assert db_session.query(AnalysisSkillGap).filter_by(analysis_id=analysis.id).count() == 0
    assert calls


def test_consent_check_runs_before_ownership(client, monkeypatch):
    headers_a = register_and_login(client, "owner_a@example.com")
    headers_b = register_and_login(client, "owner_b@example.com")
    cv_id_a = create_cv(client, headers_a, "owner.pdf")
    calls = _install_ai_spy(monkeypatch)

    ownership_called = {"value": False}

    def ownership_spy(*args, **kwargs):
        ownership_called["value"] = True
        return original(*args, **kwargs)

    original = analysis_service.get_owned_active_cv
    monkeypatch.setattr(analysis_service, "get_owned_active_cv", ownership_spy)

    res = client.post(
        "/api/v1/analyses",
        headers=headers_b,
        json=valid_payload(cv_id=cv_id_a, accepted=False),
    )
    assert res.status_code == 403
    assert res.json()["detail"]["data"]["code"] == "AI_CONSENT_REQUIRED"
    assert ownership_called["value"] is False
    assert calls == []


def test_extra_consent_fields_rejected(client, monkeypatch):
    headers = register_and_login(client)
    calls = _install_ai_spy(monkeypatch)
    payload = valid_payload()
    payload["ai_consent"]["unexpected"] = "x"
    res = client.post("/api/v1/analyses", headers=headers, json=payload)
    assert res.status_code == 422
    assert calls == []
