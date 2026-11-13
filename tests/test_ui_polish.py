"""Kiểm thử hồi quy UX/UI đảm bảo giao diện không rò rỉ thuật ngữ/thành phần backend."""


def test_user_facing_pages_hide_backend_artifacts(client):
    for path in ("/", "/explore", "/profile", "/cv", "/analysis", "/login", "/register"):
        html = client.get(path).text
        assert 'href="/docs"' not in html
        assert "M2 - Student Profile" not in html
        assert "(AI Consent)" not in html
        assert "Task 4" not in html
        assert 'id="resultJson"' not in html
        assert "bcrypt" not in html.lower()
        assert "Swagger" not in html


def test_explore_hides_raw_weight_notation_and_keeps_filters(client):
    explore_html = client.get("/explore").text
    assert 'class="journey-strip"' in explore_html
    assert 'class="view-tabs"' in explore_html
    assert 'id="resetFilters"' in explore_html
    assert "Trọng số" not in explore_html

    explore_js = client.get("/static/explore.js").text
    assert "w=" not in explore_js
    assert "Đã tải dữ liệu nghề nghiệp" not in explore_js


def test_profile_cv_analysis_expose_user_friendly_controls(client):
    profile_html = client.get("/profile").text
    assert '<select id="target_role_id"' in profile_html
    assert 'id="catalogSkillsSuggestions"' in profile_html
    assert 'id="profileCompletenessBar"' in profile_html

    cv_html = client.get("/cv").text
    assert 'id="cvDropzone"' in cv_html
    assert 'id="deleteConfirmModal"' in cv_html
    assert 'id="analyzeWithCvLink"' in cv_html
    assert "xóa mềm" not in cv_html.lower()

    analysis_html = client.get("/analysis").text
    assert 'id="cv_id" name="cv_id" type="hidden"' in analysis_html
    assert 'id="career_role_id" name="career_role_id" type="hidden"' in analysis_html
    assert 'id="cvSelect"' in analysis_html
    assert 'id="roleSelect"' in analysis_html
    assert 'id="sourceCvBtn"' in analysis_html
    assert 'id="sourceProfileBtn"' in analysis_html
    assert "pipeline" not in analysis_html.lower()
