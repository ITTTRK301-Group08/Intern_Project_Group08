"""Kiểm thử hồi quy UX/UI đảm bảo giao diện không rò rỉ thuật ngữ/thành phần backend."""


def test_user_facing_pages_hide_backend_artifacts(client):
    for path in ("/", "/explore", "/profile", "/cv", "/analysis", "/interview", "/roadmap", "/dashboard", "/admin", "/login", "/register"):
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
    assert "$('resourceTypeFilter').value = ''" in explore_js
    assert "$('resourceRoleFilter').value = ''" in explore_js


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
    assert 'id="cvSelect"' in analysis_html
    assert 'id="roleSelect"' in analysis_html
    assert 'id="sourceCvBtn"' in analysis_html
    assert 'id="sourceProfileBtn"' in analysis_html
    assert 'id="consentModal"' in analysis_html
    assert 'id="cv_id"' in analysis_html
    assert 'id="career_role_id"' in analysis_html
    assert "pipeline" not in analysis_html.lower()


def test_analysis_assets_have_no_unresolved_merge_markers(client):
    for path in ("/analysis", "/static/analysis.js"):
        content = client.get(path).text
        assert "Temporary merge branch" not in content
        assert "<<<<<<<" not in content
        assert ">>>>>>>" not in content


def test_project_branding_is_career_mentor_everywhere(client):
    for path in ("/", "/explore", "/profile", "/cv", "/analysis", "/interview", "/roadmap", "/dashboard", "/admin", "/login", "/register"):
        html = client.get(path).text
        assert "Career Mentor" in html
        assert "careerpilot" not in html.lower()
        assert "la bàn" not in html.lower()

    for path in ("/static/admin.js", "/static/roadmap.js"):
        script = client.get(path).text
        assert "careerpilot" not in script.lower()
        assert "la bàn" not in script.lower()
