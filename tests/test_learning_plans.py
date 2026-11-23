import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.models.analysis import Analysis, AnalysisSkillGap
from app.models.career import CareerCategory, CareerRole, Skill
from app.models.learning_plan import LearningPlan, LearningPlanItem
from app.models.learning_resource import LearningResource
from app.models.profile_data import CareerRoleSkill
from app.models.user import User
from app.schemas.learning_plan_ai import ResourceSelectionResponse
from app.services import learning_plan_service
from app.services.ai import AIServiceError


@pytest.fixture(autouse=True)
def mock_resource_selector(monkeypatch):
    class FakeAIService:
        async def generate_structured(self, *, prompt, response_schema, system_instruction):
            payload = json.loads(prompt)
            resources_by_skill = {}
            for resource in payload["approved_resources"]:
                resources_by_skill.setdefault(resource["skill_id"], resource["id"])
            return response_schema.model_validate({
                "selections": [
                    {
                        "skill_id": task["skill_id"],
                        "week_number": task["week_number"],
                        "resource_id": resources_by_skill.get(task["skill_id"]),
                    }
                    for task in payload["tasks"]
                ]
            })

    monkeypatch.setattr(learning_plan_service, "get_ai_service", FakeAIService)


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
        description="Python's official tutorial",
        language="vi",
        is_free=True,
        approval_status="approved",
    )
    res_sql = LearningResource(
        slug="sql-bolt-practice",
        skill_id=skill_sql.id,
        title="Thực hành SQL Bolt",
        provider="SQLBolt",
        url="https://sqlbolt.com/",
        resource_type="practice",
        description="Interactive SQL exercises",
        language="en",
        is_free=True,
        approval_status="approved",
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
        evidence="Đã xây dựng dự án bằng Python",
        has_evidence=True,
        recommendation="Học thêm nâng cao Python",
    )
    gap_sql = AnalysisSkillGap(
        analysis_id=analysis.id,
        skill_id=skill_sql.id,
        current_level=1,
        target_level=3,
        evidence="Đã thực hành truy vấn SQL",
        has_evidence=True,
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


def test_list_plans_auto_creates_from_latest_completed_analysis(client, db_session):
    headers, user_id = register_user(client, "auto_plan_user@example.com")
    analysis = setup_catalog_and_analysis(db_session, user_id=user_id, status="completed")

    first = client.get("/api/v1/learning-plans?include_archived=false", headers=headers)
    assert first.status_code == 200
    plans = first.json()["data"]
    assert len(plans) == 1
    assert plans[0]["analysis_id"] == analysis.id
    assert plans[0]["status"] == "active"
    assert plans[0]["total_items"] > 0

    # Một lượt mở lộ trình thứ hai không được tạo thêm plan trùng.
    second = client.get("/api/v1/learning-plans?include_archived=false", headers=headers)
    assert second.status_code == 200
    assert [p["id"] for p in second.json()["data"]] == [plans[0]["id"]]


def test_list_plans_does_not_call_ai(client, db_session, monkeypatch):
    headers, user_id = register_user(client, "auto_plan_no_ai@example.com")
    setup_catalog_and_analysis(db_session, user_id=user_id, status="completed")

    class NoAI:
        def __init__(self):
            raise AssertionError("Auto-create must not call AI during a page load")

    monkeypatch.setattr(learning_plan_service, "get_ai_service", NoAI)

    response = client.get("/api/v1/learning-plans?include_archived=false", headers=headers)
    assert response.status_code == 200
    plans = response.json()["data"]
    assert len(plans) == 1
    assert plans[0]["total_items"] > 0


def test_list_plans_does_not_create_from_pending_analysis(client, db_session):
    headers, user_id = register_user(client, "auto_plan_pending_user@example.com")
    setup_catalog_and_analysis(db_session, user_id=user_id, status="pending")

    response = client.get("/api/v1/learning-plans?include_archived=false", headers=headers)
    assert response.status_code == 200
    assert response.json()["data"] == []
    assert db_session.query(LearningPlan).count() == 0


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
    assert first_res["relevance_score"] == 100
    assert first_res["description"] is not None
    assert all(
        item["resource_match_status"] == (
            "available" if item["resource_id"] is not None else "no_approved_match"
        )
        for item in data["items"]
    )

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


def test_plan_has_no_unapproved_resources_when_no_approved_match(client, db_session):
    headers, user_id = register_user(client, "resource-free-plan@example.com")
    analysis = setup_catalog_and_analysis(db_session, user_id=user_id)
    db_session.query(LearningResource).update({"approval_status": "pending"})
    db_session.commit()

    response = client.post(
        "/api/v1/learning-plans",
        json={"analysis_id": analysis.id},
        headers=headers,
    )
    assert response.status_code == 201
    items = response.json()["data"]["items"]
    assert items
    assert all(item["resource_id"] is None for item in items)
    assert all(item["resource"] is None for item in items)
    assert all(item["resource_match_status"] == "no_approved_match" for item in items)


def test_plan_is_created_when_resource_ai_is_unavailable(client, db_session, monkeypatch):
    headers, user_id = register_user(client, "resource-ai-down@example.com")
    analysis = setup_catalog_and_analysis(db_session, user_id=user_id)

    class FailingAIService:
        async def generate_structured(self, *, prompt, response_schema, system_instruction):
            raise AIServiceError("provider rate limited")

    monkeypatch.setattr(learning_plan_service, "get_ai_service", FailingAIService)
    response = client.post(
        "/api/v1/learning-plans",
        json={"analysis_id": analysis.id},
        headers=headers,
    )
    assert response.status_code == 201
    items = response.json()["data"]["items"]
    assert items
    assert all(item["resource_id"] is None for item in items)
    assert all(item["resource_match_status"] == "no_approved_match" for item in items)


def test_ai_cannot_attach_unknown_resource_id(client, db_session, monkeypatch):
    headers, user_id = register_user(client, "invalid-resource-selection@example.com")
    analysis = setup_catalog_and_analysis(db_session, user_id=user_id)

    class InvalidAIService:
        async def generate_structured(self, *, prompt, response_schema, system_instruction):
            payload = json.loads(prompt)
            return response_schema.model_validate({
                "selections": [
                    {
                        "skill_id": task["skill_id"],
                        "week_number": task["week_number"],
                        "resource_id": 999999,
                    }
                    for task in payload["tasks"]
                ]
            })

    monkeypatch.setattr(learning_plan_service, "get_ai_service", InvalidAIService)
    response = client.post(
        "/api/v1/learning-plans",
        json={"analysis_id": analysis.id},
        headers=headers,
    )
    assert response.status_code == 502
    assert response.json()["detail"]["data"]["code"] == "INVALID_RESOURCE_RECOMMENDATION"
    assert db_session.query(LearningPlan).count() == 0

