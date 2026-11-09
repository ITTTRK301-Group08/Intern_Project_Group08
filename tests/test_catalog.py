from types import SimpleNamespace

import pytest

from app import bootstrap_admin as bootstrap_admin_command
from app.models.user import User
from app.services.catalog_service import bootstrap_admin


def register_and_get_token(client, email="catalog@example.com"):
    payload = {"email": email, "password": "StrongPass123"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def test_catalog_endpoints_are_public_and_empty_catalog_is_valid(client):
    for path in (
        "/api/v1/catalog/categories",
        "/api/v1/catalog/roles",
        "/api/v1/catalog/skills",
        "/api/v1/catalog/resources",
    ):
        response = client.get(path)
        assert response.status_code == 200
        assert response.json()["data"] == []


def test_explore_page_and_assets_are_served(client):
    for path in ("/", "/explore"):
        response = client.get(path)
        assert response.status_code == 200
        assert "Khám phá nghề nghiệp" in response.text

    for path in ("/static/explore.css", "/static/explore.js"):
        assert client.get(path).status_code == 200


def test_catalog_administration_requires_admin(client):
    token = register_and_get_token(client)
    response = client.get(
        "/api/v1/admin/catalog",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_admin_can_manage_catalog_and_users_can_explore_it(client, db_session):
    token = register_and_get_token(client)
    user = db_session.query(User).filter_by(email="catalog@example.com").one()
    user.role = "admin"
    db_session.commit()
    headers = {"Authorization": f"Bearer {token}"}

    category_response = client.post(
        "/api/v1/admin/career-categories",
        headers=headers,
        json={
            "name": "Software Development",
            "slug": "software-development",
            "description": "Build software",
        },
    )
    assert category_response.status_code == 201
    category_id = category_response.json()["data"]["id"]

    skill_response = client.post(
        "/api/v1/admin/skills",
        headers=headers,
        json={"name": "Python", "description": "Programming language"},
    )
    assert skill_response.status_code == 201
    skill_id = skill_response.json()["data"]["id"]

    role_response = client.post(
        "/api/v1/admin/career-roles",
        headers=headers,
        json={
            "category_id": category_id,
            "name": "Backend Developer",
            "slug": "backend-developer",
            "description": "Build backend systems",
            "required_skills": [{"skill_id": skill_id, "required_level": 4}],
        },
    )
    assert role_response.status_code == 201

    resource_response = client.post(
        "/api/v1/admin/resources",
        headers=headers,
        json={
            "slug": "python-docs",
            "skill_id": skill_id,
            "title": "Python tutorial",
            "provider": "Python",
            "url": "https://docs.python.org/3/tutorial/",
            "resource_type": "documentation",
            "description": "Official tutorial",
        },
    )
    assert resource_response.status_code == 201

    roles = client.get("/api/v1/catalog/roles").json()["data"]
    assert roles[0]["required_skills"][0]["skill"]["name"] == "Python"
    resources = client.get(
        "/api/v1/catalog/resources", params={"skill_id": skill_id}
    ).json()["data"]
    assert resources[0]["title"] == "Python tutorial"

    hidden = client.post(
        "/api/v1/admin/resources",
        headers=headers,
        json={
            "slug": "hidden-resource",
            "title": "Hidden",
            "provider": "Example",
            "url": "https://example.com/learn",
            "resource_type": "article",
            "is_active": False,
        },
    )
    assert hidden.status_code == 201
    visible_resources = client.get("/api/v1/catalog/resources").json()["data"]
    assert all(item["slug"] != "hidden-resource" for item in visible_resources)
    admin_catalog = client.get(
        "/api/v1/admin/catalog", headers=headers
    ).json()
    assert admin_catalog["success"] is True
    admin_resources = admin_catalog["data"]["resources"]
    assert any(item["slug"] == "hidden-resource" for item in admin_resources)


def test_bootstrapped_admin_can_login_and_manage_catalog(client, db_session):
    admin, created = bootstrap_admin(
        db_session, email="verified-admin@example.com", password="StrongPass123"
    )
    assert created is True
    assert admin.password_hash.startswith("$2")

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "verified-admin@example.com", "password": "StrongPass123"},
    )
    assert login.status_code == 200
    token = login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    catalog = client.get("/api/v1/admin/catalog", headers=headers)
    assert catalog.status_code == 200
    assert catalog.json()["success"] is True
    assert isinstance(catalog.json()["data"]["categories"], list)

    created_skill = client.post(
        "/api/v1/admin/skills",
        headers=headers,
        json={"name": "Admin test skill", "description": "Temporary integration test"},
    )
    assert created_skill.status_code == 201
    skill_id = created_skill.json()["data"]["id"]
    deleted = client.delete(f"/api/v1/admin/skills/{skill_id}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["success"] is True
    assert deleted.json()["data"] == {"deleted": True}


def test_student_and_invalid_token_cannot_manage_catalog(client):
    token = register_and_get_token(client, email="rbac-student@example.com")
    student_response = client.get(
        "/api/v1/admin/catalog",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert student_response.status_code == 403
    assert student_response.json()["success"] is False
    assert student_response.json()["detail"] == "Administrator access required"

    missing_response = client.get(
        "/api/v1/admin/catalog",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert missing_response.status_code == 401


def test_learning_resource_rejects_non_http_urls(client, db_session):
    token = register_and_get_token(client)
    user = db_session.query(User).filter_by(email="catalog@example.com").one()
    user.role = "admin"
    db_session.commit()

    response = client.post(
        "/api/v1/admin/resources",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "slug": "unsafe-resource",
            "title": "Unsafe",
            "provider": "Example",
            "url": "javascript:alert(1)",
            "resource_type": "article",
        },
    )
    assert response.status_code == 422


def test_admin_bootstrap_is_idempotent_and_does_not_elevate_existing_users(db_session):
    admin, created = bootstrap_admin(
        db_session, email="ADMIN@example.com", password="StrongPass123"
    )
    assert created is True
    assert admin.email == "admin@example.com"
    assert admin.role == "admin"
    assert admin.password_hash != "StrongPass123"

    same_admin, created_again = bootstrap_admin(
        db_session, email="admin@example.com", password="DifferentPass123"
    )
    assert created_again is False
    assert same_admin.id == admin.id

    student = User(
        email="student-existing@example.com",
        password_hash="already-hashed",
        role="student",
        is_active=True,
    )
    db_session.add(student)
    db_session.commit()
    with pytest.raises(ValueError, match="refusing to elevate"):
        bootstrap_admin(
            db_session,
            email="student-existing@example.com",
            password="StrongPass123",
        )
    db_session.refresh(student)
    assert student.role == "student"


def test_admin_bootstrap_command_prompts_for_hidden_password(
    db_session, monkeypatch, capsys
):
    monkeypatch.setattr(
        bootstrap_admin_command.sys, "stdin", SimpleNamespace(isatty=lambda: True)
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: "prompted-admin@example.com")
    passwords = iter(("StrongPass123", "StrongPass123"))
    monkeypatch.setattr(
        bootstrap_admin_command.getpass,
        "getpass",
        lambda _prompt: next(passwords),
    )
    monkeypatch.setattr(
        bootstrap_admin_command, "SessionLocal", lambda: db_session
    )

    assert bootstrap_admin_command.main() == 0
    output = capsys.readouterr()
    assert "Created admin account: prompted-admin@example.com" in output.out
    assert "StrongPass123" not in output.out
    assert "StrongPass123" not in output.err
    admin = db_session.query(User).filter_by(email="prompted-admin@example.com").one()
    assert admin.role == "admin"


def test_admin_bootstrap_command_rejects_mismatched_passwords(
    db_session, monkeypatch, capsys
):
    monkeypatch.setattr(
        bootstrap_admin_command.sys, "stdin", SimpleNamespace(isatty=lambda: True)
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: "prompted-admin@example.com")
    passwords = iter(("StrongPass123", "DifferentPass123"))
    monkeypatch.setattr(
        bootstrap_admin_command.getpass,
        "getpass",
        lambda _prompt: next(passwords),
    )
    monkeypatch.setattr(
        bootstrap_admin_command, "SessionLocal", lambda: db_session
    )

    assert bootstrap_admin_command.main() == 2
    assert "Passwords do not match." in capsys.readouterr().err
    assert db_session.query(User).count() == 0
