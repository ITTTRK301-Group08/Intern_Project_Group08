from pathlib import Path

import fitz

from app.models.analysis import Analysis
from app.models.cv import CV
from app.models.user import User
from app.services import cv_service


def register_and_login(
    client, email: str = "task91011@example.com", password: str = "StrongPass123"
) -> dict[str, str]:
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert reg.status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def make_admin_headers(client, db_session, email: str = "admin_t9@example.com") -> dict[str, str]:
    headers = register_and_login(client, email=email)
    user = db_session.query(User).filter_by(email=email).one()
    user.role = "admin"
    db_session.commit()
    return headers


def make_pdf_bytes(text: str = "Nguyen Van A\nPython Developer\nSkills: Python, SQL") -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    if text:
        page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def make_scanned_image_pdf_bytes() -> bytes:
    # Create a 1x1 PNG image stream embedded in a PDF page with zero text layer
    doc = fitz.open()
    page = doc.new_page(width=200, height=200)
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 10, 10), False)
    pix.clear_with(200)
    page.insert_image(fitz.Rect(10, 10, 100, 100), stream=pix.tobytes("png"))
    data = doc.tobytes()
    doc.close()
    return data


# ── TASK 9 TESTS: Career roles with level, skills, benchmark (0-5) & weight ──


