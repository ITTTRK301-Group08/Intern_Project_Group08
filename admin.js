/**
 * Giao diện Quản trị — Career Mentor.
 * Mọi danh sách và số liệu đều được tải từ API Admin thật qua window.fetch.
 * session.js đã bọc fetch để tự làm mới access token khi hết hạn.
 */
(function () {
  'use strict';

  if (window.__LaBanAdminLoaded__) return;
  window.__LaBanAdminLoaded__ = true;

  var PAGE_SIZE = 10;
  var MAX_OPTION_PAGES = 20;
  var isDirectMode = false;
  var TAB_KEYS = ['roles', 'categories', 'skills', 'resources', 'users'];
  var ENDPOINTS = {
    roles: '/api/v1/admin/career-roles',
    categories: '/api/v1/admin/career-categories',
    skills: '/api/v1/admin/skills',
    resources: '/api/v1/admin/resources',
    users: '/api/v1/admin/users'
  };
  var DETAIL_TITLES = {
    roles: 'Chi tiết vị trí nghề nghiệp',
    categories: 'Chi tiết phân nhóm nghề nghiệp',
    resources: 'Chi tiết tài nguyên học tập',
    users: 'Chi tiết người dùng'
  };

  function emptyState() {
    return { page: 1, data: null, loading: false, error: '' };
  }

  var state = {
    roles: emptyState(),
    categories: emptyState(),
    skills: emptyState(),
    resources: emptyState(),
    users: emptyState(),
    options: { categories: [], skills: [], loaded: false },
    requestSeq: {},
    currentTab: 'roles',
    sessionReady: false,
    currentUserId: null
  };
  var editingRoleIsActive = true;

  function $(id) {
    return document.getElementById(id);
  }

  function display(value, fallback) {
    return value === null || value === undefined || value === ''
      ? (fallback === undefined ? '—' : fallback)
      : String(value);
  }

  function clearNode(node) {
    if (!node) return;
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function setText(id, value) {
    var node = $(id);
    if (node) node.textContent = display(value, '—');
  }

  function formatCount(value) {
    var number = Number(value || 0);
    return Number.isFinite(number) ? number.toLocaleString('vi-VN') : String(value);
  }

  function formatDate(value) {
    if (window.LaBanApp && window.LaBanApp.formatDate) {
      return window.LaBanApp.formatDate(value);
    }
    return display(value, '—');
  }

  function showFeedback(message, isError) {
    var box = $('adminFeedback');
    if (!box) return;
    box.textContent = display(message, '');
    box.className = 'status-card ' + (isError ? 'danger' : 'ok');
    box.style.display = 'block';
    window.setTimeout(function () {
      if (box.textContent === message) box.style.display = 'none';
    }, 5000);
  }

  window.closeAllModals = function () {
    ['categoryModal', 'roleModal', 'skillModal', 'resourceModal', 'detailModal'].forEach(function (id) {
      var modal = $(id);
      if (modal) modal.style.display = 'none';
    });
  };

  function getAdminHeaders() {
    var token = window.LaBanApp ? window.LaBanApp.getToken() : '';
    if (isDirectMode || !token) {
      throw new Error('Vui lòng đăng nhập tài khoản Admin để sử dụng tính năng này.');
    }
    return {
      Authorization: 'Bearer ' + token,
      'Content-Type': 'application/json'
    };
  }

  function apiError(body, fallback) {
    if (window.LaBanApp && window.LaBanApp.extractApiError) {
      return window.LaBanApp.extractApiError(body, fallback);
    }
    if (body && typeof body.detail === 'string') return body.detail;
    if (body && typeof body.message === 'string') return body.message;
    return fallback || 'Yêu cầu chưa thể thực hiện.';
  }

  function unwrap(response, fallback) {
    return response.json().catch(function () { return {}; }).then(function (body) {
      if (!response.ok) throw new Error(apiError(body, fallback));
      if (!body || typeof body !== 'object') {
        throw new Error('Phản hồi từ máy chủ không hợp lệ.');
      }
      return body.data;
    });
  }

  function requestJson(path, options, fallback) {
    var headers;
    try {
      headers = getAdminHeaders();
    } catch (error) {
      return Promise.reject(error);
    }
    var init = options || {};
    var merged = { method: init.method || 'GET', headers: headers };
    if (init.body !== undefined) merged.body = init.body;
    return window.fetch(path, merged).then(function (response) {
      return unwrap(response, fallback);
    });
  }

  function buildQuery(params) {
    var query = new URLSearchParams();
    Object.keys(params || {}).forEach(function (key) {
      var value = params[key];
      if (value !== undefined && value !== null && value !== '') {
        query.append(key, String(value));
      }
    });
    var text = query.toString();
    return text ? '?' + text : '';
  }

  function boolFilter(value) {
    return value === '' || value === undefined || value === null ? undefined : value === 'true';
  }

  function safeUrl(value) {
    try {
      var parsed = new URL(String(value), window.location.href);
      if (parsed.protocol === 'http:' || parsed.protocol === 'https:') return parsed.href;
    } catch (_) {}
    return '';
  }

  function badge(text, kind) {
    return el('span', 'badge ' + (kind || 'badge-ok'), text);
  }

  function statusBadge(isActive, activeLabel, inactiveLabel) {
    return badge(
      isActive ? (activeLabel || 'Hoạt động') : (inactiveLabel || 'Tạm ẩn'),
      isActive ? 'badge-ok' : 'badge-muted'
    );
  }

  function actionButton(label, className, handler, disabled, title) {
    var button = el('button', 'admin-action-btn ' + (className || ''), label);
    button.type = 'button';
    if (title) button.title = title;
    if (disabled) {
      button.disabled = true;
      button.title = title || 'Không thể thực hiện trên tài khoản hiện tại';
    } else {
      button.addEventListener('click', handler);
    }
    return button;
  }

  function cell(text, className, strong) {
    var td = el('td', className);
    if (strong) {
      td.appendChild(el('strong', '', display(text, '—')));
    } else {
      td.textContent = display(text, '—');
    }
    return td;
  }

  function actionsCell(buttons) {
    var td = el('td', 'admin-actions');
    buttons.forEach(function (button) {
      if (button) td.appendChild(button);
    });
    return td;
  }

  function stateRow(colspan, message, isError) {
    var tr = document.createElement('tr');
    var td = el('td', 'admin-state-row' + (isError ? ' error' : ''), message);
    td.colSpan = colspan;
    tr.appendChild(td);
    return tr;
  }

  function renderEmpty(tbody, colspan, loading, error) {
    clearNode(tbody);
    if (loading) {
      tbody.appendChild(stateRow(colspan, 'Đang tải dữ liệu từ cơ sở dữ liệu…', false));
      return true;
    }
    if (error) {
      tbody.appendChild(stateRow(colspan, error, true));
      return true;
    }
    return false;
  }

  /* ── Tabs & URL ───────────────────────────────────────────── */

  function initialTabFromLocation() {
    var fromQuery = '';
    try {
      fromQuery = new URLSearchParams(window.location.search).get('tab') || '';
    } catch (_) {}
    var fromHash = (window.location.hash || '').replace(/^#/, '');
    var candidate = fromQuery || fromHash;
    return TAB_KEYS.indexOf(candidate) !== -1 ? candidate : 'roles';
  }

  function syncTabUrl(key) {
    try {
      var url = new URL(window.location.href);
      url.searchParams.set('tab', key);
      url.hash = '';
      window.history.replaceState(null, '', url.pathname + url.search);
    } catch (_) {}
  }

  function selectTab(key, updateUrl) {
    if (TAB_KEYS.indexOf(key) === -1) key = 'roles';
    state.currentTab = key;

    Array.prototype.forEach.call(document.querySelectorAll('.admin-tab-btn'), function (button) {
      var active = button.getAttribute('data-tab') === key;
      if (active) button.classList.add('active');
      else button.classList.remove('active');
      button.setAttribute('aria-selected', active ? 'true' : 'false');
    });

    TAB_KEYS.forEach(function (tabKey) {
      var panel = $('tabContent' + tabKey.charAt(0).toUpperCase() + tabKey.slice(1));
      if (panel) panel.style.display = tabKey === key ? 'block' : 'none';
    });

    if (updateUrl) syncTabUrl(key);
    if (state.sessionReady) loadTab(key);
    else renderTab(key);
  }

  function setupTabs() {
    if (!document.querySelector('.admin-tab-btn')) return;

    Array.prototype.forEach.call(document.querySelectorAll('.admin-tab-btn'), function (button) {
      button.addEventListener('click', function () {
        selectTab(button.getAttribute('data-tab'), true);
      });
    });

    Array.prototype.forEach.call(document.querySelectorAll('[data-goto-tab]'), function (button) {
      button.addEventListener('click', function () {
        selectTab(button.getAttribute('data-goto-tab'), true);
      });
    });

    Array.prototype.forEach.call(document.querySelectorAll('.admin-page-btn'), function (button) {
      button.addEventListener('click', function () {
        var tab = button.getAttribute('data-page');
        var direction = button.getAttribute('data-dir');
        var tabState = state[tab];
        if (!tabState || !tabState.data) return;
        var next = tabState.page + (direction === 'next' ? 1 : -1);
        if (next < 1 || next > tabState.data.total_pages) return;
        tabState.page = next;
        loadTab(tab);
      });
    });

    var searchMap = {
      searchRolesInput: 'roles',
      searchCategoriesInput: 'categories',
      searchSkillsInput: 'skills',
      searchResourcesInput: 'resources',
      searchUsersInput: 'users'
    };
    Object.keys(searchMap).forEach(function (id) {
      var input = $(id);
      if (!input) return;
      input.addEventListener('input', function () {
        var tab = searchMap[id];
        state[tab].search = input.value.trim();
        state[tab].page = 1;
        loadTab(tab);
      });
    });

    var filterMap = {
      filterRolesCategory: { tab: 'roles', key: 'categoryId' },
      filterRolesLevel: { tab: 'roles', key: 'level' },
      filterRolesActive: { tab: 'roles', key: 'isActive' },
      filterSkillsActive: { tab: 'skills', key: 'isActive' },
      filterResourcesType: { tab: 'resources', key: 'resourceType' },
      filterResourcesApproval: { tab: 'resources', key: 'approvalStatus' },
      filterResourcesActive: { tab: 'resources', key: 'isActive' },
      filterUsersRole: { tab: 'users', key: 'role' },
      filterUsersStatus: { tab: 'users', key: 'isActive' }
    };
    Object.keys(filterMap).forEach(function (id) {
      var select = $(id);
      if (!select) return;
      select.addEventListener('change', function () {
        var cfg = filterMap[id];
        state[cfg.tab][cfg.key] = select.value;
        state[cfg.tab].page = 1;
        loadTab(cfg.tab);
      });
    });

    var addMap = {
      btnAddRole: openRoleModal,
      btnAddCategory: openCategoryModal,
      btnAddSkill: openSkillModal,
      btnAddResource: openResourceModal
    };
    Object.keys(addMap).forEach(function (id) {
      var button = $(id);
      if (button) button.addEventListener('click', function () { addMap[id](); });
    });

    var addSkillBtn = $('btnAddRoleSkill');
    if (addSkillBtn) addSkillBtn.addEventListener('click', addRoleSkillFromPicker);
  }

  /* ── Shared option lists ──────────────────────────────────── */

  function fetchAllOptions(path, fallback) {
    var collected = [];
    var page = 1;

    function nextPage() {
      return requestJson(path + buildQuery({ page: page, page_size: 100 }), null, fallback)
        .then(function (data) {
          if (!data || !Array.isArray(data.items)) throw new Error('Phản hồi danh mục không hợp lệ.');
          collected = collected.concat(data.items);
          if (data.total_pages && page < data.total_pages && page < MAX_OPTION_PAGES) {
            page += 1;
            return nextPage();
          }
          return collected;
        });
    }

    return nextPage();
  }

  function loadOptions(force) {
    if (state.options.loaded && !force) return Promise.resolve(state.options);
    return Promise.all([
      fetchAllOptions(ENDPOINTS.categories, 'Không thể tải danh sách phân nhóm.'),
      fetchAllOptions(ENDPOINTS.skills, 'Không thể tải danh sách kỹ năng.')
    ]).then(function (results) {
      state.options.categories = results[0];
      state.options.skills = results[1];
      state.options.loaded = true;
      fillOptionSelects();
      return state.options;
    });
  }

  function ensureOptions(force) {
    return force ? loadOptions(true) : loadOptions(false);
  }

  function fillSelect(select, items, placeholder, placeholderValue) {
    if (!select) return;
    clearNode(select);
    if (placeholder !== undefined) {
      var first = document.createElement('option');
      first.value = placeholderValue === undefined ? '' : placeholderValue;
      first.textContent = placeholder;
      select.appendChild(first);
    }
    (items || []).forEach(function (item) {
      var option = document.createElement('option');
      option.value = item.id;
      option.textContent = item.name;
      select.appendChild(option);
    });
  }

  function fillOptionSelects() {
    fillSelect($('filterRolesCategory'), state.options.categories, 'Tất cả phân nhóm', '');
    fillSelect($('roleFormCategory'), state.options.categories, '-- Chưa phân nhóm --', '');
    fillSelect($('roleSkillPicker'), state.options.skills, '-- Chọn kỹ năng để thêm --', '');
    fillSelect($('resourceFormSkill'), state.options.skills, '-- Không gắn kỹ năng cụ thể --', '');
  }

  /* ── Data loading ─────────────────────────────────────────── */

  function tabQuery(tab) {
    var s = state[tab];
    var params = { page: s.page, page_size: PAGE_SIZE };
    if (s.search) params.search = s.search;
    if (tab === 'roles') {
      if (s.categoryId) params.category_id = s.categoryId;
      if (s.level) params.level = s.level;
      if (s.isActive !== '') params.is_active = boolFilter(s.isActive);
    } else if (tab === 'skills' || tab === 'resources' || tab === 'users') {
      if (s.isActive !== '') params.is_active = boolFilter(s.isActive);
    }
    if (tab === 'resources') {
      if (s.resourceType) params.resource_type = s.resourceType;
      if (s.approvalStatus) params.approval_status = s.approvalStatus;
    }
    if (tab === 'users' && s.role) params.role = s.role;
    return buildQuery(params);
  }

  function loadTab(tab) {
    var s = state[tab];
    if (!s) return Promise.resolve(null);
    var seq = (state.requestSeq[tab] || 0) + 1;
    state.requestSeq[tab] = seq;
    s.loading = true;
    s.error = '';
    renderTab(tab);

    return requestJson(ENDPOINTS[tab] + tabQuery(tab), null, 'Không thể tải dữ liệu.')
      .then(function (data) {
        if (state.requestSeq[tab] !== seq) return null;
        if (!data || !Array.isArray(data.items)) {
          throw new Error('Phản hồi danh sách không hợp lệ.');
        }
        s.data = data;
        if (data.total_pages && s.page > data.total_pages) {
          s.page = data.total_pages;
          return loadTab(tab);
        }
        s.loading = false;
        renderTab(tab);
        return data;
      })
      .catch(function (error) {
        if (state.requestSeq[tab] !== seq) return null;
        s.loading = false;
        s.error = error.message || 'Không thể tải dữ liệu.';
        s.data = null;
        renderTab(tab);
        return null;
      });
  }

  function loadStats() {
    return requestJson('/api/v1/admin/stats', null, 'Không thể tải thống kê hệ thống.')
      .then(function (data) {
        if (!data) throw new Error('Phản hồi thống kê không hợp lệ.');
        setText('statTotalUsers', formatCount(data.total_users));
        setText(
          'statUserBreakdown',
          formatCount(data.total_active_users) + ' hoạt động · ' +
          formatCount(data.total_locked_users) + ' đã khóa'
        );
        setText('statTotalAnalyses', formatCount(data.total_analyses));
        setText('statTotalInterviews', formatCount(data.total_interviews));
        setText('statRolesCount', formatCount(data.total_roles));
        setText('statCategoriesCount', formatCount(data.total_categories));
        setText('statSkillsCount', formatCount(data.total_skills));
        setText('statResourcesCount', formatCount(data.total_resources));
        setText(
          'statResourcesBreakdown',
          formatCount(data.total_pending_resources) + ' chờ duyệt'
        );
      })
      .catch(function (error) {
        showFeedback(error.message || 'Không thể tải thống kê hệ thống.', true);
      });
  }

  function loadSession() {
    var headers;
    try {
      headers = getAdminHeaders();
    } catch (error) {
      showFeedback(error.message, true);
      return Promise.resolve(false);
    }

    return window.fetch('/api/v1/auth/me', { headers: headers })
      .then(function (response) {
        return unwrap(response, 'Không thể xác nhận phiên đăng nhập.');
      })
      .then(function (me) {
        if (!me || me.role !== 'admin') {
          kickOutNonAdmin();
          return false;
        }
        state.currentUserId = me.id || null;
        return true;
      })
      .catch(function (error) {
        showFeedback(error.message || 'Không thể xác nhận phiên đăng nhập.', true);
        return false;
      });
  }

  function refreshView(message, options) {
    var cfg = options || {};
    closeAllModals();
    if (message) showFeedback(message, false);
    var jobs = [loadStats(), loadTab(state.currentTab)];
    if (cfg.options) jobs.push(ensureOptions(true));
    return Promise.all(jobs);
  }

  /* ── Table rendering ──────────────────────────────────────── */

  function renderPagination(tab) {
    var s = state[tab];
    var info = $(tab + 'PageInfo');
    if (info) {
      if (s.loading) info.textContent = 'Đang tải…';
      else if (s.error) info.textContent = s.error;
      else if (!s.data) info.textContent = 'Chưa có dữ liệu.';
      else {
        var total = s.data.total || 0;
        var from = total ? (s.data.page - 1) * s.data.page_size + 1 : 0;
        var to = Math.min(s.data.page * s.data.page_size, total);
        info.textContent = 'Hiển thị ' + from + '–' + to + ' / ' + total +
          ' bản ghi · Trang ' + s.data.page + '/' + s.data.total_pages;
      }
    }
    Array.prototype.forEach.call(
      document.querySelectorAll('.admin-page-btn[data-page="' + tab + '"]'),
      function (button) {
        var dir = button.getAttribute('data-dir');
        var disabled = !s.data || s.loading ||
          (dir === 'prev' ? s.data.page <= 1 : s.data.page >= s.data.total_pages);
        button.disabled = Boolean(disabled);
      }
    );
  }

  function renderTab(tab) {
    switch (tab) {
      case 'roles': renderRolesTable(); break;
      case 'categories': renderCategoriesTable(); break;
      case 'skills': renderSkillsTable(); break;
      case 'resources': renderResourcesTable(); break;
      case 'users': renderUsersTable(); break;
      default: break;
    }
    renderPagination(tab);
  }

  function renderRolesTable() {
    var tbody = $('rolesTableBody');
    if (!tbody) return;
    var s = state.roles;
    if (renderEmpty(tbody, 7, s.loading, s.error)) return;
    var roles = (s.data && s.data.items) || [];
    if (!roles.length) {
      tbody.appendChild(stateRow(7, 'Không tìm thấy vị trí nghề nghiệp phù hợp.', false));
      return;
    }

    roles.forEach(function (role) {
      var tr = document.createElement('tr');
      var categoryName = role.category ? role.category.name : 'Chưa phân nhóm';
      var levelClass = 'level-' + String(role.level || 'junior').toLowerCase().replace(/[^a-z]/g, '');
      var level = el('span', 'level-badge ' + levelClass, display(role.level, 'Junior'));
      var levelCell = el('td');
      levelCell.appendChild(level);

      tr.appendChild(cell('#' + role.id));
      tr.appendChild(cell(role.name, '', true));
      tr.appendChild(levelCell);
      tr.appendChild(cell(categoryName));
      tr.appendChild(cell((role.required_skills || []).length + ' kỹ năng'));
      var statusCell = el('td');
      statusCell.appendChild(statusBadge(role.is_active));
      tr.appendChild(statusCell);
      tr.appendChild(actionsCell([
        actionButton('Chi tiết', 'admin-btn-edit', function () { openDetail('roles', role.id); }),
        actionButton('Sửa', 'admin-btn-edit', function () { openRoleModal(role.id); }),
        actionButton(role.is_active ? 'Ẩn' : 'Hiện', 'admin-btn-toggle', function () {
          setItemStatus('roles', role, role.is_active === false);
        }),
        actionButton('Xóa', 'admin-btn-delete', function () { deleteEntity('roles', role.id); })
      ]));
      tbody.appendChild(tr);
    });
  }

  function renderCategoriesTable() {
    var tbody = $('categoriesTableBody');
    if (!tbody) return;
    var s = state.categories;
    if (renderEmpty(tbody, 6, s.loading, s.error)) return;
    var categories = (s.data && s.data.items) || [];
    if (!categories.length) {
      tbody.appendChild(stateRow(6, 'Không tìm thấy phân nhóm nghề nghiệp phù hợp.', false));
      return;
    }

    categories.forEach(function (category) {
      var tr = document.createElement('tr');
      var slugCell = el('td');
      slugCell.appendChild(el('code', '', display(category.slug, '—')));
      tr.appendChild(cell('#' + category.id));
      tr.appendChild(cell(category.name, '', true));
      tr.appendChild(slugCell);
      tr.appendChild(cell(category.description || 'Chưa có mô tả'));
      tr.appendChild(cell('Xem chi tiết'));
      tr.appendChild(actionsCell([
        actionButton('Chi tiết', 'admin-btn-edit', function () { openDetail('categories', category.id); }),
        actionButton('Sửa', 'admin-btn-edit', function () { openCategoryModal(category.id); }),
        actionButton('Xóa', 'admin-btn-delete', function () { deleteEntity('categories', category.id); })
      ]));
      tbody.appendChild(tr);
    });
  }

  function renderSkillsTable() {
    var tbody = $('skillsTableBody');
    if (!tbody) return;
    var s = state.skills;
    if (renderEmpty(tbody, 5, s.loading, s.error)) return;
    var skills = (s.data && s.data.items) || [];
    if (!skills.length) {
      tbody.appendChild(stateRow(5, 'Không tìm thấy kỹ năng phù hợp.', false));
      return;
    }

    skills.forEach(function (skill) {
      var tr = document.createElement('tr');
      var statusCell = el('td');
      statusCell.appendChild(statusBadge(skill.is_active));
      tr.appendChild(cell('#' + skill.id));
      tr.appendChild(cell(skill.name, '', true));
      tr.appendChild(cell(skill.description || 'Chưa có mô tả'));
      tr.appendChild(statusCell);
      tr.appendChild(actionsCell([
        actionButton('Sửa', 'admin-btn-edit', function () { openSkillModal(skill.id); }),
        actionButton(skill.is_active ? 'Ẩn' : 'Hiện', 'admin-btn-toggle', function () {
          setItemStatus('skills', skill, skill.is_active === false);
        }),
        actionButton('Xóa', 'admin-btn-delete', function () { deleteEntity('skills', skill.id); })
      ]));
      tbody.appendChild(tr);
    });
  }

  var RESOURCE_TYPE_LABELS = {
    documentation: 'Tài liệu',
    course: 'Khóa học',
    video: 'Video',
    article: 'Bài viết',
    practice: 'Thực hành',
    project: 'Dự án'
  };
  var APPROVAL_LABELS = {
    pending: 'Chờ duyệt',
    approved: 'Đã duyệt',
    rejected: 'Từ chối'
  };

  function approvalBadge(status) {
    var kind = status === 'approved' ? 'badge-ok' : status === 'rejected' ? 'badge-muted' : 'badge-warn';
    return badge(APPROVAL_LABELS[status] || APPROVAL_LABELS.pending, kind);
  }

  function renderResourcesTable() {
    var tbody = $('resourcesTableBody');
    if (!tbody) return;
    var s = state.resources;
    if (renderEmpty(tbody, 9, s.loading, s.error)) return;
    var resources = (s.data && s.data.items) || [];
    if (!resources.length) {
      tbody.appendChild(stateRow(9, 'Không tìm thấy tài nguyên học tập phù hợp.', false));
      return;
    }

    resources.forEach(function (resource) {
      var tr = document.createElement('tr');
      var titleCell = el('td');
      var href = safeUrl(resource.url);
      if (href) {
        var link = el('a', '', resource.title);
        link.href = href;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        titleCell.appendChild(link);
      } else {
        titleCell.appendChild(el('strong', '', display(resource.title, '—')));
      }

      var skillCell = el('td');
      skillCell.appendChild(el('span', 'skill-tag', resource.skill ? resource.skill.name : 'Chung'));

      var approvalCell = el('td');
      approvalCell.appendChild(approvalBadge(resource.approval_status));
      approvalCell.appendChild(document.createTextNode(' '));
      approvalCell.appendChild(actionButton(
        resource.approval_status === 'approved' ? 'Từ chối' : 'Duyệt',
        '',
        function () {
          reviewResource(
            resource.id,
            resource.approval_status === 'approved' ? 'rejected' : 'approved'
          );
        }
      ));

      var statusCell = el('td');
      statusCell.appendChild(statusBadge(resource.is_active));

      tr.appendChild(cell('#' + resource.id));
      tr.appendChild(titleCell);
      tr.appendChild(cell(resource.provider));
      tr.appendChild(skillCell);
      tr.appendChild(cell(RESOURCE_TYPE_LABELS[resource.resource_type] || resource.resource_type));
      tr.appendChild(approvalCell);
      tr.appendChild(cell(resource.is_free ? 'Miễn phí' : 'Có phí'));
      tr.appendChild(statusCell);
      tr.appendChild(actionsCell([
        actionButton('Chi tiết', 'admin-btn-edit', function () { openDetail('resources', resource.id); }),
        actionButton('Sửa', 'admin-btn-edit', function () { openResourceModal(resource.id); }),
        actionButton(resource.is_active ? 'Ẩn' : 'Hiện', 'admin-btn-toggle', function () {
          setItemStatus('resources', resource, resource.is_active === false);
        }),
        actionButton('Xóa', 'admin-btn-delete', function () { deleteEntity('resources', resource.id); })
      ]));
      tbody.appendChild(tr);
    });
  }

  function renderUsersTable() {
    var tbody = $('usersTableBody');
    if (!tbody) return;
    var s = state.users;
    if (renderEmpty(tbody, 7, s.loading, s.error)) return;
    var users = (s.data && s.data.items) || [];
    if (!users.length) {
      tbody.appendChild(stateRow(7, 'Không tìm thấy người dùng phù hợp.', false));
      return;
    }

    users.forEach(function (user) {
      var tr = document.createElement('tr');
      var roleCell = el('td', '', user.role === 'admin' ? 'Quản trị viên' : 'Học viên');
      var statusCell = el('td');
      statusCell.appendChild(statusBadge(user.is_active, 'Hoạt động', 'Đã khóa'));
      var isSelf = state.currentUserId !== null && user.id === state.currentUserId;

      tr.appendChild(cell('#' + user.id));
      tr.appendChild(cell(user.email, '', true));
      tr.appendChild(cell(user.full_name || 'Chưa cập nhật'));
      tr.appendChild(roleCell);
      tr.appendChild(statusCell);
      tr.appendChild(cell(formatDate(user.created_at)));
      tr.appendChild(actionsCell([
        actionButton('Chi tiết', 'admin-btn-edit', function () { openDetail('users', user.id); }),
        actionButton(
          user.is_active ? 'Khóa' : 'Mở khóa',
          user.is_active ? 'admin-btn-delete' : 'admin-btn-edit',
          function () { setItemStatus('users', user, user.is_active === false); },
          isSelf,
          isSelf ? 'Không thể khóa tài khoản hiện tại' : ''
        )
      ]));
      tbody.appendChild(tr);
    });
  }

  /* ── Detail modal ─────────────────────────────────────────── */

  function detailRow(list, label, value) {
    var dt = el('dt', 'admin-detail-label', label);
    var dd = el('dd', 'admin-detail-value');
    if (value && value.nodeType) dd.appendChild(value);
    else dd.textContent = display(value, '—');
    list.appendChild(dt);
    list.appendChild(dd);
  }

  function detailList(values, formatter) {
    var ul = el('ul', 'admin-detail-list');
    (values || []).forEach(function (value) {
      ul.appendChild(el('li', '', formatter ? formatter(value) : value));
    });
    if (!ul.firstChild) ul.appendChild(el('li', '', 'Không có dữ liệu'));
    return ul;
  }

  function renderDetail(kind, data) {
    var body = $('detailModalBody');
    if (!body) return;
    clearNode(body);
    var dl = el('dl', 'admin-detail-grid');

    if (kind === 'users') {
      detailRow(dl, 'Email', data.email);
      detailRow(dl, 'Họ tên', data.full_name);
      detailRow(dl, 'Vai trò', data.role === 'admin' ? 'Quản trị viên' : 'Học viên');
      detailRow(dl, 'Trạng thái', data.is_active ? 'Hoạt động' : 'Đã khóa');
      detailRow(dl, 'Lượt phân tích', formatCount(data.total_analyses));
      detailRow(dl, 'Phiên phỏng vấn', formatCount(data.total_interviews));
      var profile = data.profile || {};
      detailRow(dl, 'Chuyên ngành', profile.major);
      detailRow(dl, 'Trường đại học', profile.university);
      detailRow(dl, 'Mục tiêu nghề nghiệp', profile.career_goal);
      detailRow(dl, 'Vị trí mục tiêu', profile.target_role_name);
      detailRow(dl, 'Ngày tạo', formatDate(data.created_at));
      detailRow(dl, 'Cập nhật lần cuối', formatDate(data.updated_at));
    } else if (kind === 'roles') {
      detailRow(dl, 'Tên vị trí', data.name);
      detailRow(dl, 'Slug', data.slug);
      detailRow(dl, 'Cấp độ', data.level);
      detailRow(dl, 'Phân nhóm', data.category ? data.category.name : 'Chưa phân nhóm');
      detailRow(dl, 'Mô tả', data.description);
      detailRow(dl, 'Trạng thái', data.is_active ? 'Hoạt động' : 'Tạm ẩn');
      detailRow(dl, 'Kỹ năng yêu cầu', detailList(data.required_skills, function (item) {
        return item.skill.name + ' · cấp ' + item.required_level +
          ' · hệ số ' + item.weight + (item.is_required ? ' · bắt buộc' : '');
      }));
      detailRow(dl, 'Ngày tạo', formatDate(data.created_at));
    } else if (kind === 'categories') {
      detailRow(dl, 'Tên phân nhóm', data.name);
      detailRow(dl, 'Slug', data.slug);
      detailRow(dl, 'Mô tả', data.description);
      detailRow(dl, 'Số vị trí', formatCount(data.role_count));
      detailRow(dl, 'Các vị trí', detailList(data.roles, function (role) {
        return role.name + ' · ' + role.level + (role.is_active ? '' : ' (tạm ẩn)');
      }));
      detailRow(dl, 'Ngày tạo', formatDate(data.created_at));
    } else if (kind === 'resources') {
      var link = el('a', '', data.url);
      link.href = safeUrl(data.url) || '#';
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      detailRow(dl, 'Tiêu đề', data.title);
      detailRow(dl, 'Slug', data.slug);
      detailRow(dl, 'Nhà cung cấp', data.provider);
      detailRow(dl, 'Liên kết', link);
      detailRow(dl, 'Kỹ năng', data.skill ? data.skill.name : 'Chung');
      detailRow(dl, 'Phân loại', RESOURCE_TYPE_LABELS[data.resource_type] || data.resource_type);
      detailRow(dl, 'Ngôn ngữ', data.language === 'vi' ? 'Tiếng Việt' : 'Tiếng Anh');
      detailRow(dl, 'Chi phí', data.is_free ? 'Miễn phí' : 'Có phí');
      detailRow(dl, 'Kiểm duyệt', APPROVAL_LABELS[data.approval_status] || data.approval_status);
      detailRow(dl, 'Trạng thái', data.is_active ? 'Hoạt động' : 'Tạm ẩn');
      detailRow(dl, 'Mô tả', data.description);
      detailRow(dl, 'Nhóm liên quan', detailList(data.related_categories, function (item) {
        return item.name;
      }));
      detailRow(dl, 'Ngày tạo', formatDate(data.created_at));
    }

    body.appendChild(dl);
  }

  function openDetail(kind, id) {
    var modal = $('detailModal');
    var body = $('detailModalBody');
    if (!modal || !body) return;
    setText('detailModalTitle', DETAIL_TITLES[kind] || 'Chi tiết');
    clearNode(body);
    body.appendChild(el('p', 'admin-detail-loading', 'Đang tải chi tiết…'));
    modal.style.display = 'flex';

    requestJson(ENDPOINTS[kind] + '/' + id, null, 'Không thể tải chi tiết bản ghi.')
      .then(function (data) {
        if (!data) throw new Error('Không có dữ liệu chi tiết.');
        renderDetail(kind, data);
      })
      .catch(function (error) {
        clearNode(body);
        body.appendChild(el('p', 'admin-detail-error', error.message || 'Không thể tải chi tiết bản ghi.'));
      });
  }

  /* ── CRUD forms ───────────────────────────────────────────── */

  function submitForm(form, task) {
    if (!form) return Promise.resolve(null);
    var submit = form.querySelector('[type="submit"]');
    if (submit) submit.disabled = true;
    return Promise.resolve()
      .then(task)
      .catch(function (error) {
        showFeedback(error.message || 'Không thể lưu dữ liệu.', true);
        return null;
      })
      .then(function (result) {
        if (submit) submit.disabled = false;
        return result;
      });
  }

  function saveEntity(method, path, payload, fallback, successMessage, refreshOptions) {
    return requestJson(path, {
      method: method,
      body: JSON.stringify(payload)
    }, fallback).then(function () {
      return refreshView(successMessage, { options: Boolean(refreshOptions) });
    });
  }

  function openCategoryModal(categoryId) {
    var modal = $('categoryModal');
    if (!modal) return;
    var form = $('categoryForm');
    if (form) form.reset();
    if (categoryId) {
      var category = null;
      var items = (state.categories.data && state.categories.data.items) || [];
      items.some(function (item) { if (item.id === categoryId) category = item; return Boolean(category); });
      if (!category) {
        showFeedback('Không tìm thấy phân nhóm cần chỉnh sửa.', true);
        return;
      }
      setText('categoryModalTitle', 'Chỉnh sửa phân nhóm #' + category.id);
      $('categoryFormId').value = category.id;
      $('categoryFormName').value = category.name || '';
      $('categoryFormSlug').value = category.slug || '';
      $('categoryFormDesc').value = category.description || '';
    } else {
      setText('categoryModalTitle', 'Thêm phân nhóm nghề nghiệp');
      $('categoryFormId').value = '';
    }
    modal.style.display = 'flex';
  }

  function openSkillModal(skillId) {
    var modal = $('skillModal');
    if (!modal) return;
    var form = $('skillForm');
    if (form) form.reset();
    if (skillId) {
      var skill = null;
      var items = (state.skills.data && state.skills.data.items) || [];
      items.some(function (item) { if (item.id === skillId) skill = item; return Boolean(skill); });
      if (!skill) {
        showFeedback('Không tìm thấy kỹ năng cần chỉnh sửa.', true);
        return;
      }
      setText('skillModalTitle', 'Chỉnh sửa kỹ năng #' + skill.id);
      $('skillFormId').value = skill.id;
      $('skillFormName').value = skill.name || '';
      $('skillFormDesc').value = skill.description || '';
    } else {
      setText('skillModalTitle', 'Thêm kỹ năng chuẩn');
      $('skillFormId').value = '';
    }
    modal.style.display = 'flex';
  }

  function roleSkillRow(skill, requiredLevel, isRequired, weight) {
    var row = el('div', 'admin-skill-chip');
    row.setAttribute('data-role-skill-id', skill.id);

    var name = el('span', 'admin-skill-chip-name', skill.name);
    var level = document.createElement('select');
    level.className = 'admin-form-control admin-skill-chip-level';
    level.setAttribute('data-field', 'required_level');
    level.setAttribute('aria-label', 'Cấp độ yêu cầu cho ' + skill.name);
    for (var i = 0; i <= 5; i += 1) {
      var option = document.createElement('option');
      option.value = i;
      option.textContent = 'Cấp ' + i;
      level.appendChild(option);
    }
    level.value = requiredLevel === undefined ? 3 : requiredLevel;

    var weightInput = document.createElement('input');
    weightInput.type = 'number';
    weightInput.className = 'admin-form-control admin-skill-chip-weight';
    weightInput.setAttribute('data-field', 'weight');
    weightInput.setAttribute('aria-label', 'Trọng số cho ' + skill.name);
    weightInput.min = '0.5';
    weightInput.max = '5';
    weightInput.step = '0.5';
    weightInput.value = weight === undefined ? 1 : weight;

    var requiredLabel = el('label', 'admin-skill-chip-check');
    var checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.setAttribute('data-field', 'is_required');
    checkbox.checked = isRequired !== false;
    requiredLabel.appendChild(checkbox);
    requiredLabel.appendChild(document.createTextNode(' Bắt buộc'));

    var removeBtn = actionButton('✕', 'admin-skill-chip-remove', function () {
      row.parentNode.removeChild(row);
    }, false, 'Bỏ kỹ năng này');

    row.append(name, level, weightInput, requiredLabel, removeBtn);
    return row;
  }

  function addRoleSkill(skill, requiredLevel, isRequired, weight) {
    var list = $('roleSkillsList');
    if (!list || !skill) return;
    var existing = list.querySelector('[data-role-skill-id="' + skill.id + '"]');
    if (existing) {
      showFeedback('Kỹ năng này đã có trong danh sách yêu cầu.', true);
      return;
    }
    list.appendChild(roleSkillRow(skill, requiredLevel, isRequired, weight));
  }

  function addRoleSkillFromPicker() {
    var picker = $('roleSkillPicker');
    if (!picker || !picker.value) {
      showFeedback('Vui lòng chọn kỹ năng để thêm.', true);
      return;
    }
    var id = Number(picker.value);
    var skill = null;
    state.options.skills.some(function (item) { if (item.id === id) skill = item; return Boolean(skill); });
    addRoleSkill(skill);
  }

  function collectRoleSkills() {
    var list = $('roleSkillsList');
    if (!list) return [];
    var rows = list.querySelectorAll('[data-role-skill-id]');
    return Array.prototype.map.call(rows, function (row) {
      var levelNode = row.querySelector('[data-field="required_level"]');
      var weightNode = row.querySelector('[data-field="weight"]');
      var requiredNode = row.querySelector('[data-field="is_required"]');
      var weight = Number(weightNode ? weightNode.value : 1);
      if (!Number.isFinite(weight) || weight <= 0) weight = 1;
      return {
        skill_id: Number(row.getAttribute('data-role-skill-id')),
        required_level: Number(levelNode ? levelNode.value : 3),
        is_required: requiredNode ? requiredNode.checked : true,
        weight: weight
      };
    });
  }

  function openRoleModal(roleId) {
    var modal = $('roleModal');
    if (!modal) return;
    var form = $('roleForm');
    if (form) form.reset();
    var skillList = $('roleSkillsList');
    if (skillList) clearNode(skillList);
    $('roleFormId').value = '';

    ensureOptions(false).then(function () {
      if (!roleId) {
        editingRoleIsActive = true;
        setText('roleModalTitle', 'Thêm vị trí nghề nghiệp');
        $('roleFormLevel').value = 'Junior';
        modal.style.display = 'flex';
        return null;
      }
      return requestJson(ENDPOINTS.roles + '/' + roleId, null, 'Không thể tải chi tiết vị trí nghề nghiệp.')
        .then(function (role) {
          if (!role) throw new Error('Không có dữ liệu vị trí nghề nghiệp.');
          editingRoleIsActive = role.is_active !== false;
          setText('roleModalTitle', 'Chỉnh sửa vị trí nghề nghiệp #' + role.id);
          $('roleFormId').value = role.id;
          $('roleFormName').value = role.name || '';
          $('roleFormLevel').value = role.level || 'Junior';
          $('roleFormSlug').value = role.slug || '';
          $('roleFormCategory').value = role.category_id || '';
          $('roleFormDesc').value = role.description || '';
          (role.required_skills || []).forEach(function (item) {
            addRoleSkill(
              item.skill,
              item.required_level,
              item.is_required,
              item.weight
            );
          });
          modal.style.display = 'flex';
        });
    }).catch(function (error) {
      showFeedback(error.message || 'Không thể mở form vị trí nghề nghiệp.', true);
    });
  }

  function openResourceModal(resourceId) {
    var modal = $('resourceModal');
    if (!modal) return;
    var form = $('resourceForm');
    if (form) form.reset();
    $('resourceFormId').value = '';

    ensureOptions(false).then(function () {
      if (!resourceId) {
        setText('resourceModalTitle', 'Thêm tài nguyên học tập');
        $('resourceFormLanguage').value = 'en';
        $('resourceFormFree').value = 'true';
        $('resourceFormActive').value = 'true';
        modal.style.display = 'flex';
        return null;
      }
      return requestJson(ENDPOINTS.resources + '/' + resourceId, null, 'Không thể tải chi tiết tài nguyên.')
        .then(function (resource) {
          if (!resource) throw new Error('Không có dữ liệu tài nguyên.');
          setText('resourceModalTitle', 'Chỉnh sửa tài nguyên #' + resource.id);
          $('resourceFormId').value = resource.id;
          $('resourceFormSlug').value = resource.slug || '';
          $('resourceFormTitle').value = resource.title || '';
          $('resourceFormProvider').value = resource.provider || '';
          $('resourceFormUrl').value = resource.url || '';
          $('resourceFormSkill').value = resource.skill_id || '';
          $('resourceFormType').value = resource.resource_type || 'documentation';
          $('resourceFormLanguage').value = resource.language || 'en';
          $('resourceFormDescription').value = resource.description || '';
          $('resourceFormFree').value = resource.is_free === false ? 'false' : 'true';
          $('resourceFormActive').value = resource.is_active === false ? 'false' : 'true';
          modal.style.display = 'flex';
        });
    }).catch(function (error) {
      showFeedback(error.message || 'Không thể mở form tài nguyên.', true);
    });
  }

  function setupForms() {
    var categoryForm = $('categoryForm');
    if (categoryForm) {
      categoryForm.addEventListener('submit', function (event) {
        event.preventDefault();
        submitForm(categoryForm, function () {
          var id = $('categoryFormId').value;
          var payload = {
            name: $('categoryFormName').value.trim(),
            slug: $('categoryFormSlug').value.trim(),
            description: $('categoryFormDesc').value.trim() || null
          };
          return saveEntity(
            id ? 'PUT' : 'POST',
            id ? ENDPOINTS.categories + '/' + id : ENDPOINTS.categories,
            payload,
            'Không thể lưu phân nhóm nghề nghiệp.',
            id ? 'Đã cập nhật phân nhóm nghề nghiệp.' : 'Đã tạo phân nhóm nghề nghiệp.',
            true
          );
        });
      });
    }

    var skillForm = $('skillForm');
    if (skillForm) {
      skillForm.addEventListener('submit', function (event) {
        event.preventDefault();
        submitForm(skillForm, function () {
          var id = $('skillFormId').value;
          var payload = {
            name: $('skillFormName').value.trim(),
            description: $('skillFormDesc').value.trim() || null
          };
          return saveEntity(
            id ? 'PUT' : 'POST',
            id ? ENDPOINTS.skills + '/' + id : ENDPOINTS.skills,
            payload,
            'Không thể lưu kỹ năng.',
            id ? 'Đã cập nhật kỹ năng chuẩn.' : 'Đã tạo kỹ năng chuẩn.',
            true
          );
        });
      });
    }

    var roleForm = $('roleForm');
    if (roleForm) {
      roleForm.addEventListener('submit', function (event) {
        event.preventDefault();
        submitForm(roleForm, function () {
          var id = $('roleFormId').value;
          var categoryValue = $('roleFormCategory').value;
          var payload = {
            category_id: categoryValue ? Number(categoryValue) : null,
            name: $('roleFormName').value.trim(),
            slug: $('roleFormSlug').value.trim(),
            level: $('roleFormLevel').value,
            description: $('roleFormDesc').value.trim() || null,
            is_active: editingRoleIsActive,
            required_skills: collectRoleSkills()
          };
          return saveEntity(
            id ? 'PUT' : 'POST',
            id ? ENDPOINTS.roles + '/' + id : ENDPOINTS.roles,
            payload,
            'Không thể lưu vị trí nghề nghiệp.',
            id ? 'Đã cập nhật vị trí nghề nghiệp và danh sách kỹ năng.' : 'Đã tạo vị trí nghề nghiệp.'
          );
        });
      });
    }

    var resourceForm = $('resourceForm');
    if (resourceForm) {
      resourceForm.addEventListener('submit', function (event) {
        event.preventDefault();
        submitForm(resourceForm, function () {
          var id = $('resourceFormId').value;
          var skillValue = $('resourceFormSkill').value;
          var payload = {
            slug: $('resourceFormSlug').value.trim(),
            title: $('resourceFormTitle').value.trim(),
            provider: $('resourceFormProvider').value.trim(),
            url: $('resourceFormUrl').value.trim(),
            skill_id: skillValue ? Number(skillValue) : null,
            resource_type: $('resourceFormType').value,
            description: $('resourceFormDescription').value.trim() || null,
            language: $('resourceFormLanguage').value || 'en',
            is_free: $('resourceFormFree').value === 'true',
            is_active: $('resourceFormActive').value === 'true'
          };
          return saveEntity(
            id ? 'PUT' : 'POST',
            id ? ENDPOINTS.resources + '/' + id : ENDPOINTS.resources,
            payload,
            'Không thể lưu tài nguyên học tập.',
            id
              ? 'Đã cập nhật tài nguyên; trạng thái kiểm duyệt đã trở lại chờ duyệt.'
              : 'Đã tạo tài nguyên ở trạng thái chờ duyệt.'
          );
        });
      });
    }
  }

  /* ── Status, review and delete ────────────────────────────── */

  function setItemStatus(tab, item, nextActive) {
    var labels = {
      roles: 'vị trí nghề nghiệp',
      skills: 'kỹ năng',
      resources: 'tài nguyên học tập',
      users: 'tài khoản'
    };
    var label = labels[tab] || 'bản ghi';
    var name = item.email || item.name || item.title || ('#' + item.id);
    if (!nextActive && !window.confirm('Bạn có chắc chắn muốn tạm ngưng ' + label + ' "' + name + '" không?')) {
      return Promise.resolve(null);
    }
    var method = tab === 'users' ? 'PUT' : 'PATCH';
    return requestJson(ENDPOINTS[tab] + '/' + item.id + '/status', {
      method: method,
      body: JSON.stringify({ is_active: nextActive })
    }, 'Không thể cập nhật trạng thái.').then(function () {
      return refreshView(nextActive ? 'Đã kích hoạt ' + label + ' thành công.' : 'Đã tạm ngưng ' + label + '.');
    }).catch(function (error) {
      showFeedback(error.message || 'Không thể cập nhật trạng thái.', true);
      return null;
    });
  }

  function reviewResource(resourceId, approvalStatus) {
    return requestJson(ENDPOINTS.resources + '/' + resourceId + '/approval', {
      method: 'PATCH',
      body: JSON.stringify({ approval_status: approvalStatus })
    }, 'Không thể cập nhật kiểm duyệt.').then(function () {
      return refreshView(
        approvalStatus === 'approved' ? 'Đã phê duyệt tài nguyên.' : 'Đã từ chối tài nguyên.'
      );
    }).catch(function (error) {
      showFeedback(error.message || 'Không thể cập nhật kiểm duyệt.', true);
      return null;
    });
  }

  function deleteEntity(tab, id) {
    var labels = {
      roles: 'vị trí nghề nghiệp',
      categories: 'phân nhóm nghề nghiệp',
      skills: 'kỹ năng',
      resources: 'tài nguyên học tập'
    };
    var label = labels[tab] || 'bản ghi';
    if (!window.confirm('Bạn có chắc chắn muốn xóa ' + label + ' #' + id + ' không?')) {
      return Promise.resolve(null);
    }
    return requestJson(ENDPOINTS[tab] + '/' + id, {
      method: 'DELETE'
    }, 'Không thể xóa bản ghi.').then(function () {
      return refreshView('Đã xóa ' + label + ' thành công.', { options: tab === 'categories' || tab === 'skills' });
    }).catch(function (error) {
      showFeedback(error.message || 'Không thể xóa bản ghi.', true);
      return null;
    });
  }

  /* ── Access guard & bootstrap ─────────────────────────────── */

  function kickOutNonAdmin(msg) {
    state.sessionReady = false;
    var content = $('adminAuthorizedContent');
    if (content) content.style.display = 'none';
    var denied = $('adminAccessDenied');
    if (denied) denied.style.display = 'block';
    if (msg) showFeedback(msg, true);

    var secondsLeft = 2;
    var countEl = $('kickSeconds');
    var interval = window.setInterval(function () {
      secondsLeft -= 1;
      if (countEl) countEl.textContent = String(secondsLeft);
      if (secondsLeft <= 0) {
        window.clearInterval(interval);
        window.location.replace('./explore.html');
      }
    }, 1000);
  }

  document.addEventListener('DOMContentLoaded', function () {
    setupTabs();
    setupForms();
    fillOptionSelects();
    selectTab(initialTabFromLocation(), false);

    loadSession().then(function (ok) {
      if (!ok) return null;
      state.sessionReady = true;
      return ensureOptions(false).then(function () {
        return Promise.all([loadStats(), loadTab(state.currentTab)]);
      });
    }).catch(function (error) {
      showFeedback(error.message || 'Không thể khởi tạo trang quản trị.', true);
    });
  });
})();
