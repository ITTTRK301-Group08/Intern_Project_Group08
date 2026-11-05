from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.security import create_access_token
from app.models.student_profile import StudentProfile
from app.models.user import User


def register_and_login(client, email: str = "student@example.com", password: str = "StrongPass123"):
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert reg.status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def valid_profile_payload(**overrides):
    payload = {
        "full_name": "Nguyen Ngoc Khang",
        "major": "Phat trien phan mem",
        "university": "PTIT",
        "strengths": ["Problem Solving", "Teamwork"],
        "self_assessed_skills": [
            {"skill_name": "Python", "level": 4},
            {"skill_name": "SQL", "level": 3},
        ],
        "career_goal": "Backend Developer Intern",
        "target_role_id": None,
        "bio": "Sinh vien yeu thich lap trinh Backend",
    }
    payload.update(overrides)
    return payload


def test_get_profile_requires_auth(client):
    response = client.get("/api/v1/profile/me")
    assert response.status_code == 401


def test_put_profile_requires_auth(client):
    response = client.put("/api/v1/profile/me", json=valid_profile_payload())
    assert response.status_code == 401


def test_get_profile_not_found_for_new_user(client):
    headers = register_and_login(client)
    response = client.get("/api/v1/profile/me", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Profile not found"


def test_create_profile_via_put_upsert(client):
    headers = register_and_login(client)
    response = client.put("/api/v1/profile/me", json=valid_profile_payload(), headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Cap nhat ho so thanh cong"
    data = body["data"]
    assert data["full_name"] == "Nguyen Ngoc Khang"
    assert data["email"] == "student@example.com"
    assert data["major"] == "Phat trien phan mem"
    assert data["university"] == "PTIT"
    assert data["strengths"] == ["Problem Solving", "Teamwork"]
    assert data["self_assessed_skills"][0]["skill_name"] == "Python"
    assert data["self_assessed_skills"][0]["level"] == 4
    assert data["career_goal"] == "Backend Developer Intern"
    assert data["bio"] == "Sinh vien yeu thich lap trinh Backend"
    assert "password_hash" not in str(body)


def test_get_profile_success_after_create(client):
    headers = register_and_login(client)
    client.put("/api/v1/profile/me", json=valid_profile_payload(), headers=headers)
    response = client.get("/api/v1/profile/me", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Lay ho so thanh cong"
    assert body["data"]["full_name"] == "Nguyen Ngoc Khang"
    assert body["data"]["email"] == "student@example.com"


def test_partial_update_does_not_erase_other_fields(client, db_session):
    headers = register_and_login(client)
    client.put("/api/v1/profile/me", json=valid_profile_payload(), headers=headers)
    before = db_session.query(StudentProfile).first()
    assert before.major == "Phat trien phan mem"

    response = client.put(
        "/api/v1/profile/me",
        json={"full_name": "Nguyen Ngoc Khang", "career_goal": "AI Engineer Intern"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["career_goal"] == "AI Engineer Intern"
    assert data["major"] == "Phat trien phan mem"
    assert data["university"] == "PTIT"
    assert data["strengths"] == ["Problem Solving", "Teamwork"]
    assert len(data["self_assessed_skills"]) == 2


def test_full_name_empty_rejected(client):
    headers = register_and_login(client)
    response = client.put("/api/v1/profile/me", json=valid_profile_payload(full_name=""), headers=headers)
    assert response.status_code == 422


def test_full_name_blank_rejected(client):
    headers = register_and_login(client)
    response = client.put("/api/v1/profile/me", json=valid_profile_payload(full_name="   "), headers=headers)
    assert response.status_code == 422


def test_skill_level_below_zero_rejected(client):
    headers = register_and_login(client)
    payload = valid_profile_payload(self_assessed_skills=[{"skill_name": "Python", "level": -1}])
    response = client.put("/api/v1/profile/me", json=payload, headers=headers)
    assert response.status_code == 422


def test_skill_level_above_five_rejected(client):
    headers = register_and_login(client)
    payload = valid_profile_payload(self_assessed_skills=[{"skill_name": "Python", "level": 6}])
    response = client.put("/api/v1/profile/me", json=payload, headers=headers)
    assert response.status_code == 422


def test_skill_name_empty_rejected(client):
    headers = register_and_login(client)
    payload = valid_profile_payload(self_assessed_skills=[{"skill_name": "", "level": 3}])
    response = client.put("/api/v1/profile/me", json=payload, headers=headers)
    assert response.status_code == 422


def test_cannot_set_user_id_via_request(client):
    headers = register_and_login(client)
    payload = valid_profile_payload()
    payload["user_id"] = 999
    response = client.put("/api/v1/profile/me", json=payload, headers=headers)
    assert response.status_code == 422


def test_cannot_set_id_via_request(client):
    headers = register_and_login(client)
    payload = valid_profile_payload()
    payload["id"] = 999
    response = client.put("/api/v1/profile/me", json=payload, headers=headers)
    assert response.status_code == 422


def test_user_cannot_access_or_modify_other_profile(client, db_session):
    headers_a = register_and_login(client, "a@example.com")
    headers_b = register_and_login(client, "b@example.com")
    client.put("/api/v1/profile/me", json=valid_profile_payload(full_name="User A"), headers=headers_a)
    client.put("/api/v1/profile/me", json=valid_profile_payload(full_name="User B"), headers=headers_b)

    # B can only read their own profile via /me (identity from token)
    res_b = client.get("/api/v1/profile/me", headers=headers_b)
    assert res_b.status_code == 200
    assert res_b.json()["data"]["full_name"] == "User B"
    assert res_b.json()["data"]["email"] == "b@example.com"

    # B update does not change A
    client.put("/api/v1/profile/me", json={"full_name": "User B Updated"}, headers=headers_b)
    res_a = client.get("/api/v1/profile/me", headers=headers_a)
    assert res_a.json()["data"]["full_name"] == "User A"

    profiles = db_session.query(StudentProfile).all()
    assert len(profiles) == 2
    assert {p.full_name for p in profiles} == {"User A", "User B Updated"}


def test_one_user_cannot_have_two_profiles_db_constraint(db_session):
    user = User(email="uniq@example.com", password_hash="x", role="student", is_active=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    db_session.add(StudentProfile(user_id=user.id, full_name="One"))
    db_session.commit()
    db_session.add(StudentProfile(user_id=user.id, full_name="Two"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_json_fields_persisted(client, db_session):
    headers = register_and_login(client)
    client.put("/api/v1/profile/me", json=valid_profile_payload(), headers=headers)
    profile = db_session.query(StudentProfile).first()
    assert profile.strengths == ["Problem Solving", "Teamwork"]
    assert profile.self_assessed_skills == [
        {"skill_name": "Python", "level": 4},
        {"skill_name": "SQL", "level": 3},
    ]


def test_updated_at_changes_on_update(client, db_session):
    headers = register_and_login(client)
    client.put("/api/v1/profile/me", json=valid_profile_payload(), headers=headers)
    first = db_session.query(StudentProfile).first()
    first_updated = first.updated_at
    # Ensure a measurable change
    first.updated_at = datetime.now(timezone.utc) - timedelta(seconds=5)
    db_session.commit()

    client.put("/api/v1/profile/me", json={"full_name": "Updated Name"}, headers=headers)
    db_session.expire_all()
    second = db_session.query(StudentProfile).first()
    assert second.full_name == "Updated Name"
    assert second.updated_at is not None
    assert second.updated_at >= first_updated or second.updated_at != first.updated_at
