import fitz

from app.models.cv import CV
from app.services import ai_service, analysis_service


def register_and_login(client, email: str = "consent@example.com", password: str = "StrongPass123"):
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert reg.status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def make_pdf_bytes(text: str = "Consent CV content") -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def create_cv(client, headers, name: str = "cv.pdf") -> int:
    pdf = make_pdf_bytes()
    res = client.post("/api/v1/cvs", headers=headers, files={"file": (name, pdf, "application/pdf")})
    assert res.status_code == 201
    return res.json()["data"]["cv"]["id"]


def valid_payload(cv_id=None, career_role_id=None, accepted=True, purpose_version="v1"):
    payload = {
        "ai_consent": {"accepted": accepted, "purpose_version": purpose_version},
    }
    if cv_id is not None:
        payload["cv_id"] = cv_id
    if career_role_id is not None:
        payload["career_role_id"] = career_role_id
    return payload


def _install_ai_spy(monkeypatch):
    calls = []

    def spy(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        raise AssertionError("AI provider must not be called in Task 4")

    monkeypatch.setattr(ai_service, "request_skill_gap_analysis", spy)
    return calls


def test_requires_jwt(client, monkeypatch):
    calls = _install_ai_spy(monkeypatch)
    res = client.post("/api/v1/analyses", json=valid_payload())
    assert res.status_code == 401
    assert calls == []


def test_invalid_token_rejected(client, monkeypatch):
    calls = _install_ai_spy(monkeypatch)
    res = client.post(
        "/api/v1/analyses",
        headers={"Authorization": "Bearer invalid"},
        json=valid_payload(),
    )
    assert res.status_code == 401
    assert calls == []


def test_missing_consent_rejected(client, monkeypatch):
    headers = register_and_login(client)
    calls = _install_ai_spy(monkeypatch)
    res = client.post("/api/v1/analyses", headers=headers, json={"cv_id": 1})
    assert res.status_code == 422
    assert calls == []


def test_consent_not_accepted_rejected(client, monkeypatch):
    headers = register_and_login(client)
    calls = _install_ai_spy(monkeypatch)
    res = client.post("/api/v1/analyses", headers=headers, json=valid_payload(accepted=False))
    assert res.status_code == 403
    body = res.json()
    assert body["detail"]["data"]["code"] == "AI_CONSENT_REQUIRED"
    assert calls == []


def test_consent_version_mismatch_rejected(client, monkeypatch):
    headers = register_and_login(client)
    calls = _install_ai_spy(monkeypatch)
    res = client.post(
        "/api/v1/analyses",
        headers=headers,
        json=valid_payload(purpose_version="v999"),
    )
    assert res.status_code == 422
    body = res.json()
    assert body["detail"]["data"]["code"] == "AI_CONSENT_VERSION_UNSUPPORTED"
    assert calls == []


def test_cannot_access_other_users_cv(client, monkeypatch):
    headers_a = register_and_login(client, "a_consent@example.com")
    headers_b = register_and_login(client, "b_consent@example.com")
    cv_id_a = create_cv(client, headers_a, "a.pdf")
    calls = _install_ai_spy(monkeypatch)
    res = client.post("/api/v1/analyses", headers=headers_b, json=valid_payload(cv_id=cv_id_a))
    assert res.status_code == 403
    assert res.json()["detail"]["data"]["code"] == "CV_FORBIDDEN"
    assert calls == []


def test_cv_not_found_rejected(client, monkeypatch):
    headers = register_and_login(client)
    calls = _install_ai_spy(monkeypatch)
    res = client.post("/api/v1/analyses", headers=headers, json=valid_payload(cv_id=999999))
    assert res.status_code == 404
    assert res.json()["detail"]["data"]["code"] == "CV_NOT_FOUND"
    assert calls == []


def test_inactive_cv_rejected(client, db_session, monkeypatch):
    headers = register_and_login(client, "inactive_cv@example.com")
    cv_id = create_cv(client, headers, "inactive.pdf")
    cv = db_session.query(CV).filter_by(id=cv_id).first()
    cv.is_active = False
    db_session.commit()
    calls = _install_ai_spy(monkeypatch)
    res = client.post("/api/v1/analyses", headers=headers, json=valid_payload(cv_id=cv_id))
    assert res.status_code == 404
    assert res.json()["detail"]["data"]["code"] == "CV_NOT_FOUND"
    assert calls == []


def test_valid_consent_and_ownership_returns_501(client, monkeypatch):
    headers = register_and_login(client)
    cv_id = create_cv(client, headers)
    calls = _install_ai_spy(monkeypatch)
    res = client.post(
        "/api/v1/analyses",
        headers=headers,
        json=valid_payload(cv_id=cv_id, career_role_id=2),
    )
    assert res.status_code == 501
    body = res.json()
    detail = body["detail"]
    assert detail["success"] is False
    assert detail["data"]["code"] == "ANALYSIS_PIPELINE_NOT_IMPLEMENTED"
    assert "consent" in detail["message"].lower()
    assert "analysis_id" not in str(body)
    assert calls == []


def test_valid_consent_without_cv_returns_501(client, monkeypatch):
    headers = register_and_login(client)
    calls = _install_ai_spy(monkeypatch)
    res = client.post("/api/v1/analyses", headers=headers, json=valid_payload())
    assert res.status_code == 501
    assert res.json()["detail"]["data"]["code"] == "ANALYSIS_PIPELINE_NOT_IMPLEMENTED"
    assert calls == []


def test_consent_check_runs_before_ownership(client, monkeypatch):
    headers_a = register_and_login(client, "owner_a@example.com")
    headers_b = register_and_login(client, "owner_b@example.com")
    cv_id_a = create_cv(client, headers_a, "owner.pdf")
    calls = _install_ai_spy(monkeypatch)

    ownership_called = {"value": False}

    def ownership_spy(*args, **kwargs):
        ownership_called["value"] = True
        return original(*args, **kwargs)

    original = analysis_service.get_owned_active_cv
    monkeypatch.setattr(analysis_service, "get_owned_active_cv", ownership_spy)

    res = client.post(
        "/api/v1/analyses",
        headers=headers_b,
        json=valid_payload(cv_id=cv_id_a, accepted=False),
    )
    assert res.status_code == 403
    assert res.json()["detail"]["data"]["code"] == "AI_CONSENT_REQUIRED"
    assert ownership_called["value"] is False
    assert calls == []


def test_extra_consent_fields_rejected(client, monkeypatch):
    headers = register_and_login(client)
    calls = _install_ai_spy(monkeypatch)
    payload = valid_payload()
    payload["ai_consent"]["unexpected"] = "x"
    res = client.post("/api/v1/analyses", headers=headers, json=payload)
    assert res.status_code == 422
    assert calls == []
