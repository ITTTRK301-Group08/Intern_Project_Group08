"""Kiểm thử giao diện Admin dùng dữ liệu thật, không phải dữ liệu mô phỏng."""

import re


ADMIN_IDS = (
    "adminFeedback",
    "adminAccessDenied",
    "adminAuthorizedContent",
    "kickSeconds",
    "statTotalUsers",
    "statUserBreakdown",
    "statTotalAnalyses",
    "statTotalInterviews",
    "statRolesCount",
    "statCategoriesCount",
    "statSkillsCount",
    "statResourcesCount",
    "statResourcesBreakdown",
    "tabContentRoles",
    "tabContentCategories",
    "tabContentSkills",
    "tabContentResources",
    "tabContentUsers",
    "searchRolesInput",
    "searchCategoriesInput",
    "searchSkillsInput",
    "searchResourcesInput",
    "searchUsersInput",
    "filterRolesCategory",
    "filterRolesLevel",
    "filterRolesActive",
    "filterSkillsActive",
    "filterResourcesType",
    "filterResourcesApproval",
    "filterResourcesActive",
    "filterUsersRole",
    "filterUsersStatus",
    "rolesTableBody",
    "categoriesTableBody",
    "skillsTableBody",
    "resourcesTableBody",
    "usersTableBody",
    "rolesPageInfo",
    "categoriesPageInfo",
    "skillsPageInfo",
    "resourcesPageInfo",
    "usersPageInfo",
    "roleSkillPicker",
    "btnAddRoleSkill",
    "roleSkillsList",
    "resourceFormLanguage",
    "resourceFormActive",
    "detailModal",
    "detailModalTitle",
    "detailModalBody",
)

ADMIN_ENDPOINTS = (
    "/api/v1/admin/stats",
    "/api/v1/admin/users",
    "/api/v1/admin/career-categories",
    "/api/v1/admin/career-roles",
    "/api/v1/admin/skills",
    "/api/v1/admin/resources",
)

STAT_FIELDS = (
    "total_users",
    "total_active_users",
    "total_locked_users",
    "total_analyses",
    "total_interviews",
    "total_categories",
    "total_roles",
    "total_skills",
    "total_resources",
    "total_pending_resources",
)


def test_admin_html_exposes_all_management_controls(client):
    html = client.get("/admin").text

    for element_id in ADMIN_IDS:
        assert 'id="%s"' % element_id in html, element_id

    for tab in ("roles", "categories", "skills", "resources", "users"):
        assert 'data-tab="%s"' % tab in html

    for tab in ("roles", "categories", "skills", "resources", "users"):
        assert 'data-page="%s" data-dir="prev"' % tab in html
        assert 'data-page="%s" data-dir="next"' % tab in html


def test_admin_html_has_no_hardcoded_stat_counts(client):
    html = client.get("/admin").text

    assert '<div id="statTotalUsers" class="admin-stat-val">—</div>' in html
    assert '<div id="statRolesCount" class="admin-stat-val">—</div>' in html
    assert not re.search(
        r'id="stat(?:TotalUsers|TotalAnalyses|TotalInterviews|RolesCount|'
        r'CategoriesCount|SkillsCount|ResourcesCount)"[^>]*>[0-9]',
        html,
    )


def test_admin_js_uses_real_api_and_safe_dom_rendering(client):
    script = client.get("/static/admin.js").text

    for endpoint in ADMIN_ENDPOINTS:
        assert endpoint in script, endpoint

    for field in STAT_FIELDS:
        assert field in script, field

    assert "window.fetch" in script
    assert "/api/v1/auth/me" in script
    assert "kickOutNonAdmin" in script
    assert "function setItemStatus" in script
    assert "'detailModal'" in script
    assert "innerHTML" not in script
    assert "catalogData" not in script
    assert "Python Tutorial" not in script
    assert "Machine Learning Crash Course" not in script

    assert "total_pages" in script
    assert "page_size" in script
    assert "required_skills" in script
    assert "related_categories" in script
    assert "language:" in script
    assert "is_active:" in script
    assert "/approval" in script
    assert "/status" in script


def test_admin_js_supports_tab_deep_links(client):
    script = client.get("/static/admin.js").text

    assert "URLSearchParams(window.location.search).get('tab')" in script
    assert "window.location.hash" in script
    assert "searchParams.set('tab'" in script
    assert "data-goto-tab" in script


def test_admin_css_covers_new_management_components(client):
    css = client.get("/static/admin.css").text

    for class_name in (
        "admin-filter-bar",
        "admin-filter-control",
        "admin-table-scroll",
        "admin-table-footer",
        "admin-page-info",
        "admin-pagination",
        "admin-page-btn",
        "admin-state-row",
        "admin-skill-picker-row",
        "admin-skill-list",
        "admin-skill-chip",
        "admin-detail-grid",
        "admin-stat-link",
        "badge-warn",
    ):
        assert class_name in css, class_name
