"""Kiểm thử các API quản trị: thống kê, người dùng và danh mục phân trang."""

from app.models.analysis import Analysis
from app.models.career import CareerCategory, CareerRole, Skill
from app.models.interview import InterviewSession
from app.models.learning_resource import LearningResource
from app.models.student_profile import StudentProfile
from app.models.user import User


def register(client, email, password="StrongPass123"):
    response = client.post(
        "/api/v1/auth/register", json={"email": email, "password": password}
    )
    assert response.status_code == 201
    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert login.status_code == 200
    return login.json()["data"]["access_token"]


def make_admin(client, db_session, email="admin-mgmt@example.com"):
    token = register(client, email)
    user = db_session.query(User).filter_by(email=email).one()
    user.role = "admin"
    db_session.commit()
    return token, user


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_admin_stats_report_real_database_counts(client, db_session):
    token, admin = make_admin(client, db_session)
    register(client, "locked-user@example.com")
    locked_user = db_session.query(User).filter_by(email="locked-user@example.com").one()
    locked_user.is_active = False
    db_session.add(
        StudentProfile(user_id=locked_user.id, full_name="Nguyễn Văn Bị Khóa")
    )
    category = CareerCategory(name="Data and AI", slug="data-and-ai")
    skill = Skill(name="Python")
    db_session.add_all([category, skill])
    db_session.commit()
    db_session.add(
        CareerRole(
            name="Data Analyst",
            slug="data-analyst",
            category_id=category.id,
        )
    )
    db_session.add_all(
        [
            Analysis(
                user_id=admin.id,
                consent_accepted=True,
                consent_purpose_version="v1",
                status="pending",
            ),
            InterviewSession(user_id=admin.id, status="ready"),
            LearningResource(
                slug="stats-resource",
                title="Stats resource",
                provider="Example",
                url="https://example.com/stats-resource",
                resource_type="article",
                approval_status="pending",
            ),
        ]
    )
    db_session.commit()

    response = client.get("/api/v1/admin/stats", headers=auth(token))
    assert response.status_code == 200
    assert response.json()["data"] == {
        "total_users": 2,
        "total_active_users": 1,
        "total_locked_users": 1,
        "total_analyses": 1,
        "total_interviews": 1,
        "total_categories": 1,
        "total_roles": 1,
        "total_skills": 1,
        "total_resources": 1,
        "total_pending_resources": 1,
    }


def test_admin_users_support_search_filter_pagination_and_detail(
    client, db_session
):
    token, admin = make_admin(client, db_session)
    register(client, "student-page@example.com")
    student = db_session.query(User).filter_by(email="student-page@example.com").one()
    student.is_active = False
    db_session.add(
        StudentProfile(
            user_id=student.id,
            full_name="Trần Thị Bình",
            major="Công nghệ thông tin",
            university="Đại học Bách khoa",
        )
    )
    db_session.add_all(
        [
            Analysis(
                user_id=student.id,
                consent_accepted=True,
                consent_purpose_version="v1",
                status="pending",
            ),
            InterviewSession(user_id=student.id, status="ready"),
        ]
    )
    db_session.commit()
    headers = auth(token)

    first_page = client.get(
        "/api/v1/admin/users", params={"page": 1, "page_size": 1}, headers=headers
    )
    assert first_page.status_code == 200
    page_data = first_page.json()["data"]
    assert page_data["total"] == 2
    assert page_data["page"] == 1
    assert page_data["page_size"] == 1
    assert page_data["total_pages"] == 2
    assert len(page_data["items"]) == 1
    assert "password_hash" not in str(page_data)

    by_name = client.get(
        "/api/v1/admin/users", params={"search": "thị"}, headers=headers
    ).json()["data"]
    assert by_name["total"] == 1
    assert by_name["items"][0]["email"] == "student-page@example.com"
    assert by_name["items"][0]["full_name"] == "Trần Thị Bình"

    by_role = client.get(
        "/api/v1/admin/users", params={"role": "admin"}, headers=headers
    ).json()["data"]
    assert by_role["total"] == 1
    assert by_role["items"][0]["email"] == "admin-mgmt@example.com"

    locked = client.get(
        "/api/v1/admin/users", params={"is_active": "false"}, headers=headers
    ).json()["data"]
    assert locked["total"] == 1
    assert locked["items"][0]["is_active"] is False

    detail = client.get(
        f"/api/v1/admin/users/{student.id}", headers=headers
    )
    assert detail.status_code == 200
    detail_data = detail.json()["data"]
    assert detail_data["email"] == "student-page@example.com"
    assert detail_data["full_name"] == "Trần Thị Bình"
    assert detail_data["profile"]["major"] == "Công nghệ thông tin"
    assert detail_data["total_analyses"] == 1
    assert detail_data["total_interviews"] == 1
    assert "password_hash" not in str(detail_data)

    assert (
        client.get("/api/v1/admin/users/999999", headers=headers).status_code == 404
    )
    assert (
        client.get(
            "/api/v1/admin/users", params={"page_size": 500}, headers=headers
        ).status_code
        == 422
    )


