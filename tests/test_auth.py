import jwt
import pytest
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.models.user import User


def _register_payload(email: str = "student@example.com", password: str = "StrongPass123") -> dict:
    return {"email": email, "password": password}


def test_register_success(client, db_session):
    response = client.post("/api/v1/auth/register", json=_register_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["user"]["email"] == "student@example.com"
    assert body["data"]["user"]["role"] == "student"
    assert body["data"]["user"]["is_active"] is True
    assert "password_hash" not in str(body)

    user = db_session.query(User).filter_by(email="student@example.com").first()
    assert user is not None
    assert user.password_hash != "StrongPass123"
    assert user.password_hash.startswith("$2")


def test_register_duplicate_email(client):
    first = client.post("/api/v1/auth/register", json=_register_payload())
    assert first.status_code == 201
    second = client.post("/api/v1/auth/register", json=_register_payload())
    assert second.status_code == 400
    assert second.json()["detail"] == "Email already registered"


def test_register_invalid_email(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "StrongPass123"},
    )
    assert response.status_code == 422
    assert response.json()["success"] is False
    assert response.json()["data"] is None
    assert response.json()["message"] == "Request validation failed"
    assert all("input" not in error for error in response.json()["detail"])


def test_register_invalid_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "short@example.com", "password": "short"},
    )
    assert response.status_code == 422


def test_password_is_stored_as_bcrypt_hash(db_session):
    hashed = hash_password("StrongPass123")
    assert hashed.startswith("$2")
    assert hashed != "StrongPass123"
    assert verify_password("StrongPass123", hashed) is True
    assert verify_password("WrongPass123", hashed) is False

    user = User(
        email="hashcheck@example.com",
        password_hash=hashed,
        role="student",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    assert user.password_hash.startswith("$2")


def test_login_success(client):
    client.post("/api/v1/auth/register", json=_register_payload())
    response = client.post("/api/v1/auth/login", json=_register_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["token_type"] == "bearer"
    assert isinstance(body["data"]["access_token"], str) and body["data"]["access_token"]


def test_login_wrong_password(client):
    client.post("/api/v1/auth/register", json=_register_payload())
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "student@example.com", "password": "WrongPass123"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_login_nonexistent_email(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "StrongPass123"},
    )
    assert response.status_code == 401


def test_login_inactive_account(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload("inactive@example.com"))
    user = db_session.query(User).filter_by(email="inactive@example.com").first()
    user.is_active = False
    db_session.commit()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@example.com", "password": "StrongPass123"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Account is inactive"


def test_jwt_valid_token():
    token = create_access_token({"sub": "42"})
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert "exp" in payload


def test_jwt_expired_token(client):
    expired = create_access_token({"sub": "1"}, expires_delta=__import__("datetime").timedelta(seconds=-5))
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Token has expired"


def test_jwt_invalid_token(client):
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_jwt_invalid_signature(client):
    settings = get_settings()
    bad = jwt.encode(
        {"sub": "1"},
        "wrong-signature-secret-key-at-least-32-bytes",
        algorithm=settings.jwt_algorithm,
    )
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bad}"})
    assert response.status_code == 401


def test_me_with_valid_token(client):
    client.post("/api/v1/auth/register", json=_register_payload())
    login = client.post("/api/v1/auth/login", json=_register_payload())
    token = login.json()["data"]["access_token"]
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["email"] == "student@example.com"
    assert "password_hash" not in str(body)


def test_me_without_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_expired_token(client):
    expired = create_access_token({"sub": "1"}, expires_delta=__import__("datetime").timedelta(seconds=-5))
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


def test_me_cannot_access_other_user_info(client):
    client.post("/api/v1/auth/register", json=_register_payload("user1@example.com"))
    client.post("/api/v1/auth/register", json=_register_payload("user2@example.com"))
    login1 = client.post("/api/v1/auth/login", json=_register_payload("user1@example.com"))
    token1 = login1.json()["data"]["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token1}"})
    assert me.status_code == 200
    assert me.json()["data"]["email"] == "user1@example.com"
    # No endpoint accepts user selection in Task 1; identity is derived from token only.


def test_cors_allows_configured_origin_only():
    from fastapi.testclient import TestClient

    from app.core.config import Settings
    from app.main import create_app

    cors_app = create_app(
        Settings(
            secret_key="test-cors-secret-key-that-is-at-least-32-bytes",
            cors_allowed_origins=["https://frontend.example"],
        )
    )
    with TestClient(cors_app) as cors_client:
        allowed = cors_client.options(
            "/api/v1/auth/me",
            headers={
                "Origin": "https://frontend.example",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
        denied = cors_client.options(
            "/api/v1/auth/me",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "https://frontend.example"
    assert "access-control-allow-origin" not in denied.headers


def test_security_settings_reject_weak_secret_and_wildcard_cors(monkeypatch):
    from app.core.config import Settings

    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(secret_key="short")
    with pytest.raises(ValidationError, match="CORS origin"):
        Settings(
            secret_key="test-settings-secret-key-that-is-at-least-32-bytes",
            cors_allowed_origins=["*"],
        )
    with pytest.raises(ValidationError, match="explicitly configured"):
        Settings(environment="production")
    assert Settings(
        environment="production",
        secret_key="test-production-secret-key-that-is-at-least-32-bytes",
    ).environment == "production"


def test_unexpected_errors_use_the_api_error_envelope(caplog):
    from fastapi.testclient import TestClient

    from app.core.config import Settings
    from app.main import create_app

    error_app = create_app(
        Settings(secret_key="test-api-errors-secret-key-that-is-at-least-32-bytes")
    )

    @error_app.get("/intentional-test-error")
    def raise_test_error():
        raise RuntimeError("private diagnostic detail")

    with TestClient(error_app, raise_server_exceptions=False) as error_client:
        response = error_client.get("/intentional-test-error")

    assert response.status_code == 500
    assert response.json() == {
        "success": False,
        "data": None,
        "message": "Internal server error",
        "detail": "Internal server error",
    }
    assert "private diagnostic detail" not in response.text
    assert "Unhandled request error" in caplog.text
