/**
 * Xử lý giao diện Quản trị danh mục hệ thống (Sprint 3 / M1).
 * Hỗ trợ quản lý CRUD Roles, Categories, Skills, Resources với dual-mode tương thích.
 */
(function () {
  'use strict';

  if (window.__LaBanAdminLoaded__) return;
  window.__LaBanAdminLoaded__ = true;

  var isDirectMode = window.location.protocol === 'file:' ||
                     window.location.pathname.indexOf('/app/static/') !== -1 ||
                     !window.location.host;

  var catalogData = {
    categories: [
      { id: 1, name: 'Software Development', slug: 'software-development', description: 'Phát triển phần mềm ứng dụng, hệ thống và web.' },
      { id: 2, name: 'Data and AI', slug: 'data-and-ai', description: 'Phân tích dữ liệu lớn và xây dựng mô hình học máy.' },
      { id: 3, name: 'Cybersecurity', slug: 'cybersecurity', description: 'Bảo mật hệ thống, an ninh mạng và an toàn thông tin.' },
      { id: 4, name: 'Product Design', slug: 'product-design', description: 'Nghiên cứu trải nghiệm và thiết kế giao diện sản phẩm số.' }
    ],
    roles: [
      { id: 1, category_id: 1, name: 'Backend Developer', slug: 'backend-developer', level: 'Junior', description: 'Thiết kế và xây dựng server, RESTful API và cơ sở dữ liệu.', is_active: true, required_skills: [{}, {}, {}, {}] },
      { id: 2, category_id: 1, name: 'Frontend Developer', slug: 'frontend-developer', level: 'Junior', description: 'Xây dựng giao diện web tương tác, hiện đại và tối ưu trải nghiệm.', is_active: true, required_skills: [{}, {}, {}] },
      { id: 3, category_id: 2, name: 'Data Analyst', slug: 'data-analyst', level: 'Junior', description: 'Khai phá dữ liệu, trực quan hóa và cung cấp báo cáo hỗ trợ ra quyết định.', is_active: true, required_skills: [{}, {}, {}, {}] },
      { id: 4, category_id: 2, name: 'Machine Learning Engineer', slug: 'machine-learning-engineer', level: 'Junior', description: 'Nghiên cứu và triển khai các thuật toán học máy, thị giác máy tính và NLP.', is_active: true, required_skills: [{}, {}, {}, {}] },
      { id: 5, category_id: 3, name: 'Cybersecurity Analyst', slug: 'cybersecurity-analyst', level: 'Fresher', description: 'Giám sát an ninh mạng, phát hiện nguy cơ và ứng phó sự cố an toàn thông tin.', is_active: true, required_skills: [{}, {}, {}] },
      { id: 6, category_id: 4, name: 'UX/UI Designer', slug: 'ux-ui-designer', level: 'Intern', description: 'Phỏng vấn người dùng, xây dựng wireframe và thiết kế UI hoàn chỉnh trên Figma.', is_active: true, required_skills: [{}, {}, {}] }
    ],
    skills: [
      { id: 1, name: 'Python', description: 'Ngôn ngữ lập trình phổ biến cho backend, dữ liệu và AI.' },
      { id: 2, name: 'SQL', description: 'Truy vấn và thao tác trên cơ sở dữ liệu quan hệ.' },
      { id: 3, name: 'Git', description: 'Quản lý phiên bản mã nguồn và cộng tác dự án.' },
      { id: 4, name: 'REST APIs', description: 'Thiết kế và tích hợp chuẩn giao tiếp dịch vụ web.' },
      { id: 5, name: 'JavaScript', description: 'Ngôn ngữ lập trình tương tác cho giao diện web.' },
      { id: 6, name: 'HTML and CSS', description: 'Cấu trúc và giao diện định kiểu cho website.' },
      { id: 7, name: 'Data Visualization', description: 'Trực quan hóa dữ liệu bằng biểu đồ và dashboard.' },
      { id: 8, name: 'Statistics', description: 'Thống kê ứng dụng và phân tích suy luận.' },
      { id: 9, name: 'Machine Learning', description: 'Thuật toán học máy và đánh giá mô hình.' },
      { id: 10, name: 'Linux', description: 'Quản trị hệ điều hành và dòng lệnh Linux.' },
      { id: 11, name: 'Networking', description: 'Mạng máy tính, giao thức TCP/IP và bảo mật kết nối.' },
      { id: 12, name: 'Threat Modeling', description: 'Nhận diện và phòng ngừa lỗ hổng bảo mật.' },
      { id: 13, name: 'UX Research', description: 'Nghiên cứu hành vi người dùng và kiểm thử khả dụng.' },
      { id: 14, name: 'Wireframing', description: 'Vẽ khung cấu trúc bố cục sản phẩm số.' }
    ],
    resources: [
      { id: 1, skill_id: 1, title: 'Python Tutorial', provider: 'Python Software Foundation', url: 'https://docs.python.org/3/tutorial/', resource_type: 'documentation', is_free: true },
      { id: 2, skill_id: 2, title: 'Interactive SQL Lessons', provider: 'SQLBolt', url: 'https://sqlbolt.com/', resource_type: 'practice', is_free: true },
      { id: 3, skill_id: 3, title: 'Git Documentation', provider: 'Git', url: 'https://git-scm.com/doc', resource_type: 'documentation', is_free: true },
      { id: 4, skill_id: 5, title: 'JavaScript Guide', provider: 'MDN', url: 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide', resource_type: 'documentation', is_free: true },
      { id: 5, skill_id: 6, title: 'Learn Web Development', provider: 'MDN', url: 'https://developer.mozilla.org/en-US/docs/Learn', resource_type: 'course', is_free: true },
      { id: 6, skill_id: 1, title: 'Python Course', provider: 'Kaggle Learn', url: 'https://www.kaggle.com/learn/python', resource_type: 'course', is_free: true },
      { id: 7, skill_id: 7, title: 'Data Visualization Course', provider: 'Kaggle Learn', url: 'https://www.kaggle.com/learn/data-visualization', resource_type: 'course', is_free: true },
      { id: 8, skill_id: 8, title: 'Intro to Statistics', provider: 'Kaggle Learn', url: 'https://www.kaggle.com/learn/intro-to-statistics', resource_type: 'course', is_free: true },
      { id: 9, skill_id: 9, title: 'Machine Learning Crash Course', provider: 'Google', url: 'https://developers.google.com/machine-learning/crash-course', resource_type: 'course', is_free: true },
      { id: 10, skill_id: 10, title: 'Linux Journey', provider: 'Linux Journey', url: 'https://linuxjourney.com/', resource_type: 'course', is_free: true },
      { id: 11, skill_id: 12, title: 'OWASP Top 10', provider: 'OWASP', url: 'https://owasp.org/www-project-top-ten/', resource_type: 'documentation', is_free: true },
      { id: 12, skill_id: 11, title: 'What is computer networking?', provider: 'Cloudflare', url: 'https://www.cloudflare.com/learning/network-layer/what-is-a-computer-network/', resource_type: 'article', is_free: true },
      { id: 13, skill_id: 13, title: 'UX Research Cheat Sheet', provider: 'Nielsen Norman Group', url: 'https://www.nngroup.com/articles/ux-research-cheat-sheet/', resource_type: 'article', is_free: true },
      { id: 14, skill_id: 14, title: 'Guide to wireframing', provider: 'Figma', url: 'https://www.figma.com/resource-library/what-is-wireframing/', resource_type: 'article', is_free: true }
    ]
  };

  function $(id) {
    return document.getElementById(id);
  }

  function showFeedback(msg, isError) {
    var box = $('adminFeedback');
    if (!box) return;
    box.textContent = msg;
    box.className = 'status-card ' + (isError ? 'danger' : 'ok');
    box.style.display = 'block';
    setTimeout(function () {
      box.style.display = 'none';
    }, 4000);
  }

  window.closeAllModals = function () {
    ['categoryModal', 'roleModal', 'skillModal', 'resourceModal'].forEach(function (id) {
      var m = $(id);
      if (m) m.style.display = 'none';
    });
  };

  function updateStats() {
    $('statRolesCount').textContent = catalogData.roles.length;
    $('statCategoriesCount').textContent = catalogData.categories.length;
    $('statSkillsCount').textContent = catalogData.skills.length;
    $('statResourcesCount').textContent = catalogData.resources.length;
  }

  /* ── Tab 1: Roles ────────────────────────────────────────── */
  function renderRolesTable(filterText) {
    var tbody = $('rolesTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    var query = (filterText || '').trim().toLowerCase();
    var list = catalogData.roles.filter(function (r) {
      return !query || r.name.toLowerCase().includes(query) || (r.level || '').toLowerCase().includes(query);
    });

    if (list.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--muted); padding: 24px;">Không tìm thấy vị trí nghề nghiệp nào.</td></tr>';
      return;
    }

    list.forEach(function (role) {
      var cat = catalogData.categories.find(function (c) { return c.id === role.category_id; });
      var catName = cat ? cat.name : 'Chưa phân nhóm';
      var skillsCount = (role.required_skills ? role.required_skills.length : 0);

      var tr = document.createElement('tr');
      tr.innerHTML = '<td>#' + role.id + '</td>' +
        '<td><strong>' + role.name + '</strong></td>' +
        '<td><span class="level-badge level-' + (role.level || 'junior').toLowerCase() + '">' + (role.level || 'Junior') + '</span></td>' +
        '<td>' + catName + '</td>' +
        '<td>' + skillsCount + ' kỹ năng</td>' +
        '<td><span class="badge ' + (role.is_active !== false ? 'badge-ok' : 'badge-muted') + '">' + (role.is_active !== false ? 'Hoạt động' : 'Tạm ẩn') + '</span></td>' +
        '<td style="text-align: right;">' +
          '<button type="button" class="admin-action-btn admin-btn-edit" data-edit-role="' + role.id + '">Sửa</button>' +
          '<button type="button" class="admin-action-btn admin-btn-delete" data-del-role="' + role.id + '">Xóa</button>' +
        '</td>';
      tbody.appendChild(tr);
    });

    // Wire edit & delete buttons
    Array.prototype.forEach.call(tbody.querySelectorAll('[data-edit-role]'), function (btn) {
      btn.onclick = function () {
        var id = Number(btn.getAttribute('data-edit-role'));
        openRoleModal(id);
      };
    });
    Array.prototype.forEach.call(tbody.querySelectorAll('[data-del-role]'), function (btn) {
      btn.onclick = function () {
        var id = Number(btn.getAttribute('data-del-role'));
        deleteRole(id);
      };
    });
  }

  function openRoleModal(roleId) {
    var catSelect = $('roleFormCategory');
    catSelect.innerHTML = '';
    catalogData.categories.forEach(function (c) {
      var opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = c.name;
      catSelect.appendChild(opt);
    });

    if (roleId) {
      var role = catalogData.roles.find(function (r) { return r.id === roleId; });
      if (!role) return;
      $('roleModalTitle').textContent = 'Chỉnh sửa vị trí nghề nghiệp #' + role.id;
      $('roleFormId').value = role.id;
      $('roleFormName').value = role.name;
      $('roleFormLevel').value = role.level || 'Junior';
      $('roleFormSlug').value = role.slug;
      $('roleFormCategory').value = role.category_id || '';
      $('roleFormDesc').value = role.description || '';
    } else {
      $('roleModalTitle').textContent = 'Thêm vị trí nghề nghiệp mới';
      $('roleFormId').value = '';
      $('roleFormName').value = '';
      $('roleFormLevel').value = 'Junior';
      $('roleFormSlug').value = '';
      $('roleFormDesc').value = '';
    }
    $('roleModal').style.display = 'flex';
  }

  function deleteRole(roleId) {
    if (!confirm('Bạn có chắc chắn muốn xóa vị trí nghề nghiệp #' + roleId + ' không?')) return;
    catalogData.roles = catalogData.roles.filter(function (r) { return r.id !== roleId; });
    renderRolesTable($('searchRolesInput').value);
    updateStats();
    showFeedback('Đã xóa vị trí nghề nghiệp thành công.', false);
  }

  /* ── Tab 2: Categories ───────────────────────────────────── */
  function renderCategoriesTable(filterText) {
    var tbody = $('categoriesTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    var query = (filterText || '').trim().toLowerCase();
    var list = catalogData.categories.filter(function (c) {
      return !query || c.name.toLowerCase().includes(query) || (c.slug || '').toLowerCase().includes(query);
    });

    list.forEach(function (cat) {
      var tr = document.createElement('tr');
      tr.innerHTML = '<td>#' + cat.id + '</td>' +
        '<td><strong>' + cat.name + '</strong></td>' +
        '<td><code>' + cat.slug + '</code></td>' +
        '<td>' + (cat.description || 'Chưa có mô tả') + '</td>' +
        '<td style="text-align: right;">' +
          '<button type="button" class="admin-action-btn admin-btn-edit" data-edit-cat="' + cat.id + '">Sửa</button>' +
          '<button type="button" class="admin-action-btn admin-btn-delete" data-del-cat="' + cat.id + '">Xóa</button>' +
        '</td>';
      tbody.appendChild(tr);
    });

    Array.prototype.forEach.call(tbody.querySelectorAll('[data-edit-cat]'), function (btn) {
      btn.onclick = function () {
        var id = Number(btn.getAttribute('data-edit-cat'));
        openCategoryModal(id);
      };
    });
    Array.prototype.forEach.call(tbody.querySelectorAll('[data-del-cat]'), function (btn) {
      btn.onclick = function () {
        var id = Number(btn.getAttribute('data-del-cat'));
        deleteCategory(id);
      };
    });
  }

  function openCategoryModal(catId) {
    if (catId) {
      var cat = catalogData.categories.find(function (c) { return c.id === catId; });
      if (!cat) return;
      $('categoryModalTitle').textContent = 'Chỉnh sửa phân nhóm #' + cat.id;
      $('categoryFormId').value = cat.id;
      $('categoryFormName').value = cat.name;
      $('categoryFormSlug').value = cat.slug;
      $('categoryFormDesc').value = cat.description || '';
    } else {
      $('categoryModalTitle').textContent = 'Thêm phân nhóm nghề nghiệp mới';
      $('categoryFormId').value = '';
      $('categoryFormName').value = '';
      $('categoryFormSlug').value = '';
      $('categoryFormDesc').value = '';
    }
    $('categoryModal').style.display = 'flex';
  }

  function deleteCategory(catId) {
    if (!confirm('Bạn có chắc chắn muốn xóa phân nhóm #' + catId + ' không?')) return;
    catalogData.categories = catalogData.categories.filter(function (c) { return c.id !== catId; });
    renderCategoriesTable($('searchCategoriesInput').value);
    updateStats();
    showFeedback('Đã xóa phân nhóm nghề nghiệp thành công.', false);
  }

  /* ── Tab 3: Skills ───────────────────────────────────────── */
  function renderSkillsTable(filterText) {
    var tbody = $('skillsTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    var query = (filterText || '').trim().toLowerCase();
    var list = catalogData.skills.filter(function (s) {
      return !query || s.name.toLowerCase().includes(query) || (s.description || '').toLowerCase().includes(query);
    });

    list.forEach(function (skill) {
      var tr = document.createElement('tr');
      tr.innerHTML = '<td>#' + skill.id + '</td>' +
        '<td><strong>' + skill.name + '</strong></td>' +
        '<td>' + (skill.description || 'Chưa có mô tả') + '</td>' +
        '<td style="text-align: right;">' +
          '<button type="button" class="admin-action-btn admin-btn-edit" data-edit-sk="' + skill.id + '">Sửa</button>' +
          '<button type="button" class="admin-action-btn admin-btn-delete" data-del-sk="' + skill.id + '">Xóa</button>' +
        '</td>';
      tbody.appendChild(tr);
    });

    Array.prototype.forEach.call(tbody.querySelectorAll('[data-edit-sk]'), function (btn) {
      btn.onclick = function () {
        var id = Number(btn.getAttribute('data-edit-sk'));
        openSkillModal(id);
      };
    });
    Array.prototype.forEach.call(tbody.querySelectorAll('[data-del-sk]'), function (btn) {
      btn.onclick = function () {
        var id = Number(btn.getAttribute('data-del-sk'));
        deleteSkill(id);
      };
    });
  }

  function openSkillModal(skillId) {
    if (skillId) {
      var skill = catalogData.skills.find(function (s) { return s.id === skillId; });
      if (!skill) return;
      $('skillModalTitle').textContent = 'Chỉnh sửa kỹ năng #' + skill.id;
      $('skillFormId').value = skill.id;
      $('skillFormName').value = skill.name;
      $('skillFormDesc').value = skill.description || '';
    } else {
      $('skillModalTitle').textContent = 'Thêm kỹ năng chuẩn mới';
      $('skillFormId').value = '';
      $('skillFormName').value = '';
      $('skillFormDesc').value = '';
    }
    $('skillModal').style.display = 'flex';
  }

  function deleteSkill(skillId) {
    if (!confirm('Bạn có chắc chắn muốn xóa kỹ năng #' + skillId + ' không?')) return;
    catalogData.skills = catalogData.skills.filter(function (s) { return s.id !== skillId; });
    renderSkillsTable($('searchSkillsInput').value);
    updateStats();
    showFeedback('Đã xóa kỹ năng thành công.', false);
  }

  /* ── Tab 4: Resources ────────────────────────────────────── */
  function renderResourcesTable(filterText) {
    var tbody = $('resourcesTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    var query = (filterText || '').trim().toLowerCase();
    var list = catalogData.resources.filter(function (r) {
      return !query || r.title.toLowerCase().includes(query) || (r.provider || '').toLowerCase().includes(query);
    });

    list.forEach(function (res) {
      var skill = catalogData.skills.find(function (s) { return s.id === res.skill_id; });
      var skillName = skill ? skill.name : 'Chung';
      var approvalStatus = res.approval_status || 'pending';
      var approvalLabel = {
        pending: 'Chờ duyệt',
        approved: 'Đã duyệt',
        rejected: 'Từ chối'
      }[approvalStatus] || 'Chờ duyệt';

      var tr = document.createElement('tr');
      tr.innerHTML = '<td>#' + res.id + '</td>' +
        '<td><a href="' + res.url + '" target="_blank" rel="noopener noreferrer"><strong>' + res.title + ' ↗</strong></a></td>' +
        '<td>' + res.provider + '</td>' +
        '<td><span class="skill-tag">' + skillName + '</span></td>' +
        '<td>' + (res.resource_type || 'Tài liệu') + '</td>' +
        '<td><span class="badge ' + (approvalStatus === 'approved' ? 'badge-ok' : approvalStatus === 'rejected' ? 'badge-muted' : 'badge-warn') + '">' + approvalLabel + '</span> ' +
          '<button type="button" class="admin-action-btn" data-review-res="' + res.id + '" data-review-status="' + (approvalStatus === 'approved' ? 'rejected' : 'approved') + '">' +
          (approvalStatus === 'approved' ? 'Từ chối' : 'Phê duyệt') + '</button></td>' +
        '<td>' + (res.is_free !== false ? '<span style="color:var(--ok);font-weight:600;">Miễn phí</span>' : 'Có phí') + '</td>' +
        '<td style="text-align: right;">' +
          '<button type="button" class="admin-action-btn admin-btn-edit" data-edit-res="' + res.id + '">Sửa</button>' +
          '<button type="button" class="admin-action-btn admin-btn-delete" data-del-res="' + res.id + '">Xóa</button>' +
        '</td>';
      tbody.appendChild(tr);
    });

    Array.prototype.forEach.call(tbody.querySelectorAll('[data-edit-res]'), function (btn) {
      btn.onclick = function () {
        var id = Number(btn.getAttribute('data-edit-res'));
        openResourceModal(id);
      };
    });
    Array.prototype.forEach.call(tbody.querySelectorAll('[data-del-res]'), function (btn) {
      btn.onclick = function () {
        var id = Number(btn.getAttribute('data-del-res'));
        deleteResource(id);
      };
    });
    Array.prototype.forEach.call(tbody.querySelectorAll('[data-review-res]'), function (btn) {
      btn.onclick = function () {
        reviewResource(
          Number(btn.getAttribute('data-review-res')),
          btn.getAttribute('data-review-status')
        );
      };
    });
  }

  function getAdminHeaders() {
    var token = window.LaBanApp ? window.LaBanApp.getToken() : '';
    if (!token) throw new Error('Vui lòng đăng nhập tài khoản Admin để quản lý tài nguyên.');
    return {
      Authorization: 'Bearer ' + token,
      'Content-Type': 'application/json'
    };
  }

  function refreshAdminCatalog(message) {
    loadInitialData().then(function (loaded) {
      if (message && loaded) showFeedback(message, false);
    }).catch(function (error) {
      showFeedback(error.message, true);
    });
  }

  function reviewResource(resourceId, approvalStatus) {
    if (isDirectMode) {
      showFeedback('Hãy mở trang qua FastAPI và đăng nhập Admin để kiểm duyệt.', true);
      return;
    }
    var headers;
    try {
      headers = getAdminHeaders();
    } catch (error) {
      showFeedback(error.message, true);
      return;
    }
    fetch('/api/v1/admin/resources/' + resourceId + '/approval', {
      method: 'PATCH',
      headers: headers,
      body: JSON.stringify({ approval_status: approvalStatus })
    })
      .then(function (response) {
        if (!response.ok) throw new Error('Không thể cập nhật trạng thái kiểm duyệt.');
        return response.json();
      })
      .then(function () {
        refreshAdminCatalog(approvalStatus === 'approved' ? 'Đã phê duyệt tài nguyên.' : 'Đã từ chối tài nguyên.');
      })
      .catch(function (error) {
        showFeedback(error.message, true);
      });
  }

  function openResourceModal(resId) {
    var skSelect = $('resourceFormSkill');
    skSelect.innerHTML = '<option value="">-- Không gắn kỹ năng cụ thể --</option>';
    catalogData.skills.forEach(function (s) {
      var opt = document.createElement('option');
      opt.value = s.id;
      opt.textContent = s.name;
      skSelect.appendChild(opt);
    });

    if (resId) {
      var res = catalogData.resources.find(function (r) { return r.id === resId; });
      if (!res) return;
      $('resourceModalTitle').textContent = 'Chỉnh sửa tài nguyên #' + res.id;
      $('resourceFormId').value = res.id;
      $('resourceFormSlug').value = res.slug;
      $('resourceFormTitle').value = res.title;
      $('resourceFormProvider').value = res.provider;
      $('resourceFormUrl').value = res.url;
      $('resourceFormSkill').value = res.skill_id || '';
      $('resourceFormType').value = res.resource_type || 'documentation';
      $('resourceFormDescription').value = res.description || '';
      $('resourceFormFree').value = (res.is_free !== false) ? 'true' : 'false';
    } else {
      $('resourceModalTitle').textContent = 'Thêm tài nguyên học tập mới';
      $('resourceFormId').value = '';
      $('resourceFormSlug').value = '';
      $('resourceFormTitle').value = '';
      $('resourceFormProvider').value = '';
      $('resourceFormUrl').value = '';
      $('resourceFormSkill').value = '';
      $('resourceFormType').value = 'documentation';
      $('resourceFormDescription').value = '';
      $('resourceFormFree').value = 'true';
    }
    $('resourceModal').style.display = 'flex';
  }

  function deleteResource(resId) {
    if (!confirm('Bạn có chắc chắn muốn xóa tài nguyên #' + resId + ' không?')) return;
    if (isDirectMode) {
      showFeedback('Hãy mở trang qua FastAPI và đăng nhập Admin để xóa tài nguyên.', true);
      return;
    }
    var headers;
    try {
      headers = getAdminHeaders();
    } catch (error) {
      showFeedback(error.message, true);
      return;
    }
    fetch('/api/v1/admin/resources/' + resId, { method: 'DELETE', headers: headers })
      .then(function (response) {
        if (!response.ok) throw new Error('Không thể xóa tài nguyên.');
        refreshAdminCatalog('Đã xóa tài nguyên học tập.');
      })
      .catch(function (error) { showFeedback(error.message, true); });
  }

  /* ── Tab Controller ──────────────────────────────────────── */
  function setupTabs() {
    var tabBtns = document.querySelectorAll('.admin-tab-btn');
    var tabContents = {
      roles: $('tabContentRoles'),
      categories: $('tabContentCategories'),
      skills: $('tabContentSkills'),
      resources: $('tabContentResources')
    };

    Array.prototype.forEach.call(tabBtns, function (btn) {
      btn.addEventListener('click', function () {
        Array.prototype.forEach.call(tabBtns, function (b) { b.classList.remove('active'); });
        btn.classList.add('active');

        var tabKey = btn.getAttribute('data-tab');
        Object.keys(tabContents).forEach(function (k) {
          if (tabContents[k]) {
            tabContents[k].style.display = (k === tabKey) ? 'block' : 'none';
          }
        });
      });
    });

    // Wire search inputs
    $('searchRolesInput').addEventListener('input', function () { renderRolesTable(this.value); });
    $('searchCategoriesInput').addEventListener('input', function () { renderCategoriesTable(this.value); });
    $('searchSkillsInput').addEventListener('input', function () { renderSkillsTable(this.value); });
    $('searchResourcesInput').addEventListener('input', function () { renderResourcesTable(this.value); });

    // Wire Add buttons
    $('btnAddRole').addEventListener('click', function () { openRoleModal(null); });
    $('btnAddCategory').addEventListener('click', function () { openCategoryModal(null); });
    $('btnAddSkill').addEventListener('click', function () { openSkillModal(null); });
    $('btnAddResource').addEventListener('click', function () { openResourceModal(null); });
  }

  /* ── Form Submit Handlers ────────────────────────────────── */
  function setupForms() {
    // Role Form
    $('roleForm').addEventListener('submit', function (e) {
      e.preventDefault();
      var id = $('roleFormId').value;
      var name = $('roleFormName').value.trim();
      var level = $('roleFormLevel').value;
      var slug = $('roleFormSlug').value.trim();
      var catId = Number($('roleFormCategory').value);
      var desc = $('roleFormDesc').value.trim();

      if (id) {
        var existing = catalogData.roles.find(function (r) { return r.id === Number(id); });
        if (existing) {
          existing.name = name;
          existing.level = level;
          existing.slug = slug;
          existing.category_id = catId;
          existing.description = desc;
        }
        showFeedback('Cập nhật vị trí nghề nghiệp thành công.', false);
      } else {
        var newId = Math.max.apply(null, catalogData.roles.map(function (r) { return r.id; }).concat([0])) + 1;
        catalogData.roles.push({
          id: newId,
          name: name,
          level: level,
          slug: slug,
          category_id: catId,
          description: desc,
          is_active: true,
          required_skills: []
        });
        showFeedback('Tạo vị trí nghề nghiệp mới thành công.', false);
      }
      closeAllModals();
      renderRolesTable($('searchRolesInput').value);
      updateStats();
    });

    // Category Form
    $('categoryForm').addEventListener('submit', function (e) {
      e.preventDefault();
      var id = $('categoryFormId').value;
      var name = $('categoryFormName').value.trim();
      var slug = $('categoryFormSlug').value.trim();
      var desc = $('categoryFormDesc').value.trim();

      if (id) {
        var existing = catalogData.categories.find(function (c) { return c.id === Number(id); });
        if (existing) {
          existing.name = name;
          existing.slug = slug;
          existing.description = desc;
        }
        showFeedback('Cập nhật phân nhóm nghề nghiệp thành công.', false);
      } else {
        var newId = Math.max.apply(null, catalogData.categories.map(function (c) { return c.id; }).concat([0])) + 1;
        catalogData.categories.push({ id: newId, name: name, slug: slug, description: desc });
        showFeedback('Tạo phân nhóm nghề nghiệp mới thành công.', false);
      }
      closeAllModals();
      renderCategoriesTable($('searchCategoriesInput').value);
      updateStats();
    });

    // Skill Form
    $('skillForm').addEventListener('submit', function (e) {
      e.preventDefault();
      var id = $('skillFormId').value;
      var name = $('skillFormName').value.trim();
      var desc = $('skillFormDesc').value.trim();

      if (id) {
        var existing = catalogData.skills.find(function (s) { return s.id === Number(id); });
        if (existing) {
          existing.name = name;
          existing.description = desc;
        }
        showFeedback('Cập nhật kỹ năng chuẩn thành công.', false);
      } else {
        var newId = Math.max.apply(null, catalogData.skills.map(function (s) { return s.id; }).concat([0])) + 1;
        catalogData.skills.push({ id: newId, name: name, description: desc });
        showFeedback('Tạo kỹ năng chuẩn mới thành công.', false);
      }
      closeAllModals();
      renderSkillsTable($('searchSkillsInput').value);
      updateStats();
    });

    // Resource Form
    $('resourceForm').addEventListener('submit', function (e) {
      e.preventDefault();
      var id = $('resourceFormId').value;
      var slug = $('resourceFormSlug').value.trim();
      var title = $('resourceFormTitle').value.trim();
      var provider = $('resourceFormProvider').value.trim();
      var url = $('resourceFormUrl').value.trim();
      var skillId = $('resourceFormSkill').value ? Number($('resourceFormSkill').value) : null;
      var rType = $('resourceFormType').value;
      var description = $('resourceFormDescription').value.trim();
      var isFree = $('resourceFormFree').value === 'true';

      if (isDirectMode) {
        showFeedback('Hãy mở trang qua FastAPI và đăng nhập Admin để lưu tài nguyên.', true);
        return;
      }
      var headers;
      try {
        headers = getAdminHeaders();
      } catch (error) {
        showFeedback(error.message, true);
        return;
      }
      var existingResource = id ? catalogData.resources.find(function (r) { return r.id === Number(id); }) : null;
      if (id && !existingResource) {
        showFeedback('Không tìm thấy tài nguyên cần cập nhật.', true);
        return;
      }
      var payload = {
          slug: slug,
          title: title,
          provider: provider,
          url: url,
          skill_id: skillId,
          resource_type: rType,
          description: description || null,
          is_free: isFree,
          is_active: true
        };
      fetch(id ? '/api/v1/admin/resources/' + id : '/api/v1/admin/resources', {
        method: id ? 'PUT' : 'POST',
        headers: headers,
        body: JSON.stringify(payload)
      })
        .then(function (response) {
          if (!response.ok) {
            return response.json().then(function (body) {
              throw new Error(body.message || 'Không thể lưu tài nguyên.');
            });
          }
          return response.json();
        })
        .then(function () {
          closeAllModals();
          refreshAdminCatalog(id ? 'Tài nguyên đã cập nhật và chuyển về trạng thái chờ duyệt.' : 'Tài nguyên đã được tạo ở trạng thái chờ duyệt.');
        })
        .catch(function (error) {
          showFeedback(error.message, true);
        });
    });
  }

  function kickOutNonAdmin(msg) {
    var content = $('adminAuthorizedContent');
    if (content) content.style.display = 'none';
    var denied = $('adminAccessDenied');
    if (denied) denied.style.display = 'block';

    var secondsLeft = 2;
    var countEl = $('kickSeconds');
    var interval = setInterval(function () {
      secondsLeft -= 1;
      if (countEl) countEl.textContent = String(secondsLeft);
      if (secondsLeft <= 0) {
        clearInterval(interval);
        window.location.replace('/explore');
      }
    }, 1000);
  }

  function loadInitialData() {
    var token = window.LaBanApp ? window.LaBanApp.getToken() : '';
    if (isDirectMode || !token || token === 'demo_student_token') {
      renderRolesTable('');
      renderCategoriesTable('');
      renderSkillsTable('');
      renderResourcesTable('');
      updateStats();
      showFeedback('Đăng nhập Admin qua FastAPI để tải kho tài nguyên.', true);
      return Promise.resolve(false);
    }

    fetch('/api/v1/admin/catalog', {
      headers: { Authorization: 'Bearer ' + token }
    })
      .then(function (res) {
        if (!res.ok) throw new Error('Không thể tải catalog admin');
        return res.json();
      })
      .then(function (body) {
        if (body && body.data) {
          if (body.data.roles) catalogData.roles = body.data.roles;
          if (body.data.categories) catalogData.categories = body.data.categories;
          if (body.data.skills) catalogData.skills = body.data.skills;
          if (body.data.resources) catalogData.resources = body.data.resources;
        }
      })
      .catch(function () {
        // Fallback demo data
      })
      .finally(function () {
        renderRolesTable('');
        renderCategoriesTable('');
        renderSkillsTable('');
        renderResourcesTable('');
        updateStats();
      });
  }

  document.addEventListener('DOMContentLoaded', function () {
    setupTabs();
    setupForms();
    loadInitialData();
  });
})();