def test_task9_careers_with_levels_weights_and_active_filtering(client, db_session):
    admin_headers = make_admin_headers(client, db_session)

    cat_res = client.post(
        "/api/v1/admin/career-categories",
        headers=admin_headers,
        json={"name": "Engineering", "slug": "engineering", "description": "Software"},
    )
    assert cat_res.status_code == 201
    category_id = cat_res.json()["data"]["id"]

    s1 = client.post(
        "/api/v1/admin/skills",
        headers=admin_headers,
        json={"name": "Python", "description": "Backend language"},
    ).json()["data"]["id"]
    s2 = client.post(
        "/api/v1/admin/skills",
        headers=admin_headers,
        json={"name": "SQL", "description": "Relational DB"},
    ).json()["data"]["id"]

    # Create active Intern and Junior roles, plus an inactive Fresher role
    intern_res = client.post(
        "/api/v1/admin/career-roles",
        headers=admin_headers,
        json={
            "category_id": category_id,
            "name": "Backend Developer",
            "slug": "backend-developer-intern",
            "level": "intern",
            "description": "Intern backend",
            "is_active": True,
            "required_skills": [
                {"skill_id": s1, "required_level": 3, "is_required": True, "weight": 1.5},
                {"skill_id": s2, "required_level": 2, "is_required": False, "weight": 0.5},
            ],
        },
    )
    assert intern_res.status_code == 201
    assert intern_res.json()["data"]["level"] == "Intern"
    intern_id = intern_res.json()["data"]["id"]

    junior_res = client.post(
        "/api/v1/admin/career-roles",
        headers=admin_headers,
        json={
            "category_id": category_id,
            "name": "Backend Developer",
            "slug": "backend-developer-junior",
            "level": "Junior",
            "description": "Junior backend",
            "is_active": True,
            "required_skills": [
                {"skill_id": s1, "required_level": 4, "is_required": True, "weight": 2.0},
            ],
        },
    )
    assert junior_res.status_code == 201

    inactive_res = client.post(
        "/api/v1/admin/career-roles",
        headers=admin_headers,
        json={
            "category_id": category_id,
            "name": "Hidden Role",
            "slug": "hidden-role-fresher",
            "level": "Fresher",
            "is_active": False,
            "required_skills": [{"skill_id": s1, "required_level": 3}],
        },
    )
    assert inactive_res.status_code == 201
    inactive_id = inactive_res.json()["data"]["id"]

    # Duplicate (name, level) must be rejected with 409
    dup_res = client.post(
        "/api/v1/admin/career-roles",
        headers=admin_headers,
        json={
            "category_id": category_id,
            "name": "Backend Developer",
            "slug": "backend-developer-intern-dup",
            "level": "Intern",
            "required_skills": [{"skill_id": s1, "required_level": 3}],
        },
    )
    assert dup_res.status_code == 409

    # Non-positive weight must be rejected with 422
    bad_weight = client.post(
        "/api/v1/admin/career-roles",
        headers=admin_headers,
        json={
            "category_id": category_id,
            "name": "QA Engineer",
            "slug": "qa-engineer",
            "level": "Fresher",
            "required_skills": [{"skill_id": s1, "required_level": 3, "weight": 0}],
        },
    )
    assert bad_weight.status_code == 422

    # Public /api/v1/careers returns only active roles
    all_active = client.get("/api/v1/careers")
    assert all_active.status_code == 200
    roles_data = all_active.json()["data"]
    assert len(roles_data) == 2
    assert all(r["is_active"] is True for r in roles_data)

    # Filter by level
    intern_only = client.get("/api/v1/careers", params={"level": "intern"})
    assert intern_only.status_code == 200
    assert len(intern_only.json()["data"]) == 1
    assert intern_only.json()["data"][0]["level"] == "Intern"

    # Detail and skills endpoints on both /careers and /catalog/roles
    detail_res = client.get(f"/api/v1/careers/{intern_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["data"]["level"] == "Intern"

    skills_res = client.get(f"/api/v1/careers/{intern_id}/skills")
    assert skills_res.status_code == 200
    skill_items = skills_res.json()["data"]
    assert len(skill_items) == 2
    # Sorted by weight desc: Python (1.5) then SQL (0.5)
    assert skill_items[0]["skill"]["name"] == "Python"
    assert skill_items[0]["required_level"] == 3
    assert skill_items[0]["weight"] == 1.5
    assert skill_items[0]["is_required"] is True
    assert skill_items[1]["skill"]["name"] == "SQL"
    assert skill_items[1]["weight"] == 0.5
    assert skill_items[1]["is_required"] is False

    # Catalog role detail/skills stay synchronized
    cat_skills = client.get(f"/api/v1/catalog/roles/{intern_id}/skills")
    assert cat_skills.status_code == 200
    assert cat_skills.json()["data"] == skill_items

    # Inactive role is hidden from public detail & skills
    assert client.get(f"/api/v1/careers/{inactive_id}").status_code == 404
    assert client.get(f"/api/v1/careers/{inactive_id}/skills").status_code == 404


# ── TASK 10 TESTS: Scanned / no-text PDF warning & profile fallback guidance ──


def test_task10_scanned_image_pdf_returns_clear_warning_and_profile_guidance(
    client, tmp_path, monkeypatch
):
    root = tmp_path / "uploads" / "cvs"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cv_service, "UPLOAD_ROOT", root)

    headers = register_and_login(client, email="scan_student@example.com")
    scanned_pdf = make_scanned_image_pdf_bytes()

    res = client.post(
        "/api/v1/cvs",
        headers=headers,
        files={"file": ("scanned_cv.pdf", scanned_pdf, "application/pdf")},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["success"] is True
    assert "khong trich xuat duoc" in body["message"].lower()
    data = body["data"]
    assert data["has_text"] is False
    assert data["cv"]["has_text"] is False
    assert data["cv"]["extraction_status"] == "no_text"
    warning = data["warning"]
    assert warning is not None
    assert warning["code"] == "PDF_NO_EXTRACTABLE_TEXT"
    assert "anh quet" in warning["cause"].lower()
    assert "ho so" in warning["guidance"].lower()
    assert warning["profile_url"] == "/profile"
    assert warning["analysis_url"] == "/analysis?source=profile"

    # Detail endpoint also includes the warning
    cv_id = data["cv"]["id"]
    detail_res = client.get(f"/api/v1/cvs/{cv_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["data"]["warning"]["code"] == "PDF_NO_EXTRACTABLE_TEXT"


def test_task10_too_short_noise_pdf_flagged_and_valid_pdf_has_no_warning(
    client, tmp_path, monkeypatch
):
    root = tmp_path / "uploads" / "cvs"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cv_service, "UPLOAD_ROOT", root)

    headers = register_and_login(client, email="short_pdf@example.com")

    noise_pdf = make_pdf_bytes("Page 1")
    noise_res = client.post(
        "/api/v1/cvs",
        headers=headers,
        files={"file": ("noise.pdf", noise_pdf, "application/pdf")},
    )
    assert noise_res.status_code == 201
    assert noise_res.json()["data"]["has_text"] is False
    assert noise_res.json()["data"]["warning"] is not None

    valid_pdf = make_pdf_bytes("Nguyen Van A\nBackend Engineer\nPython FastAPI SQL Docker")
    valid_res = client.post(
        "/api/v1/cvs",
        headers=headers,
        files={"file": ("valid_cv.pdf", valid_pdf, "application/pdf")},
    )
    assert valid_res.status_code == 201
    valid_data = valid_res.json()["data"]
    assert valid_data["has_text"] is True
    assert valid_data["warning"] is None
    assert valid_data["cv"]["extraction_status"] == "ok"


# ── TASK 11 TESTS: CV list, detail & soft-delete for CVs used in analyses ──


def test_task11_cv_list_detail_and_ownership(client, tmp_path, monkeypatch):
    root = tmp_path / "uploads" / "cvs"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cv_service, "UPLOAD_ROOT", root)

    assert client.get("/api/v1/cvs").status_code == 401

    headers_a = register_and_login(client, email="cva@example.com")
    headers_b = register_and_login(client, email="cvb@example.com")

    up_a1 = client.post(
        "/api/v1/cvs",
        headers=headers_a,
        files={"file": ("cv_v1.pdf", make_pdf_bytes("Version 1 CV Python SQL"), "application/pdf")},
    ).json()["data"]["cv"]
    up_a2 = client.post(
        "/api/v1/cvs",
        headers=headers_a,
        files={"file": ("cv_v2.pdf", make_pdf_bytes("Version 2 CV FastAPI Docker"), "application/pdf")},
    ).json()["data"]["cv"]
    up_b = client.post(
        "/api/v1/cvs",
        headers=headers_b,
        files={"file": ("other.pdf", make_pdf_bytes("User B CV content"), "application/pdf")},
    ).json()["data"]["cv"]

    list_a = client.get("/api/v1/cvs", headers=headers_a)
    assert list_a.status_code == 200
    assert list_a.json()["data"]["total"] == 2
    names_a = {item["file_name"] for item in list_a.json()["data"]["cvs"]}
    assert names_a == {"cv_v1.pdf", "cv_v2.pdf"}
    assert "file_path" not in str(list_a.json())
    assert "/uploads/" not in str(list_a.json())

    # User B cannot read or delete User A's CV
    assert client.get(f"/api/v1/cvs/{up_a1['id']}", headers=headers_b).status_code == 403
    assert client.delete(f"/api/v1/cvs/{up_a1['id']}", headers=headers_b).status_code == 403

    # Detail returns extracted text
    detail_a = client.get(f"/api/v1/cvs/{up_a2['id']}", headers=headers_a)
    assert detail_a.status_code == 200
    assert "FastAPI" in detail_a.json()["data"]["cv"]["extracted_text"]
    assert up_b["id"] != up_a1["id"]


