from datetime import datetime

import pytest

from app.models.analysis import Analysis, AnalysisSkillGap
from app.models.career import CareerCategory, CareerRole, Skill
from app.models.interview import InterviewQuestion, InterviewSession
from app.models.learning_plan import LearningPlan, LearningPlanItem
from app.models.profile_data import CareerRoleSkill


def register_user(client, email: str, password: str = "StrongPass123!") -> tuple[dict, int]:
    res = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert res.status_code == 201
    user_id = res.json()["data"]["user"]["id"]
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}, user_id


def setup_dashboard_fixture(db_session, user_id: int):
    # 1. Tạo Category, Role, Skills
    cat = CareerCategory(name="AI & Data", slug="ai-data", description="Dữ liệu và Trí tuệ nhân tạo")
    db_session.add(cat)
    db_session.flush()

    role = CareerRole(
        name="Data Analyst",
        slug="data-analyst",
        level="Junior",
        category_id=cat.id,
        description="Chuyên viên phân tích dữ liệu",
    )
    db_session.add(role)
    db_session.flush()

    skill_sql = Skill(name="SQL", description="Truy vấn dữ liệu")
    skill_viz = Skill(name="Data Visualization", description="Trực quan hóa dữ liệu")
    db_session.add_all([skill_sql, skill_viz])
    db_session.flush()

    # Trọng số kỹ năng: SQL (weight 2.0, req 4), Viz (weight 1.0, req 4)
    crs_sql = CareerRoleSkill(career_role_id=role.id, skill_id=skill_sql.id, required_level=4, weight=2.0)
    crs_viz = CareerRoleSkill(career_role_id=role.id, skill_id=skill_viz.id, required_level=4, weight=1.0)
    db_session.add_all([crs_sql, crs_viz])
    db_session.flush()

    # 2. Phân tích hoàn thành: SQL: current=2/4 (50%), Viz: current=4/4 (100%)
    # Điểm chuẩn: [ (2.0 * 0.5 + 1.0 * 1.0) / (2.0 + 1.0) ] * 100 = (2.0 / 3.0) * 100 = 66.7%
    analysis = Analysis(
        user_id=user_id,
        career_role_id=role.id,
        consent_accepted=True,
        consent_purpose_version="v1",
        status="completed",
        summary="Phân tích năng lực Data Analyst",
        completed_at=datetime.utcnow(),
    )
    db_session.add(analysis)
    db_session.flush()

    gap_sql = AnalysisSkillGap(
        analysis_id=analysis.id,
        skill_id=skill_sql.id,
        current_level=2,
        target_level=4,
    )
    gap_viz = AnalysisSkillGap(
        analysis_id=analysis.id,
        skill_id=skill_viz.id,
        current_level=4,
        target_level=4,
    )
    db_session.add_all([gap_sql, gap_viz])
    db_session.flush()

    # 3. Phiên phỏng vấn thử
    session = InterviewSession(
        user_id=user_id,
        career_role_id=role.id,
        status="completed",
    )
    db_session.add(session)
    db_session.flush()

    q1 = InterviewQuestion(
        session_id=session.id,
        question_text="Bạn tối ưu câu lệnh SQL JOIN như thế nào?",
        competency="SQL Optimization",
        evaluation_criteria=["Index usage", "Explain plan"],
        question_order=1,
    )
    db_session.add(q1)
    db_session.flush()

    # 4. Lộ trình học tập đang active
    plan = LearningPlan(
        user_id=user_id,
        analysis_id=analysis.id,
        title="Lộ trình Data Analyst 30 ngày",
        start_date=datetime.utcnow().date(),
        end_date=datetime.utcnow().date(),
        status="active",
    )
    db_session.add(plan)
    db_session.flush()

    it1 = LearningPlanItem(
        plan_id=plan.id,
        skill_id=skill_sql.id,
        week_number=1,
        task_description="Học cú pháp SQL Window Functions",
        is_completed=True,
        completed_at=datetime.utcnow(),
    )
    it2 = LearningPlanItem(
        plan_id=plan.id,
        skill_id=skill_viz.id,
        week_number=2,
        task_description="Tạo dashboard trên PowerBI",
        is_completed=False,
    )
    db_session.add_all([it1, it2])
    db_session.commit()

    return {
        "analysis": analysis,
        "role": role,
        "skills": [skill_sql, skill_viz],
        "session": session,
        "plan": plan,
    }


