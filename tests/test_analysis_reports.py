from sqlalchemy import select

from app.models.analysis import Analysis, AnalysisSkillGap
from app.models.career import CareerRole, Skill
from app.models.user import User


def register_and_login(client, email: str):
    registration = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "StrongPass123"},
    )
    assert registration.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


def make_analysis(db_session, *, user_id: int, role_id: int, status: str):
    analysis = Analysis(
        user_id=user_id,
        career_role_id=role_id,
        consent_accepted=True,
        consent_purpose_version="v1",
        status=status,
        readiness_score=85 if status == "completed" else None,
        summary="Tổng quan kỹ năng",
    )
    db_session.add(analysis)
    db_session.flush()
    return analysis


def test_history_report_skills_status_and_owner_filter(client, db_session):
    headers_a = register_and_login(client, "reports-a@example.com")
    headers_b = register_and_login(client, "reports-b@example.com")
    user_a = db_session.scalar(select(User).where(User.email == "reports-a@example.com"))
    user_b = db_session.scalar(select(User).where(User.email == "reports-b@example.com"))

    role = CareerRole(name="Backend Developer", slug="backend-developer")
    python_skill = Skill(name="Python")
    sql_skill = Skill(name="SQL")
    db_session.add_all([role, python_skill, sql_skill])
    db_session.flush()

    completed = make_analysis(
        db_session, user_id=user_a.id, role_id=role.id, status="completed"
    )
    db_session.add_all(
        [
            AnalysisSkillGap(
                analysis_id=completed.id,
                skill_id=python_skill.id,
                current_level=3,
                target_level=5,
                evidence="Built a REST API using Python.",
                has_evidence=True,
                recommendation="Practice asynchronous APIs.",
            ),
            AnalysisSkillGap(
                analysis_id=completed.id,
                skill_id=sql_skill.id,
                current_level=0,
                target_level=3,
                evidence=None,
                has_evidence=False,
            ),
        ]
    )
    processing = make_analysis(
        db_session, user_id=user_a.id, role_id=role.id, status="processing"
    )
    other_user_analysis = make_analysis(
        db_session, user_id=user_b.id, role_id=role.id, status="pending"
    )
    db_session.commit()

    history = client.get(
        "/api/v1/analyses?page=1&page_size=1", headers=headers_a
    )
    assert history.status_code == 200
    assert history.json()["success"] is True
    assert history.json()["data"]["total"] == 2
    assert history.json()["data"]["items"][0]["id"] == processing.id
    assert history.json()["data"]["pages"] == 2

    status_response = client.get(
        f"/api/v1/analyses/{processing.id}/status", headers=headers_a
    )
    assert status_response.status_code == 200
    assert status_response.json()["data"]["status"] == "processing"

    report = client.get(f"/api/v1/analyses/{completed.id}", headers=headers_a)
    assert report.status_code == 200
    assert report.json()["data"]["readiness_score"] == 85
    assert report.json()["data"]["career_role_name"] == "Backend Developer"

    skills = client.get(
        f"/api/v1/analyses/{completed.id}/skills", headers=headers_a
    )
    assert skills.status_code == 200
    skill_data = {item["skill_name"]: item for item in skills.json()["data"]}
    assert skill_data["Python"]["gap_score"] == 2
    assert skill_data["Python"]["has_evidence"] is True
    assert skill_data["Python"]["evidence"] == "Built a REST API using Python."
    assert skill_data["SQL"]["current_level"] == 0
    assert skill_data["SQL"]["has_evidence"] is False

    forbidden_report = client.get(
        f"/api/v1/analyses/{other_user_analysis.id}", headers=headers_a
    )
    forbidden_status = client.get(
        f"/api/v1/analyses/{other_user_analysis.id}/status", headers=headers_a
    )
    assert forbidden_report.status_code == 404
    assert forbidden_status.status_code == 404


def test_analysis_history_requires_authentication(client):
    response = client.get("/api/v1/analyses")
    assert response.status_code == 401
