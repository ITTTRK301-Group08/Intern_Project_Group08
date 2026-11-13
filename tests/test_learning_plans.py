from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.models.analysis import Analysis, AnalysisSkillGap
from app.models.career import CareerCategory, CareerRole, Skill
from app.models.learning_plan import LearningPlan, LearningPlanItem
from app.models.learning_resource import LearningResource
from app.models.profile_data import CareerRoleSkill
from app.models.user import User


def register_user(client, email: str, password: str = "StrongPass123!") -> tuple[dict, int]:
    res = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert res.status_code == 201
    user_id = res.json()["data"]["user"]["id"]
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}, user_id


def setup_catalog_and_analysis(db_session, user_id: int, status: str = "completed") -> Analysis:
    # 1. Tạo Category và Role
    cat = CareerCategory(name="Phần mềm", slug="software", description="Ngành phát triển phần mềm")
    db_session.add(cat)
    db_session.flush()

    role = CareerRole(
        name="Backend Developer",
        slug="backend-dev",
        level="Junior",
        category_id=cat.id,
        description="Lập trình viên backend",
    )
    db_session.add(role)
    db_session.flush()

    # 2. Tạo kỹ năng
    skill_py = Skill(name="Python", description="Ngôn ngữ Python")
    skill_sql = Skill(name="SQL", description="Cơ sở dữ liệu quan hệ")
    db_session.add_all([skill_py, skill_sql])
    db_session.flush()

    # 3. Yêu cầu kỹ năng cho Role
    crs_py = CareerRoleSkill(career_role_id=role.id, skill_id=skill_py.id, required_level=4, weight=1.5)
    crs_sql = CareerRoleSkill(career_role_id=role.id, skill_id=skill_sql.id, required_level=3, weight=1.0)
    db_session.add_all([crs_py, crs_sql])
    db_session.flush()

    # 4. Tài nguyên học tập
    res_py = LearningResource(
        slug="python-official-doc",
        skill_id=skill_py.id,
        title="Tài liệu Python cơ bản",
        provider="Python Docs",
        url="https://docs.python.org/3/",
        resource_type="documentation",
        language="vi",
        is_free=True,
    )
    res_sql = LearningResource(
        slug="sql-bolt-practice",
        skill_id=skill_sql.id,
        title="Thực hành SQL Bolt",
        provider="SQLBolt",
        url="https://sqlbolt.com/",
        resource_type="practice",
        language="en",
        is_free=True,
    )
    db_session.add_all([res_py, res_sql])
    db_session.flush()

    # 5. Phân tích hoàn thành
    analysis = Analysis(
        user_id=user_id,
        career_role_id=role.id,
        consent_accepted=True,
        consent_purpose_version="v1",
        status=status,
        summary="Đánh giá kỹ năng backend developer",
        completed_at=datetime.now(timezone.utc) if status == "completed" else None,
    )
    db_session.add(analysis)
    db_session.flush()

    # 6. Gaps
    gap_py = AnalysisSkillGap(
        analysis_id=analysis.id,
        skill_id=skill_py.id,
        current_level=2,
        target_level=4,
        recommendation="Học thêm nâng cao Python",
    )
    gap_sql = AnalysisSkillGap(
        analysis_id=analysis.id,
        skill_id=skill_sql.id,
        current_level=1,
        target_level=3,
        recommendation="Luyện tập truy vấn SQL",
    )
    db_session.add_all([gap_py, gap_sql])
    db_session.commit()
    db_session.refresh(analysis)
    return analysis


def test_create_plan_unauthorized(client):
    res = client.post("/api/v1/learning-plans", json={"analysis_id": 1})
    assert res.status_code == 401


def test_create_plan_analysis_not_found(client, db_session):
    headers, _ = register_user(client, "user_not_found@example.com")
    res = client.post("/api/v1/learning-plans", json={"analysis_id": 99999}, headers=headers)
    assert res.status_code == 404
    assert res.json()["success"] is False
    assert res.json()["detail"]["data"]["code"] == "ANALYSIS_NOT_FOUND"