def test_admin_catalog_lists_are_paginated_and_filterable(client, db_session):
    token, _ = make_admin(client, db_session, email="catalog-mgmt@example.com")
    headers = auth(token)

    category = client.post(
        "/api/v1/admin/career-categories",
        headers=headers,
        json={"name": "Software Development", "slug": "software-development"},
    ).json()["data"]
    skill = client.post(
        "/api/v1/admin/skills",
        headers=headers,
        json={"name": "Python", "description": "Programming language"},
    ).json()["data"]
    role = client.post(
        "/api/v1/admin/career-roles",
        headers=headers,
        json={
            "category_id": category["id"],
            "name": "Backend Developer",
            "slug": "backend-developer",
            "required_skills": [
                {"skill_id": skill["id"], "required_level": 4, "weight": 2}
            ],
        },
    ).json()["data"]

    roles_page = client.get(
        "/api/v1/admin/career-roles",
        params={"search": "backend", "page_size": 1},
        headers=headers,
    )
    assert roles_page.status_code == 200
    roles_data = roles_page.json()["data"]
    assert roles_data["total"] == 1
    assert roles_data["items"][0]["required_skills"][0]["skill"]["name"] == "Python"

    role_detail = client.get(
        f"/api/v1/admin/career-roles/{role['id']}", headers=headers
    ).json()["data"]
    assert role_detail["category"]["name"] == "Software Development"

    categories_page = client.get(
        "/api/v1/admin/career-categories",
        params={"search": "software"},
        headers=headers,
    ).json()["data"]
    assert categories_page["total"] == 1

    category_detail = client.get(
        f"/api/v1/admin/career-categories/{category['id']}", headers=headers
    ).json()["data"]
    assert category_detail["role_count"] == 1
    assert category_detail["roles"][0]["name"] == "Backend Developer"

    blocked_delete = client.delete(
        f"/api/v1/admin/career-categories/{category['id']}", headers=headers
    )
    assert blocked_delete.status_code == 409
    assert "career role" in blocked_delete.json()["detail"]

    skills_page = client.get(
        "/api/v1/admin/skills", params={"search": "python"}, headers=headers
    ).json()["data"]
    assert skills_page["total"] == 1

    empty_category = client.post(
        "/api/v1/admin/career-categories",
        headers=headers,
        json={"name": "Temporary", "slug": "temporary"},
    ).json()["data"]
    deleted = client.delete(
        f"/api/v1/admin/career-categories/{empty_category['id']}", headers=headers
    )
    assert deleted.status_code == 200
    assert deleted.json()["data"] == {"deleted": True}


def test_admin_resources_support_filters_detail_and_related_categories(
    client, db_session
):
    token, _ = make_admin(client, db_session, email="resource-mgmt@example.com")
    headers = auth(token)

    category = client.post(
        "/api/v1/admin/career-categories",
        headers=headers,
        json={"name": "Data and AI", "slug": "data-and-ai"},
    ).json()["data"]
    skill = client.post(
        "/api/v1/admin/skills", headers=headers, json={"name": "SQL"}
    ).json()["data"]
    role = client.post(
        "/api/v1/admin/career-roles",
        headers=headers,
        json={
            "category_id": category["id"],
            "name": "Data Analyst",
            "slug": "data-analyst",
            "required_skills": [{"skill_id": skill["id"], "required_level": 3}],
        },
    ).json()["data"]
    resource = client.post(
        "/api/v1/admin/resources",
        headers=headers,
        json={
            "slug": "sql-course",
            "skill_id": skill["id"],
            "title": "SQL course",
            "provider": "Example Academy",
            "url": "https://example.com/sql-course",
            "resource_type": "course",
            "description": "Learn SQL",
        },
    ).json()["data"]
    assert resource["approval_status"] == "pending"

    pending = client.get(
        "/api/v1/admin/resources",
        params={"approval_status": "pending"},
        headers=headers,
    ).json()["data"]
    assert pending["total"] == 1

    empty_approved = client.get(
        "/api/v1/admin/resources",
        params={"approval_status": "approved"},
        headers=headers,
    ).json()["data"]
    assert empty_approved["total"] == 0

    assert (
        client.patch(
            f"/api/v1/admin/resources/{resource['id']}/approval",
            headers=headers,
            json={"approval_status": "approved"},
        ).status_code
        == 200
    )

    approved = client.get(
        "/api/v1/admin/resources",
        params={
            "approval_status": "approved",
            "resource_type": "course",
            "search": "sql",
            "is_active": "true",
            "page_size": 5,
        },
        headers=headers,
    ).json()["data"]
    assert approved["total"] == 1
    assert approved["items"][0]["related_roles"][0]["name"] == "Data Analyst"

    detail = client.get(
        f"/api/v1/admin/resources/{resource['id']}", headers=headers
    )
    assert detail.status_code == 200
    detail_data = detail.json()["data"]
    assert detail_data["related_categories"] == [
        {"id": category["id"], "name": "Data and AI"}
    ]
    assert detail_data["skill"]["name"] == "SQL"
    assert detail_data["related_roles"][0]["id"] == role["id"]

    assert (
        client.get(
            "/api/v1/admin/resources/999999", headers=headers
        ).status_code
        == 404
    )


def test_admin_read_endpoints_enforce_authorization(client, db_session):
    paths = (
        "/api/v1/admin/users",
        "/api/v1/admin/stats",
        "/api/v1/admin/career-categories",
        "/api/v1/admin/career-roles",
        "/api/v1/admin/skills",
        "/api/v1/admin/resources",
    )
    student_token = register(client, "rbac-reader@example.com")
    admin_token, _ = make_admin(client, db_session, email="rbac-admin@example.com")

    for path in paths:
        assert client.get(path).status_code == 401
        assert client.get(path, headers=auth(student_token)).status_code == 403
        assert client.get(path, headers=auth(admin_token)).status_code == 200
