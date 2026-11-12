"""Kiểm thử giao diện đăng nhập/đăng ký (UI-01) và tệp tĩnh liên quan."""


def test_login_page_is_served(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert "la bàn" in response.text
    assert 'id="loginForm"' in response.text
    assert 'id="email"' in response.text
    assert 'id="password"' in response.text
    assert 'href="/register"' in response.text
    assert "Đăng nhập" in response.text


def test_register_page_is_served(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert "la bàn" in response.text
    assert 'id="registerForm"' in response.text
    assert 'id="email"' in response.text
    assert 'id="password"' in response.text
    assert 'id="confirmPassword"' in response.text
    assert 'href="/login"' in response.text
    assert "Đăng ký" in response.text


def test_auth_assets_are_served(client):
    for path in ("/static/auth.css", "/static/auth.js", "/static/session.js"):
        assert client.get(path).status_code == 200


def test_auth_script_targets_public_auth_endpoints(client):
    script = client.get("/static/auth.js").text
    assert "/api/v1/auth/register" in script
    assert "/api/v1/auth/login" in script
    assert "acm_access_token" in script
    assert "acm_refresh_token" in script
    assert "/api/v1/auth/refresh" in client.get("/static/session.js").text
    assert "/api/v1/auth/logout" in client.get("/static/session.js").text


def test_auth_pages_load_session_refresh_support(client):
    for path in ("/login", "/register"):
        page = client.get(path).text
        assert "/static/session.js" in page
        assert "/static/auth.js" in page


def test_internal_pages_require_session_and_load_guard(client):
    for path in ("/profile", "/cv", "/analysis"):
        response = client.get(path)
        assert response.status_code == 200
        assert 'data-require-auth="true"' in response.text
        assert "/static/session.js" in response.text
        assert 'aria-label="Điều hướng"' in response.text


def test_public_pages_load_session_navigation(client):
    for path in ("/", "/explore"):
        response = client.get(path)
        assert response.status_code == 200
        assert "/static/session.js" in response.text
        assert 'data-require-auth="true"' not in response.text