def test_create_plan_analysis_forbidden(client, db_session):
    headers_alice, alice_id = register_user(client, "alice@example.com")
    headers_bob, _ = register_user(client, "bob@example.com")
    analysis = setup_catalog_and_analysis(db_session, user_id=alice_id)

    # Bob cố gắng tạo lộ trình từ báo cáo của Alice
    res = client.post("/api/v1/learning-plans", json={"analysis_id": analysis.id}, headers=headers_bob)
    assert res.status_code == 403
    assert res.json()["detail"]["data"]["code"] == "ANALYSIS_FORBIDDEN"


def test_create_plan_analysis_not_completed(client, db_session):
    headers, user_id = register_user(client, "pending_user@example.com")
    analysis = setup_catalog_and_analysis(db_session, user_id=user_id, status="pending")

    res = client.post("/api/v1/learning-plans", json={"analysis_id": analysis.id}, headers=headers)
    assert res.status_code == 400
    assert res.json()["detail"]["data"]["code"] == "ANALYSIS_NOT_COMPLETED"


def test_create_plan_success_and_br06_enforcement(client, db_session):
    headers, user_id = register_user(client, "plan_user@example.com")
    analysis = setup_catalog_and_analysis(db_session, user_id=user_id, status="completed")

    # 1. Tạo lộ trình 30 ngày thành công
    payload = {
        "analysis_id": analysis.id,
        "title": "Lộ trình 30 ngày Backend của Tôi",
        "duration_days": 30,
    }
    res = client.post("/api/v1/learning-plans", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["title"] == "Lộ trình 30 ngày Backend của Tôi"
    assert data["status"] == "active"
    assert data["total_items"] > 0
    assert data["completed_items"] == 0
    assert data["progress_percent"] == 0.0

    # Kiểm tra nhiệm vụ phân bổ qua các tuần (1 -> 4)
    weeks_present = {item["week_number"] for item in data["items"]}
    assert 1 in weeks_present
    assert 2 in weeks_present
    assert 3 in weeks_present
    assert 4 in weeks_present

    # Kiểm tra tài nguyên thực tế được gắn vào mục
    items_with_resource = [it for it in data["items"] if it["resource_id"] is not None]
    assert len(items_with_resource) > 0
    first_res = items_with_resource[0]["resource"]
    assert first_res["url"].startswith("http")

    plan_id = data["id"]

    # 2. Quy tắc BR-06: Không được tạo thêm plan active thứ 2 từ cùng analysis
    res_dup = client.post("/api/v1/learning-plans", json=payload, headers=headers)
    assert res_dup.status_code == 400
    assert res_dup.json()["detail"]["data"]["code"] == "ACTIVE_PLAN_EXISTS"

    # 3. Lấy danh sách lộ trình
    res_list = client.get("/api/v1/learning-plans", headers=headers)
    assert res_list.status_code == 200
    plans = res_list.json()["data"]
    assert len(plans) == 1
    assert plans[0]["id"] == plan_id

    # 4. Lấy chi tiết lộ trình
    res_detail = client.get(f"/api/v1/learning-plans/{plan_id}", headers=headers)
    assert res_detail.status_code == 200
    assert len(res_detail.json()["data"]["items"]) == data["total_items"]

    # 5. Cập nhật hoàn thành 1 nhiệm vụ
    item_to_complete = data["items"][0]
    res_item = client.patch(
        f"/api/v1/learning-plans/{plan_id}/items/{item_to_complete['id']}",
        json={"is_completed": True},
        headers=headers,
    )
    assert res_item.status_code == 200
    assert res_item.json()["data"]["is_completed"] is True
    assert res_item.json()["data"]["completed_at"] is not None

    # Kiểm tra tiến độ tổng thể đã tăng
    res_check = client.get(f"/api/v1/learning-plans/{plan_id}", headers=headers)
    assert res_check.json()["data"]["completed_items"] == 1
    assert res_check.json()["data"]["progress_percent"] > 0

    # 6. Chuyển trạng thái sang archived
    res_status = client.patch(
        f"/api/v1/learning-plans/{plan_id}/status",
        json={"status": "archived"},
        headers=headers,
    )
    assert res_status.status_code == 200
    assert res_status.json()["data"]["status"] == "archived"

    # Sau khi lưu trữ, có thể tạo lộ trình active mới cho cùng analysis
    res_new = client.post("/api/v1/learning-plans", json=payload, headers=headers)
    assert res_new.status_code == 201
    assert res_new.json()["data"]["id"] != plan_id