def test_task11_soft_delete_used_cv_and_hard_delete_unused_cv(
    client, db_session, tmp_path, monkeypatch
):
    root = tmp_path / "uploads" / "cvs"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cv_service, "UPLOAD_ROOT", root)

    headers = register_and_login(client, email="softdel@example.com")
    user = db_session.query(User).filter_by(email="softdel@example.com").one()

    unused_cv = client.post(
        "/api/v1/cvs",
        headers=headers,
        files={"file": ("unused.pdf", make_pdf_bytes("Unused CV content here"), "application/pdf")},
    ).json()["data"]["cv"]
    used_cv = client.post(
        "/api/v1/cvs",
        headers=headers,
        files={"file": ("used.pdf", make_pdf_bytes("Used CV in historical report"), "application/pdf")},
    ).json()["data"]["cv"]

    unused_db = db_session.query(CV).filter_by(id=unused_cv["id"]).one()
    used_db = db_session.query(CV).filter_by(id=used_cv["id"]).one()
    unused_path = Path(unused_db.file_path)
    used_path = Path(used_db.file_path)
    assert unused_path.exists() and used_path.exists()

    # Attach an Analysis record to used_cv
    analysis = Analysis(
        user_id=user.id,
        cv_id=used_cv["id"],
        consent_accepted=True,
        consent_purpose_version="v1",
        status="completed",
    )
    db_session.add(analysis)
    db_session.commit()

    # Delete unused CV -> hard delete
    del_unused = client.delete(f"/api/v1/cvs/{unused_cv['id']}", headers=headers)
    assert del_unused.status_code == 200
    assert del_unused.json()["data"]["deletion_type"] == "hard"
    assert del_unused.json()["data"]["has_analysis"] is False
    assert db_session.query(CV).filter_by(id=unused_cv["id"]).first() is None
    assert not unused_path.exists()

    # Delete used CV -> soft delete (is_active = False, analysis history & file preserved)
    del_used = client.delete(f"/api/v1/cvs/{used_cv['id']}", headers=headers)
    assert del_used.status_code == 200
    del_data = del_used.json()["data"]
    assert del_data["deletion_type"] == "soft"
    assert del_data["is_active"] is False
    assert del_data["has_analysis"] is True
    assert del_data["analysis_count"] == 1

    db_session.expire_all()
    preserved_cv = db_session.query(CV).filter_by(id=used_cv["id"]).first()
    assert preserved_cv is not None
    assert preserved_cv.is_active is False
    assert used_path.exists()
    preserved_analysis = db_session.query(Analysis).filter_by(id=analysis.id).one()
    assert preserved_analysis.cv_id == used_cv["id"]

    # Soft-deleted CV is hidden from default active list and detail, visible with include_inactive=true
    active_list = client.get("/api/v1/cvs", headers=headers).json()["data"]["cvs"]
    assert active_list == []
    assert client.get(f"/api/v1/cvs/{used_cv['id']}", headers=headers).status_code == 404

    all_list = client.get(
        "/api/v1/cvs", params={"include_inactive": "true"}, headers=headers
    ).json()["data"]["cvs"]
    assert len(all_list) == 1
    assert all_list[0]["id"] == used_cv["id"]
    assert all_list[0]["is_active"] is False
    assert all_list[0]["has_analysis"] is True

    # Cannot soft-delete again once inactive
    assert client.delete(f"/api/v1/cvs/{used_cv['id']}", headers=headers).status_code == 404


def test_frontend_pages_serve_tasks_9_10_11_elements(client):
    explore = client.get("/explore")
    assert explore.status_code == 200
    assert "levelFilter" in explore.text
    assert "roleDetailSection" in explore.text

    cv_page = client.get("/cv")
    assert cv_page.status_code == 200
    assert "scanWarningBox" in cv_page.text
    assert "cvListSection" in cv_page.text

    analysis_page = client.get("/analysis")
    assert analysis_page.status_code == 200
    assert "scannedCvWarning" in analysis_page.text
    assert "switchToProfileBtn" in analysis_page.text