def test_dashboard_summary_unauthorized(client):
    res = client.get("/api/v1/dashboard/summary")
    assert res.status_code == 401


def test_dashboard_summary_empty(client, db_session):
    headers, _ = register_user(client, "empty_user@example.com")
    res = client.get("/api/v1/dashboard/summary", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["readiness_score"] == 0.0
    assert data["total_analyses"] == 0
    assert data["total_interviews"] == 0
    assert data["active_plan"] is None


def test_dashboard_summary_with_data(client, db_session):
    headers, user_id = register_user(client, "dash_user@example.com")
    fixtures = setup_dashboard_fixture(db_session, user_id)

    res = client.get("/api/v1/dashboard/summary", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]

    # Kiểm tra điểm sẵn sàng nghề nghiệp theo công thức SRS
    assert data["readiness_score"] == 66.7
    assert data["target_role"] == "Data Analyst"
    assert data["target_role_level"] == "Junior"
    assert data["total_analyses"] == 1
    assert data["total_interviews"] == 1
    assert data["total_skills_evaluated"] == 2
    assert data["skills_matched_count"] == 1  # Viz 4/4
    assert data["skills_gap_count"] == 1      # SQL 2/4

    # Kiểm tra lộ trình đang hoạt động
    active_plan = data["active_plan"]
    assert active_plan is not None
    assert active_plan["title"] == "Lộ trình Data Analyst 30 ngày"
    assert active_plan["total_tasks"] == 2
    assert active_plan["completed_tasks"] == 1
    assert active_plan["progress_percent"] == 50.0


def test_skill_radar_endpoint(client, db_session):
    headers, user_id = register_user(client, "radar_user@example.com")
    setup_dashboard_fixture(db_session, user_id)

    res = client.get("/api/v1/dashboard/skill-radar", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["role_name"] == "Data Analyst"
    assert data["overall_readiness"] == 66.7
    assert len(data["skills"]) == 2

    # Tìm skill SQL
    sql_item = next(s for s in data["skills"] if s["skill_name"] == "SQL")
    assert sql_item["current_level"] == 2
    assert sql_item["required_level"] == 4
    assert sql_item["gap_score"] == 2
    assert sql_item["is_gap"] is True

    # Tìm skill Data Visualization
    viz_item = next(s for s in data["skills"] if s["skill_name"] == "Data Visualization")
    assert viz_item["current_level"] == 4
    assert viz_item["required_level"] == 4
    assert viz_item["gap_score"] == 0
    assert viz_item["is_gap"] is False


def test_learning_progress_endpoint(client, db_session):
    headers, user_id = register_user(client, "prog_user@example.com")
    setup_dashboard_fixture(db_session, user_id)

    res = client.get("/api/v1/dashboard/learning-progress", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["has_active_plan"] is True
    assert data["plan"]["progress_percent"] == 50.0
    breakdown = data["weekly_breakdown"]
    assert len(breakdown) == 4

    w1 = next(b for b in breakdown if b["week_number"] == 1)
    assert w1["total_tasks"] == 1
    assert w1["completed_tasks"] == 1
    assert w1["progress_percent"] == 100.0

    w2 = next(b for b in breakdown if b["week_number"] == 2)
    assert w2["total_tasks"] == 1
    assert w2["completed_tasks"] == 0
    assert w2["progress_percent"] == 0.0


def test_interview_history_endpoint(client, db_session):
    headers, user_id = register_user(client, "interview_user@example.com")
    setup_dashboard_fixture(db_session, user_id)

    res = client.get("/api/v1/dashboard/interview-history", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["career_role_name"] == "Data Analyst"
    assert item["status"] == "completed"
    assert item["question_count"] == 1
