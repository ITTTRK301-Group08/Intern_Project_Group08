import os
import uuid
from pathlib import Path

import fitz
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models.cv import CV
from app.models.user import User
from app.services import cv_service


def register_and_login(client, email: str = "cvstudent@example.com", password: str = "StrongPass123"):
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert reg.status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def make_pdf_bytes(text: str = "Nguyen Van A\nPython Developer\nSkills: Python, SQL", pages: int = 1) -> bytes:
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72 + i * 10), f"{text}\nPage {i + 1}")
    data = doc.tobytes()
    doc.close()
    return data


def make_empty_text_pdf_bytes() -> bytes:
    doc = fitz.open()
    doc.new_page()  # no text inserted
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture(autouse=True)
def isolate_upload_root(tmp_path, monkeypatch):
    root = tmp_path / "uploads" / "cvs"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cv_service, "UPLOAD_ROOT", root)
    return root


def test_upload_valid_pdf(client, db_session, isolate_upload_root):
    headers = register_and_login(client)
    pdf = make_pdf_bytes("Nguyen Van A Python SQL FastAPI")
    response = client.post(
        "/api/v1/cvs",
        headers=headers,
        files={"file": ("resume.pdf", pdf, "application/pdf")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert "Upload CV thanh cong" in body["message"]
    cv = body["data"]["cv"]
    assert cv["file_name"] == "resume.pdf"
    assert cv["file_size"] == len(pdf)
    assert cv["mime_type"] == "application/pdf"
    assert cv["is_active"] is True
    assert "Nguyen Van A" in (cv["extracted_text"] or "")
    assert "file_path" not in str(body)
    assert "/uploads/" not in str(body)

    db_cv = db_session.query(CV).filter_by(id=cv["id"]).first()
    assert db_cv is not None
    assert db_cv.user_id is not None
    assert db_cv.extracted_text and "Python" in db_cv.extracted_text
    assert Path(db_cv.file_path).exists()
    assert Path(db_cv.file_path).parent == isolate_upload_root.resolve()
    assert Path(db_cv.file_path).name.endswith(".pdf")
    # UUID filename
    uuid.UUID(Path(db_cv.file_path).stem)


def test_upload_multipage_pdf(client):
    headers = register_and_login(client)
    pdf = make_pdf_bytes("Multi page CV content", pages=3)
    response = client.post("/api/v1/cvs", headers=headers, files={"file": ("multi.pdf", pdf, "application/pdf")})
    assert response.status_code == 201
    text = response.json()["data"]["cv"]["extracted_text"]
    assert "Page 1" in text and "Page 3" in text


def test_upload_pdf_without_text(client):
    headers = register_and_login(client)
    pdf = make_empty_text_pdf_bytes()
    response = client.post("/api/v1/cvs", headers=headers, files={"file": ("scan.pdf", pdf, "application/pdf")})
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert "khong trich xuat duoc" in body["message"].lower()
    assert (body["data"]["cv"]["extracted_text"] or "") == ""


def test_upload_file_too_large(client, isolate_upload_root):
    headers = register_and_login(client)
    oversized = b"%PDF-" + (b"a" * (5 * 1024 * 1024 + 1))
    response = client.post("/api/v1/cvs", headers=headers, files={"file": ("big.pdf", oversized, "application/pdf")})
    assert response.status_code == 400
    assert "5MB" in response.json()["detail"]
    assert list(isolate_upload_root.glob("*.pdf")) == []


def test_upload_empty_file(client):
    headers = register_and_login(client)
    response = client.post("/api/v1/cvs", headers=headers, files={"file": ("empty.pdf", b"", "application/pdf")})
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_docx_rejected(client):
    headers = register_and_login(client)
    response = client.post(
        "/api/v1/cvs",
        headers=headers,
        files={"file": ("resume.docx", b"PK\x03\x04fake", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 400


def test_upload_renamed_txt_to_pdf_rejected(client):
    headers = register_and_login(client)
    response = client.post(
        "/api/v1/cvs",
        headers=headers,
        files={"file": ("resume.pdf", b"just plain text, not a pdf", "application/pdf")},
    )
    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


def test_upload_fake_pdf_magic_bytes_missing(client):
    headers = register_and_login(client)
    response = client.post(
        "/api/v1/cvs",
        headers=headers,
        files={"file": ("resume.pdf", b"NOTPDF-1.7 garbage", "application/pdf")},
    )
    assert response.status_code == 400


def test_upload_corrupted_pdf(client):
    headers = register_and_login(client)
    corrupted = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\ntruncated and broken"
    response = client.post("/api/v1/cvs", headers=headers, files={"file": ("bad.pdf", corrupted, "application/pdf")})
    assert response.status_code == 400


def test_upload_requires_auth(client):
    pdf = make_pdf_bytes()
    response = client.post("/api/v1/cvs", files={"file": ("resume.pdf", pdf, "application/pdf")})
    assert response.status_code == 401


def test_upload_invalid_token(client):
    pdf = make_pdf_bytes()
    response = client.post(
        "/api/v1/cvs",
        headers={"Authorization": "Bearer invalid-token"},
        files={"file": ("resume.pdf", pdf, "application/pdf")},
    )
    assert response.status_code == 401


def test_upload_expired_token(client):
    from datetime import timedelta

    from app.core.security import create_access_token

    pdf = make_pdf_bytes()
    expired = create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-5))
    response = client.post(
        "/api/v1/cvs",
        headers={"Authorization": f"Bearer {expired}"},
        files={"file": ("resume.pdf", pdf, "application/pdf")},
    )
    assert response.status_code == 401


def test_cv_linked_to_correct_user(client, db_session):
    headers_a = register_and_login(client, "a_cv@example.com")
    headers_b = register_and_login(client, "b_cv@example.com")
    pdf = make_pdf_bytes()
    res_a = client.post("/api/v1/cvs", headers=headers_a, files={"file": ("a.pdf", pdf, "application/pdf")})
    res_b = client.post("/api/v1/cvs", headers=headers_b, files={"file": ("b.pdf", make_pdf_bytes("B content"), "application/pdf")})
    assert res_a.status_code == 201 and res_b.status_code == 201
    cvs = db_session.query(CV).order_by(CV.id).all()
    assert len(cvs) == 2
    users = db_session.query(User).order_by(User.id).all()
    by_email = {u.email: u.id for u in users}
    assert cvs[0].user_id == by_email["a_cv@example.com"]
    assert cvs[1].user_id == by_email["b_cv@example.com"]


def test_no_db_record_on_extraction_failure(client, db_session, isolate_upload_root, monkeypatch):
    headers = register_and_login(client)
    pdf = make_pdf_bytes()

    def boom(_path):
        raise cv_service.HTTPException(status_code=400, detail="Unable to read or extract text from PDF")

    monkeypatch.setattr(cv_service, "extract_pdf_text", boom)
    response = client.post("/api/v1/cvs", headers=headers, files={"file": ("resume.pdf", pdf, "application/pdf")})
    assert response.status_code == 400
    assert db_session.query(CV).count() == 0
    assert list(isolate_upload_root.glob("*.pdf")) == []


def test_db_error_cleans_up_file(client, db_session, isolate_upload_root, monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError

    headers = register_and_login(client)
    pdf = make_pdf_bytes()

    original_commit = db_session.commit

    def failing_commit():
        raise SQLAlchemyError("db fail")

    monkeypatch.setattr(db_session, "commit", failing_commit)
    response = client.post("/api/v1/cvs", headers=headers, files={"file": ("resume.pdf", pdf, "application/pdf")})
    assert response.status_code == 500
    assert list(isolate_upload_root.glob("*.pdf")) == []


def test_stored_file_uses_uuid_and_not_public(client, isolate_upload_root):
    headers = register_and_login(client)
    pdf = make_pdf_bytes()
    response = client.post("/api/v1/cvs", headers=headers, files={"file": ("../../evil.pdf", pdf, "application/pdf")})
    assert response.status_code == 201
    files = list(isolate_upload_root.glob("*.pdf"))
    assert len(files) == 1
    uuid.UUID(files[0].stem)
    assert "static" not in str(files[0]).lower()
    assert "public" not in str(files[0]).lower()
    assert files[0].name != "evil.pdf"


def test_non_pdf_extension_rejected(client):
    headers = register_and_login(client)
    pdf = make_pdf_bytes()
    response = client.post("/api/v1/cvs", headers=headers, files={"file": ("resume.txt", pdf, "application/pdf")})
    assert response.status_code == 400
