(function () {
  'use strict';

  if (window.__LaBanAnalysisLoaded__) return;
  window.__LaBanAnalysisLoaded__ = true;

  var app = window.LaBanApp;
  var PURPOSE_VERSION = 'v1';
  var $ = function (id) { return document.getElementById(id); };
  var statusEl = $('status');
  var loadingEl = $('loading');
  var modal = $('consentModal');
  var pendingPayload = null;
  var historyPage = 1;
  var historyPages = 0;
  var selectedAnalysisId = null;
  var pollTimer = null;
  var sourceMode = 'cv';
  var rolesById = Object.create(null);
  var cvsById = Object.create(null);

  function setStatus(message, type) {
    statusEl.textContent = message || '';
    statusEl.className = 'status' + (type ? ' ' + type : '');
  }

  function setLoading(on) {
    loadingEl.classList.toggle('hidden', !on);
    $('startAnalysisBtn').disabled = on;
  }

  function getToken() {
    return app ? app.getToken() : (localStorage.getItem('acm_access_token') || '');
  }

  function showModal(show) {
    modal.classList.toggle('hidden', !show);
    if (show) $('consentAccept').focus();
  }

  function dateLabel(value) {
    if (!value) return '—';
    var date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString('vi-VN');
  }

  function errorMessage(body, fallback) {
    return app ? app.extractApiError(body, fallback) : (
      body && body.detail && (body.detail.message || body.detail) ||
      body && body.message || fallback
    );
  }

  async function requestJson(path, options) {
    var token = getToken();
    if (!token) {
      if (app) app.redirectToLogin();
      throw new Error('Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.');
    }

    var requestOptions = Object.assign({}, options || {});
    requestOptions.headers = Object.assign({}, requestOptions.headers || {}, {
      Authorization: 'Bearer ' + token
    });
    var response = await fetch(path, requestOptions);
    var body = await response.json().catch(function () { return {}; });
    return { response: response, body: body };
  }

  function appendOption(select, value, label) {
    var option = document.createElement('option');
    option.value = String(value);
    option.textContent = label;
    select.appendChild(option);
  }

  function renderRolePreview() {
    var role = rolesById[$('roleSelect').value];
    var preview = $('selectedRolePreview');
    if (!role) {
      preview.classList.add('hidden');
      return;
    }

    $('previewRoleName').textContent = role.name;
    $('previewRoleLevel').textContent = role.level || '—';
    $('previewRoleCategory').textContent = role.category ? role.category.name : 'Chưa phân nhóm';
    $('previewRoleDesc').textContent = role.description || 'Chưa có mô tả cho vị trí này.';
    var skillNames = (role.required_skills || []).map(function (item) {
      return item.skill && item.skill.name;
    }).filter(Boolean);
    $('previewRoleSkills').textContent = skillNames.length
      ? 'Kỹ năng tiêu chuẩn: ' + skillNames.join(', ')
      : 'Vị trí này chưa có kỹ năng tiêu chuẩn được cấu hình.';
    preview.classList.remove('hidden');
  }

  async function loadRoles() {
    var select = $('roleSelect');
    select.replaceChildren();
    appendOption(select, '', 'Đang tải danh sách vị trí...');
    try {
      var result = await requestJson('/api/v1/careers');
      if (!result.response.ok) {
        throw new Error(errorMessage(result.body, 'Không tải được danh mục nghề nghiệp.'));
      }
      var roles = result.body.data || [];
      select.replaceChildren();
      appendOption(select, '', roles.length ? '-- Chọn vị trí nghề nghiệp --' : 'Chưa có vị trí nghề nghiệp');
      roles.forEach(function (role) {
        rolesById[String(role.id)] = role;
        appendOption(select, role.id, role.name + ' (' + (role.level || '—') + ')');
      });

      var requestedRole = new URLSearchParams(window.location.search).get('career_role_id');
      if (requestedRole && rolesById[requestedRole]) select.value = requestedRole;
      renderRolePreview();
    } catch (error) {
      select.replaceChildren();
      appendOption(select, '', 'Không tải được danh mục nghề nghiệp');
      setStatus(error.message || 'Không tải được danh mục nghề nghiệp.', 'error');
    }
  }

  function updateSourceMode(mode) {
    sourceMode = mode === 'profile' ? 'profile' : 'cv';
    var usingCv = sourceMode === 'cv';
    $('sourceCvBtn').classList.toggle('is-selected', usingCv);
    $('sourceProfileBtn').classList.toggle('is-selected', !usingCv);
    $('sourceCvBtn').setAttribute('aria-pressed', String(usingCv));
    $('sourceProfileBtn').setAttribute('aria-pressed', String(!usingCv));
    $('cvPickerWrap').classList.toggle('hidden', !usingCv);
    $('profileSourceHint').classList.toggle('hidden', usingCv);
    updateCvState();
  }

  function updateCvState() {
    var cv = cvsById[$('cvSelect').value];
    var noCv = !Object.keys(cvsById).length;
    var usable = Boolean(cv && cv.has_text);
    $('noCvHint').classList.toggle('hidden', !noCv);
    $('scannedCvWarning').classList.toggle('hidden', !cv || usable);
    $('startAnalysisBtn').disabled = loadingEl && !loadingEl.classList.contains('hidden')
      ? true
      : (sourceMode === 'cv' && !usable) || !Object.keys(rolesById).length;
  }

  async function loadCvs() {
    var select = $('cvSelect');
    select.replaceChildren();
    appendOption(select, '', 'Đang tải danh sách CV...');
    try {
      var result = await requestJson('/api/v1/cvs');
      if (!result.response.ok) {
        throw new Error(errorMessage(result.body, 'Không tải được danh sách CV.'));
      }
      var data = result.body.data || {};
      var cvs = Array.isArray(data.cvs) ? data.cvs : [];
      select.replaceChildren();
      appendOption(select, '', cvs.length ? '-- Chọn CV PDF --' : 'Chưa có CV');
      cvs.forEach(function (cv) {
        if (!cv.is_active) return;
        cvsById[String(cv.id)] = cv;
        appendOption(select, cv.id, cv.file_name + (cv.has_text ? '' : ' (chưa đọc được văn bản)'));
      });

      var params = new URLSearchParams(window.location.search);
      var requestedCv = params.get('cv_id');
      if (requestedCv && cvsById[requestedCv]) select.value = requestedCv;
      updateCvState();
    } catch (error) {
      select.replaceChildren();
      appendOption(select, '', 'Không tải được danh sách CV');
      setStatus(error.message || 'Không tải được danh sách CV.', 'error');
    }
  }

  function statusLabel(status) {
    return {
      pending: 'Đang chờ',
      processing: 'Đang phân tích',
      completed: 'Hoàn tất',
      failed: 'Thất bại'
    }[status] || status || '—';
  }

  function makeCell(text) {
    var cell = document.createElement('td');
    cell.textContent = text == null ? '—' : String(text);
    return cell;
  }

  async function loadHistory(page) {
    historyPage = page;
    $('historyEmpty').textContent = 'Đang tải lịch sử...';
    $('historyEmpty').classList.remove('hidden');
    $('historyList').replaceChildren();
    try {
      var result = await requestJson('/api/v1/analyses?page=' + page + '&page_size=10');
      if (!result.response.ok) {
        throw new Error(errorMessage(result.body, 'Không tải được lịch sử phân tích.'));
      }
      var history = result.body.data || {};
      var items = Array.isArray(history.items) ? history.items : [];
      historyPages = history.pages || 0;
      $('pageInfo').textContent = history.total
        ? 'Trang ' + history.page + ' / ' + history.pages + ' · ' + history.total + ' lần phân tích'
        : '';
      $('previousPage').disabled = page <= 1;
      $('nextPage').disabled = page >= historyPages;
      $('historyEmpty').classList.toggle('hidden', items.length > 0);
      if (!items.length) $('historyEmpty').textContent = 'Bạn chưa có lần phân tích nào.';

      items.forEach(function (item) {
        var row = document.createElement('div');
        row.className = 'history-item';
        var info = document.createElement('div');
        var title = document.createElement('strong');
        title.textContent = item.career_role_name || 'Lần phân tích #' + item.id;
        var metadata = document.createElement('div');
        metadata.className = 'muted small';
        metadata.textContent = dateLabel(item.created_at) + ' · ' + statusLabel(item.status);
        info.append(title, metadata);
        var score = document.createElement('span');
        score.className = 'badge';
        score.textContent = item.readiness_score == null ? 'Chưa có điểm' : item.readiness_score + '/100';
        var button = document.createElement('button');
        button.type = 'button';
        button.textContent = 'Xem báo cáo';
        button.addEventListener('click', function () { openReport(item.id); });
        row.append(info, score, button);
        $('historyList').appendChild(row);
      });
    } catch (error) {
      $('historyEmpty').textContent = error.message || 'Không tải được lịch sử phân tích.';
      $('pageInfo').textContent = '';
      $('previousPage').disabled = true;
      $('nextPage').disabled = true;
    }
  }

  async function renderSkills(analysisId) {
    var result = await requestJson('/api/v1/analyses/' + analysisId + '/skills');
    if (!result.response.ok) {
      throw new Error(errorMessage(result.body, 'Không tải được chi tiết kỹ năng.'));
    }
    var skills = result.body.data || [];
    var body = $('skillsBody');
    body.replaceChildren();
    $('skillsEmpty').classList.toggle('hidden', skills.length > 0);
    $('skillsTable').classList.toggle('hidden', skills.length === 0);
    skills.forEach(function (skill) {
      var row = document.createElement('tr');
      row.appendChild(makeCell(skill.skill_name));
      row.appendChild(makeCell(skill.current_level + '/5'));
      row.appendChild(makeCell(skill.required_level + '/5'));
      row.appendChild(makeCell(skill.gap_score));
      row.appendChild(makeCell(skill.has_evidence ? skill.evidence : 'Chưa có bằng chứng'));
      row.appendChild(makeCell(skill.recommendation));
      body.appendChild(row);
    });
  }

  async function refreshReport(analysisId) {
    var result = await requestJson('/api/v1/analyses/' + analysisId);
    if (!result.response.ok) {
      throw new Error(errorMessage(result.body, 'Không tải được báo cáo.'));
    }
    var report = result.body.data;
    if (selectedAnalysisId !== analysisId) return;
    $('reportRole').textContent = (report.career_role_name || 'Báo cáo #' + report.id)
      + ' · Tạo lúc ' + dateLabel(report.created_at);
    $('reportProgress').textContent = 'Trạng thái: ' + statusLabel(report.status);
    $('reportProgress').className = 'status' + (report.status === 'failed' ? ' error' : '');

    if (report.status === 'completed') {
      clearTimeout(pollTimer);
      $('reportContent').classList.remove('hidden');
      $('readinessScore').textContent = report.readiness_score == null ? '—' : report.readiness_score + '/100';
      $('reportSummary').textContent = report.summary || 'Chưa có nhận xét tổng quan.';
      await renderSkills(analysisId);
      await loadHistory(historyPage);
    } else {
      $('reportContent').classList.add('hidden');
      if (report.status === 'failed') {
        clearTimeout(pollTimer);
      } else {
        pollTimer = setTimeout(function () {
          refreshReport(analysisId).catch(function (error) {
            $('reportProgress').textContent = error.message;
            $('reportProgress').className = 'status error';
          });
        }, 2500);
      }
    }
  }

  async function openReport(analysisId) {
    clearTimeout(pollTimer);
    selectedAnalysisId = analysisId;
    $('reportCard').classList.remove('hidden');
    $('reportContent').classList.add('hidden');
    $('reportProgress').textContent = 'Đang tải báo cáo...';
    try {
      await refreshReport(analysisId);
      $('reportCard').scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (error) {
      $('reportProgress').textContent = error.message;
      $('reportProgress').className = 'status error';
    }
  }

  function showPipelineUnavailable(body) {
    var detail = body.detail || {};
    var data = detail.data || {};
    if (data.code !== 'ANALYSIS_PIPELINE_NOT_IMPLEMENTED') return false;
    $('resultTitle').textContent = 'Yêu cầu chưa được phân tích';
    $('resultSubtitle').textContent = 'Quyền đồng ý đã được xác nhận; chưa có báo cáo được tạo.';
    $('resultBadge').textContent = 'Chưa triển khai';
    $('resultBadge').className = 'badge badge-info';
    $('resultSummary').replaceChildren();
    $('resultBodyText').textContent = detail.message ||
      'Pipeline phân tích hiện chưa được triển khai. Không có điểm số hoặc kết quả giả được tạo.';
    $('resultCard').classList.remove('hidden');
    setStatus('Máy chủ chưa hỗ trợ xử lý phân tích; không có báo cáo nào được tạo.', 'error');
    return true;
  }

  async function submitAnalysis() {
    if (!pendingPayload) return;
    var payload = Object.assign({}, pendingPayload, {
      ai_consent: { accepted: true, purpose_version: PURPOSE_VERSION }
    });
    pendingPayload = null;
    showModal(false);
    setLoading(true);
    try {
      var result = await requestJson('/api/v1/analyses', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (result.response.status === 501 && showPipelineUnavailable(result.body)) return;
      if (!result.response.ok) {
        throw new Error(errorMessage(result.body, 'Không thể bắt đầu phân tích.'));
      }
      $('resultTitle').textContent = 'Đã tiếp nhận yêu cầu phân tích';
      $('resultSubtitle').textContent = 'Máy chủ đã tiếp nhận yêu cầu.';
      $('resultBadge').textContent = 'Đang xử lý';
      $('resultBadge').className = 'badge badge-info';
      $('resultSummary').replaceChildren();
      $('resultBodyText').textContent = 'Yêu cầu được tiếp nhận. Chưa có kết quả cho đến khi máy chủ trả về báo cáo.';
      $('resultCard').classList.remove('hidden');
      setStatus('Đã tiếp nhận yêu cầu phân tích.', 'ok');
      await loadHistory(1);
    } catch (error) {
      setStatus(error.message || 'Không thể kết nối máy chủ.', 'error');
    } finally {
      setLoading(false);
      updateCvState();
    }
  }

  $('analysisForm').addEventListener('submit', function (event) {
    event.preventDefault();
    setStatus('', '');
    $('resultCard').classList.add('hidden');
    var roleId = $('roleSelect').value;
    var cv = cvsById[$('cvSelect').value];
    if (!roleId || !rolesById[roleId]) {
      setStatus('Vui lòng chọn vị trí nghề nghiệp từ danh mục đã tải.', 'error');
      $('roleSelect').focus();
      return;
    }
    if (sourceMode === 'cv' && (!cv || !cv.has_text)) {
      setStatus('Chọn CV có văn bản đọc được hoặc chuyển sang dùng Hồ sơ cá nhân.', 'error');
      $('cvSelect').focus();
      return;
    }
    if (!getToken()) {
      if (app) app.redirectToLogin();
      return;
    }
    pendingPayload = {
      cv_id: sourceMode === 'cv' ? cv.id : null,
      career_role_id: Number(roleId)
    };
    showModal(true);
  });

  $('sourceCvBtn').addEventListener('click', function () { updateSourceMode('cv'); });
  $('sourceProfileBtn').addEventListener('click', function () { updateSourceMode('profile'); });
  $('switchToProfileBtn').addEventListener('click', function () { updateSourceMode('profile'); });
  $('cvSelect').addEventListener('change', updateCvState);
  $('roleSelect').addEventListener('change', renderRolePreview);
  $('consentReject').addEventListener('click', function () {
    pendingPayload = null;
    showModal(false);
    setStatus('Bạn đã từ chối. Không có dữ liệu nào được gửi.', 'info');
  });
  $('consentAccept').addEventListener('click', submitAnalysis);
  $('previousPage').addEventListener('click', function () {
    if (historyPage > 1) loadHistory(historyPage - 1);
  });
  $('nextPage').addEventListener('click', function () {
    if (historyPage < historyPages) loadHistory(historyPage + 1);
  });
  modal.addEventListener('click', function (event) {
    if (event.target === modal) event.preventDefault();
  });
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && !modal.classList.contains('hidden')) {
      pendingPayload = null;
      showModal(false);
    }
  });

  var params = new URLSearchParams(window.location.search);
  updateSourceMode(params.get('source') === 'profile' ? 'profile' : 'cv');
  Promise.all([loadRoles(), loadCvs()]).then(function () {
    updateCvState();
  });
  loadHistory(1);
})();
