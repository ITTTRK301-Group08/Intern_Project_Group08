"""Kiểm thử UI-07 (Phỏng vấn thử) ở mức văn bản và an toàn hiển thị.

Không chạy trình duyệt thật; test đọc HTML/CSS/JS do backend phục vụ để bảo đảm
các yêu cầu giao diện, XSS-safe và responsive không bị hồi quy.
"""


def test_interview_page_route_and_assets(client):
    response = client.get("/interview")
    assert response.status_code == 200
    html = response.text

    assert 'data-require-auth="true"' in html
    assert "/static/interview.css" in html
    assert "/static/interview.js" in html
    assert "/static/session.js" in html
    assert 'id="roleSelect"' in html
    assert 'id="createSessionForm"' in html
    assert 'id="questionsContainer"' in html
    assert 'id="completeBtn"' in html
    assert 'id="historyContainer"' in html
    assert 'href="/interview"' in html


def test_interview_nav_shared_across_pages(client):
    for path in (
        "/explore",
        "/profile",
        "/cv",
        "/analysis",
        "/interview",
        "/roadmap",
        "/dashboard",
        "/admin",
    ):
        html = client.get(path).text
        assert 'href="/interview"' in html, f"Thiếu link Phỏng vấn ở {path}"


def test_direct_mode_route_mapping(client):
    script = client.get("/static/session.js").text
    assert "'/interview'" in script
    assert "./interview.html" in script


def test_interview_js_is_xss_safe(client):
    script = client.get("/static/interview.js").text

    # Không dùng innerHTML cho dữ liệu API.
    assert ".innerHTML" not in script
    assert "textContent" in script
    assert "replaceChildren" in script
    assert "createElement" in script

    # Không gửi user_id từ client; backend lấy từ JWT.
    assert "user_id" not in script

    # Có cảnh báo/khóa khi AI đang chấm và chống gửi trùng.
    assert "state.submitting" in script
    assert "AI đang chấm điểm" in script
    assert "completeBtn.disabled = true" in script


def test_interview_js_wires_required_endpoints(client):
    script = client.get("/static/interview.js").text
    assert "'/api/v1/interviews'" in script
    assert "/answers" in script
    assert "/complete" in script
    assert "/api/v1/interviews?page=1&page_size=5" in script
    assert "MAX_ANSWER_LENGTH = 5000" in script
    assert "ai_consent" in script


def test_interview_css_is_responsive(client):
    css = client.get("/static/interview.css").text
    assert "@media (max-width: 980px)" in css
    assert "@media (max-width: 620px)" in css
    assert "@media (max-width: 375px)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert ".interview-layout" in css
    assert "grid-template-columns" in css


def test_dashboard_shows_real_interview_status_and_score(client):
    html = client.get("/dashboard").text
    assert 'href="/interview"' in html
    assert "Bắt đầu phiên phỏng vấn mới" in html
    assert 'href="/analysis" class="btn secondary-btn"' not in html

    script = client.get("/static/dashboard.js").text
    for status in ("ready", "in_progress", "completed", "abandoned", "failed"):
        assert status in script
    assert "INTERVIEW_STATUS_META" in script
    assert "total_score" in script
    assert "answered_count" in script
    assert "plan-status-inprogress" in script
    assert "plan-status-abandoned" in script
