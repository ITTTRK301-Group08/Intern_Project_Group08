from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select

from app.models.analysis import Analysis
from app.models.career import Skill
from app.models.learning_plan import LearningPlan, LearningPlanItem
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


def create_plan(db_session, *, user_id: int, status: str = "active"):
    analysis = Analysis(
        user_id=user_id,
        consent_accepted=True,
        consent_purpose_version="v1",
        status="completed",
        readiness_score=70,
    )
    db_session.add(analysis)
    db_session.flush()
    skill = Skill(name=f"Learning skill {analysis.id}")
    db_session.add(skill)
    db_session.flush()
    plan = LearningPlan(
        user_id=user_id,
        analysis_id=analysis.id,
        title="Four-week learning plan",
        start_date=date(2026, 11, 14),
        end_date=date(2026, 12, 12),
        status=status,
    )
    db_session.add(plan)
    db_session.flush()
    item = LearningPlanItem(
        plan_id=plan.id,
        skill_id=skill.id,
        week_number=1,
        task_description="Complete Python fundamentals.",
    )
    db_session.add(item)
    db_session.commit()
    return plan.id, item.id


def test_learning_plan_item_completion_and_status(client, db_session):
    headers = register_and_login(client, "learning-plan@example.com")
    user = db_session.scalar(
        select(User).where(User.email == "learning-plan@example.com")
    )
    plan_id, item_id = create_plan(db_session, user_id=user.id)

    details = client.get(f"/api/v1/learning-plans/{plan_id}", headers=headers)
    assert details.status_code == 200
    assert details.json()["data"]["status"] == "active"
    assert details.json()["data"]["title"] == "Four-week learning plan"
    assert details.json()["data"]["items"][0]["is_completed"] is False

    before_update = datetime.now(timezone.utc).replace(tzinfo=None)
    completed = client.patch(
        f"/api/v1/learning-plans/{plan_id}/items/{item_id}",
        headers=headers,
        json={"is_completed": True},
    )
    assert completed.status_code == 200
    assert completed.json()["data"]["is_completed"] is True
    assert completed.json()["data"]["completed_at"] is not None
    assert completed.json()["data"]["completed_at"].endswith("Z")
    stored_item = db_session.get(LearningPlanItem, item_id)
    assert stored_item.completed_at is not None
    assert stored_item.completed_at.tzinfo is None
    assert stored_item.completed_at >= before_update
    first_completed_at = stored_item.completed_at

    completed_again = client.patch(
        f"/api/v1/learning-plans/{plan_id}/items/{item_id}",
        headers=headers,
        json={"is_completed": True},
    )
    assert completed_again.status_code == 200
    assert db_session.get(LearningPlanItem, item_id).completed_at >= first_completed_at

    uncompleted = client.patch(
        f"/api/v1/learning-plans/{plan_id}/items/{item_id}",
        headers=headers,
        json={"is_completed": False},
    )
    assert uncompleted.status_code == 200
    assert uncompleted.json()["data"]["completed_at"] is None

    status_response = client.patch(
        f"/api/v1/learning-plans/{plan_id}/status",
        headers=headers,
        json={"status": "archived"},
    )
    assert status_response.status_code == 200
    assert status_response.json()["data"]["status"] == "archived"

    reactivate = client.patch(
        f"/api/v1/learning-plans/{plan_id}/status",
        headers=headers,
        json={"status": "active"},
    )
    assert reactivate.status_code == 200
    assert reactivate.json()["data"]["status"] == "active"

    listing = client.get("/api/v1/learning-plans", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["data"][0]["completed_item_count"] == 0


def test_only_one_plan_for_an_analysis_can_be_active(client, db_session):
    headers = register_and_login(client, "single-active-plan@example.com")
    user = db_session.scalar(
        select(User).where(User.email == "single-active-plan@example.com")
    )
    active_plan_id, _ = create_plan(db_session, user_id=user.id)
    active_plan = db_session.get(LearningPlan, active_plan_id)
    second_plan = LearningPlan(
        user_id=user.id,
        analysis_id=active_plan.analysis_id,
        title="Second learning plan",
        start_date=date(2026, 11, 14),
        end_date=date(2026, 12, 12),
        status="archived",
    )
    db_session.add(second_plan)
    db_session.commit()

    conflict = client.patch(
        f"/api/v1/learning-plans/{second_plan.id}/status",
        headers=headers,
        json={"status": "active"},
    )
    assert conflict.status_code == 409
    assert db_session.get(LearningPlan, active_plan_id).status == "active"
    assert db_session.get(LearningPlan, second_plan.id).status == "archived"

    archive_old = client.patch(
        f"/api/v1/learning-plans/{active_plan_id}/status",
        headers=headers,
        json={"status": "archived"},
    )
    assert archive_old.status_code == 200
    activate_new = client.patch(
        f"/api/v1/learning-plans/{second_plan.id}/status",
        headers=headers,
        json={"status": "active"},
    )
    assert activate_new.status_code == 200


def test_learning_plan_updates_are_owner_scoped(client, db_session):
    headers_a = register_and_login(client, "plan-owner-a@example.com")
    headers_b = register_and_login(client, "plan-owner-b@example.com")
    user_a = db_session.scalar(
        select(User).where(User.email == "plan-owner-a@example.com")
    )
    plan_id, item_id = create_plan(db_session, user_id=user_a.id)

    plan_result = client.patch(
        f"/api/v1/learning-plans/{plan_id}/status",
        headers=headers_b,
        json={"status": "archived"},
    )
    item_result = client.patch(
        f"/api/v1/learning-plans/{plan_id}/items/{item_id}",
        headers=headers_b,
        json={"is_completed": True},
    )
    details = client.get(
        f"/api/v1/learning-plans/{plan_id}", headers=headers_b
    )

    assert plan_result.status_code == 404
    assert item_result.status_code == 404
    assert details.status_code == 404
    assert db_session.get(LearningPlan, plan_id).status == "active"
    assert db_session.get(LearningPlanItem, item_id).is_completed is False


@pytest.mark.parametrize(
    ("path_suffix", "payload"),
    [
        ("/status", {"status": "paused"}),
        ("/items/1", {"is_completed": "yes"}),
    ],
)
def test_learning_plan_invalid_updates_are_rejected(
    client, db_session, path_suffix, payload
):
    headers = register_and_login(client, "plan-invalid@example.com")
    user = db_session.scalar(
        select(User).where(User.email == "plan-invalid@example.com")
    )
    plan_id, item_id = create_plan(db_session, user_id=user.id)
    path_suffix = path_suffix.replace("/items/1", f"/items/{item_id}")

    response = client.patch(
        f"/api/v1/learning-plans/{plan_id}{path_suffix}",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 422


def test_learning_plan_endpoints_require_authentication(client):
    assert client.get("/api/v1/learning-plans").status_code == 401
    assert (
        client.patch(
            "/api/v1/learning-plans/1/status", json={"status": "archived"}
        ).status_code
        == 401
    )
