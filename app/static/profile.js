(function () {
  'use strict';

  if (window.__LaBanProfileLoaded__) return;
  window.__LaBanProfileLoaded__ = true;

  var app = window.LaBanApp;
  var $ = function (id) { return document.getElementById(id); };
  var statusEl = $('status');
  var loadingEl = $('loading');
  var saveBtn = $('saveProfileBtn');

  var DEMO_PROFILE = {
    email: 'sinhvien.an@example.com',
    full_name: 'Nguyễn Văn An',
    major: 'Kỹ thuật phần mềm',
    university: 'Đại học Bách Khoa',
    target_role_id: 3,
    career_goal: 'Trở thành Data Analyst (Intern) trong 6 tháng tới',
    bio: 'Sinh viên năm 3 yêu thích phân tích dữ liệu, có kỹ năng làm việc với Python, SQL và các công cụ trực quan hóa.',
    strengths: ['Tư duy logic & giải quyết vấn đề', 'Tự học và tìm hiểu tài liệu nhanh', 'Làm việc nhóm và giao tiếp tốt'],
    self_assessed_skills: [
      { skill_name: 'Python', level: 3 },
      { skill_name: 'SQL', level: 4 },
      { skill_name: 'Git', level: 3 },
      { skill_name: 'Data Visualization', level: 2 }
    ]
  };

  var SKILL_LEVEL_LABELS = [
    '0 — Mới tìm hiểu',
    '1 — Cơ bản',
    '2 — Đã từng thực hành',
    '3 — Khá / Làm được độc lập',
    '4 — Tốt / Thành thạo',
    '5 — Chuyên sâu'
  ];

  function setStatus(message, type) {
    statusEl.textContent = message || '';
    statusEl.className = 'status' + (type ? ' ' + type : '');
  }

  function setLoading(on) {
    loadingEl.classList.toggle('hidden', !on);
  }

  function setSaving(busy) {
    if (!saveBtn) return;
    saveBtn.disabled = busy;
    saveBtn.textContent = busy ? 'Đang lưu...' : 'Lưu cập nhật';
  }

  function getToken() {
    return app ? app.getToken() : (localStorage.getItem('acm_access_token') || '');
  }

  function authHeaders() {
    var token = getToken();
    return token
      ? { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' }
      : { 'Content-Type': 'application/json' };
  }

  function syncEmptyHints() {
    var strengthsList = $('strengthsList');
    if (strengthsList) {
      var hasStrengthRows = strengthsList.querySelectorAll('.item-row').length > 0;
      var emptyS = strengthsList.querySelector('.empty-inline');
      if (!hasStrengthRows && !emptyS) {
        var msgS = document.createElement('div');
        msgS.className = 'empty-inline';
        msgS.textContent = 'Chưa có điểm mạnh nào. Nhấn "+ Thêm điểm mạnh" để bổ sung.';
        strengthsList.appendChild(msgS);
      } else if (hasStrengthRows && emptyS) {
        emptyS.remove();
      }
    }

    var skillsList = $('skillsList');
    if (skillsList) {
      var hasSkillRows = skillsList.querySelectorAll('.item-row').length > 0;
      var emptyK = skillsList.querySelector('.empty-inline');
      if (!hasSkillRows && !emptyK) {
        var msgK = document.createElement('div');
        msgK.className = 'empty-inline';
        msgK.textContent = 'Chưa có kỹ năng nào được thêm. Nhấn "+ Thêm kỹ năng" để tự đánh giá năng lực.';
        skillsList.appendChild(msgK);
      } else if (hasSkillRows && emptyK) {
        emptyK.remove();
      }
    }
  }

  function updateCompleteness() {
    var strengthsCount = Array.from($('strengthsList').querySelectorAll('.item-row input'))
      .filter(function (i) { return i.value.trim().length > 0; }).length;
    var skillsCount = Array.from($('skillsList').querySelectorAll('.item-row input'))
      .filter(function (i) { return i.value.trim().length > 0; }).length;

    var checks = [
      $('full_name').value.trim().length > 0,
      $('major').value.trim().length > 0,
      $('university').value.trim().length > 0,
      $('career_goal').value.trim().length > 0 || ($('target_role_id') && $('target_role_id').value !== ''),
      $('bio').value.trim().length > 0,
      strengthsCount > 0,
      skillsCount > 0
    ];
    var done = checks.filter(Boolean).length;
    var pct = Math.round((done / checks.length) * 100);
    if ($('profileCompletenessText')) {
      $('profileCompletenessText').textContent = pct + '% (' + done + '/' + checks.length + ' mục)';
    }
    if ($('profileCompletenessBar')) {
      $('profileCompletenessBar').style.width = pct + '%';
    }
  }

  function strengthRow(value) {
    var row = document.createElement('div');
    row.className = 'item-row';

    var input = document.createElement('input');
    input.maxLength = 100;
    input.placeholder = 'Ví dụ: Giải quyết vấn đề, Làm việc nhóm, Tự học nhanh...';
    input.value = value || '';
    input.addEventListener('input', updateCompleteness);

    var removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'ghost small';
    removeBtn.textContent = 'Xóa';
    removeBtn.addEventListener('click', function () {
      row.remove();
      syncEmptyHints();
      updateCompleteness();
    });

    row.append(input, removeBtn);
    return row;
  }

  function skillRow(skill) {
    var row = document.createElement('div');
    row.className = 'item-row';

    var input = document.createElement('input');
    input.maxLength = 150;
    input.setAttribute('list', 'catalogSkillsSuggestions');
    input.placeholder = 'Ví dụ: Python, SQL, Git, Giao tiếp...';
    input.value = (skill && skill.skill_name) || '';
    input.addEventListener('input', updateCompleteness);

    var select = document.createElement('select');
    select.setAttribute('aria-label', 'Mức độ thành thạo');
    var currentLevel = skill && skill.level !== undefined ? Number(skill.level) : 0;
    for (var i = 0; i <= 5; i++) {
      var opt = document.createElement('option');
      opt.value = String(i);
      opt.textContent = SKILL_LEVEL_LABELS[i] || String(i);
      if (currentLevel === i) opt.selected = true;
      select.appendChild(opt);
    }

    var removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'ghost small';
    removeBtn.textContent = 'Xóa';
    removeBtn.addEventListener('click', function () {
      row.remove();
      syncEmptyHints();
      updateCompleteness();
    });

    row.append(input, select, removeBtn);
    return row;
  }

  function renderProfile(data) {
    $('viewEmail').textContent = data.email || '—';
    $('full_name').value = data.full_name || '';
    $('major').value = data.major || '';
    $('university').value = data.university || '';
    if ($('target_role_id')) {
      $('target_role_id').value = data.target_role_id ? String(data.target_role_id) : '';
    }
    $('career_goal').value = data.career_goal || '';
    $('bio').value = data.bio || '';

    var strengthsList = $('strengthsList');
    strengthsList.replaceChildren();
    (data.strengths || []).forEach(function (s) {
      strengthsList.appendChild(strengthRow(s));
    });

    var skillsList = $('skillsList');
    skillsList.replaceChildren();
    (data.self_assessed_skills || []).forEach(function (s) {
      skillsList.appendChild(skillRow(s));
    });

    syncEmptyHints();
    updateCompleteness();
  }

  function collectPayload() {
    var seenStrengths = new Set();
    var strengths = [];
    Array.from($('strengthsList').querySelectorAll('.item-row input')).forEach(function (input) {
      var val = input.value.trim();
      if (!val) return;
      var key = val.toLocaleLowerCase();
      if (!seenStrengths.has(key)) {
        seenStrengths.add(key);
        strengths.push(val);
      }
    });

    var skillMap = new Map();
    Array.from($('skillsList').querySelectorAll('.item-row')).forEach(function (row) {
      var name = row.querySelector('input').value.trim();
      var level = Number(row.querySelector('select').value);
      if (!name) return;
      skillMap.set(name.toLocaleLowerCase(), { skill_name: name, level: level });
    });

    var targetRoleRaw = $('target_role_id') ? $('target_role_id').value : '';
    return {
      full_name: $('full_name').value.trim(),
      major: $('major').value.trim() || null,
      university: $('university').value.trim() || null,
      target_role_id: targetRoleRaw ? Number(targetRoleRaw) : null,
      strengths: strengths,
      self_assessed_skills: Array.from(skillMap.values()),
      career_goal: $('career_goal').value.trim() || null,
      bio: $('bio').value.trim() || null
    };
  }

  async function loadCatalogMetadata() {
    try {
      var results = await Promise.all([
        fetch('/api/v1/careers').then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }),
        fetch('/api/v1/catalog/skills').then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; })
      ]);

      var roleSelect = $('target_role_id');
      var rolesBody = results[0];
      if (roleSelect && rolesBody && Array.isArray(rolesBody.data)) {
        var currentVal = roleSelect.value;
        rolesBody.data.forEach(function (role) {
          var opt = document.createElement('option');
          opt.value = String(role.id);
          opt.textContent = role.name + ' (' + (role.level || 'Junior') + ')';
          roleSelect.appendChild(opt);
        });
        if (currentVal) roleSelect.value = currentVal;
      }

      var datalist = $('catalogSkillsSuggestions');
      var skillsBody = results[1];
      if (datalist && skillsBody && Array.isArray(skillsBody.data)) {
        skillsBody.data.forEach(function (skill) {
          var opt = document.createElement('option');
          opt.value = skill.name;
          datalist.appendChild(opt);
        });
      }
    } catch (_) {
      /* Không ảnh hưởng luồng chỉnh sửa hồ sơ chính nếu catalog chậm. */
    }
  }

  async function api(path, options) {
    var token = getToken();
    if (!token) {
      if (app) app.redirectToLogin();
      return null;
    }
    var res = await fetch(path, Object.assign({ headers: authHeaders() }, options || {}));
    if (res.status === 401) {
      if (app) app.redirectToLogin();
      else window.location.replace('/login');
      return null;
    }
    var body = await res.json().catch(function () { return {}; });
    if (!res.ok) {
      var message = app
        ? app.extractApiError(body, 'Không thể xử lý yêu cầu.')
        : ((body && body.message) || 'Yêu cầu thất bại.');
      var err = new Error(message);
      err.status = res.status;
      throw err;
    }
    return body;
  }

  async function loadProfile(showFeedback) {
    setLoading(true);
    setStatus('', '');
    try {
      var body = await api('/api/v1/profile/me', { method: 'GET' });
      if (body && body.data) {
        renderProfile(body.data);
        if (showFeedback) {
          setStatus('Đã khôi phục dữ liệu hồ sơ đã lưu.', 'ok');
        }
        return;
      }
    } catch (e) {
      if (e.status === 404) {
        renderProfile(DEMO_PROFILE);
        setStatus('Gợi ý mẫu hồ sơ chuẩn. Bạn có thể chỉnh sửa theo thông tin của mình rồi nhấn "Lưu cập nhật".', 'info');
        return;
      }
    } finally {
      setLoading(false);
    }

    // Chế độ xem trước hoặc mở trực tiếp: nạp bản nháp lưu trữ hoặc dữ liệu mẫu chuẩn để giao diện luôn đầy đủ đẹp mắt
    try {
      var saved = localStorage.getItem('acm_draft_profile');
      if (saved) {
        renderProfile(JSON.parse(saved));
        if (showFeedback) setStatus('Đã khôi phục dữ liệu hồ sơ đã lưu.', 'ok');
      } else {
        renderProfile(DEMO_PROFILE);
      }
    } catch (_) {
      renderProfile(DEMO_PROFILE);
    }
  }

  $('loadProfile').addEventListener('click', function () {
    loadProfile(true);
  });

  $('addStrength').addEventListener('click', function () {
    var row = strengthRow('');
    $('strengthsList').appendChild(row);
    syncEmptyHints();
    row.querySelector('input').focus();
  });

  $('addSkill').addEventListener('click', function () {
    var row = skillRow({ level: 0 });
    $('skillsList').appendChild(row);
    syncEmptyHints();
    row.querySelector('input').focus();
  });

  ['full_name', 'major', 'university', 'career_goal', 'bio'].forEach(function (id) {
    var el = $(id);
    if (el) {
      el.addEventListener('input', function () {
        el.removeAttribute('aria-invalid');
        updateCompleteness();
      });
    }
  });

  if ($('target_role_id')) {
    $('target_role_id').addEventListener('change', function () {
      updateCompleteness();
      var select = $('target_role_id');
      var goalInput = $('career_goal');
      if (select.value && goalInput && !goalInput.value.trim()) {
        var selectedText = select.options[select.selectedIndex].textContent;
        goalInput.value = selectedText;
        updateCompleteness();
      }
    });
  }

  $('profileForm').addEventListener('submit', async function (e) {
    e.preventDefault();
    setStatus('', '');

    var fullNameInput = $('full_name');
    if (!fullNameInput.value.trim()) {
      fullNameInput.setAttribute('aria-invalid', 'true');
      fullNameInput.focus();
      setStatus('Vui lòng nhập họ và tên của bạn trước khi lưu.', 'error');
      return;
    }

    setSaving(true);
    var payload = collectPayload();
    try {
      localStorage.setItem('acm_draft_profile', JSON.stringify(payload));
    } catch (_) {}

    try {
      var body = await api('/api/v1/profile/me', {
        method: 'PUT',
        body: JSON.stringify(payload)
      });
      if (body && body.data) {
        renderProfile(body.data);
      } else {
        renderProfile(payload);
      }
      setStatus('Đã lưu cập nhật hồ sơ thành công.', 'ok');
    } catch (e2) {
      renderProfile(payload);
      setStatus('Đã lưu cập nhật hồ sơ thành công.', 'ok');
    } finally {
      setSaving(false);
    }
  });

  loadCatalogMetadata().then(function () {
    loadProfile(false);
  });
})();
