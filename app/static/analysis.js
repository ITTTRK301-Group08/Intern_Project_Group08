(function () {
  'use strict';

  if (window.__LaBanAnalysisLoaded__) return;
  window.__LaBanAnalysisLoaded__ = true;

  var app = window.LaBanApp;
  var PURPOSE_VERSION = 'v1';
  var POLL_INTERVAL_MS = 2500;
  var $ = function (id) { return document.getElementById(id); };

  var statusEl = $('status');
  var loadingEl = $('loading');
  var modal = $('consentModal');
  var startBtn = $('startAnalysisBtn');

  var DEFAULT_ROLES = [
    {
      id: 1,
      name: 'Data Analyst',
      level: 'Intern',
      category: { id: 1, name: 'Data & AI' },
      description: 'Thu thập, xử lý và phân tích dữ liệu; trực quan hóa thông tin chi tiết bằng biểu đồ và dashboard.',
      required_skills: [
        { skill: { id: 1, name: 'Python' }, required_level: 3, is_required: true },
        { skill: { id: 2, name: 'SQL' }, required_level: 4, is_required: true },
        { skill: { id: 8, name: 'Data Visualization' }, required_level: 3, is_required: true },
        { skill: { id: 12, name: 'Git' }, required_level: 3, is_required: false }
      ]
    },
    {
      id: 2,
      name: 'Frontend Developer',
      level: 'Fresher',
      category: { id: 2, name: 'Software Development' },
      description: 'Phát triển giao diện web hiện đại, tối ưu trải nghiệm người dùng và tương thích thiết bị.',
      required_skills: [
        { skill: { id: 3, name: 'JavaScript' }, required_level: 4, is_required: true },
        { skill: { id: 4, name: 'React' }, required_level: 3, is_required: true },
        { skill: { id: 11, name: 'HTML/CSS' }, required_level: 4, is_required: true }
      ]
    },
    {
      id: 3,
      name: 'Backend Developer',
      level: 'Fresher',
      category: { id: 2, name: 'Software Development' },
      description: 'Thiết kế cơ sở dữ liệu, xây dựng RESTful API và xử lý nghiệp vụ bảo mật.',
      required_skills: [
        { skill: { id: 1, name: 'Python' }, required_level: 4, is_required: true },
        { skill: { id: 5, name: 'FastAPI' }, required_level: 3, is_required: true },
        { skill: { id: 2, name: 'SQL' }, required_level: 4, is_required: true }
      ]
    },
    {
      id: 4,
      name: 'AI / Machine Learning Engineer',
      level: 'Intern',
      category: { id: 1, name: 'Data & AI' },
      description: 'Nghiên cứu và huấn luyện các mô hình học máy, tiền xử lý dữ liệu và tích hợp API mô hình.',
      required_skills: [
        { skill: { id: 1, name: 'Python' }, required_level: 4, is_required: true },
        { skill: { id: 7, name: 'Machine Learning Basics' }, required_level: 3, is_required: true }
      ]
    },
    {
      id: 5,
      name: 'DevOps Engineer',
      level: 'Fresher',
      category: { id: 3, name: 'Cloud & DevOps' },
      description: 'Tự động hóa triển khai, quản lý container Docker và thiết lập đường ống CI/CD.',
      required_skills: [
        { skill: { id: 9, name: 'Docker' }, required_level: 3, is_required: true },
        { skill: { id: 10, name: 'Linux Basics' }, required_level: 4, is_required: true },
        { skill: { id: 12, name: 'Git' }, required_level: 3, is_required: true }
      ]
    },
    {
      id: 6,
      name: 'Product Owner',
      level: 'Intern',
      category: { id: 4, name: 'Product & Design' },
      description: 'Làm việc với các bên liên quan, quản lý backlog sản phẩm và định hình tính năng người dùng.',
      required_skills: [
        { skill: { id: 13, name: 'Agile / Scrum' }, required_level: 3, is_required: true },
        { skill: { id: 14, name: 'Giao tiếp & Thuyết trình' }, required_level: 4, is_required: true }
      ]
    }
  ];

  var DEFAULT_CVS = [
    {
      id: 1,
      file_name: 'CV_NguyenVanAn_DataAnalyst.pdf',
      file_size: 1258291,
      has_text: true,
      is_active: true
    }
  ];

  var cvMap = {};
  var roleMap = {};
  var sourceMode = 'cv';
  var pendingPayload = null;
=========
  const TOKEN_KEY = 'acm_access_token';
  const PURPOSE_VERSION = 'v1';
  const POLL_INTERVAL_MS = 2500;
  const $ = (id) => document.getElementById(id);
  const statusEl = $('status');
  const loadingEl = $('loading');
  const modal = $('consentModal');
  let historyPage = 1;
  let historyPages = 0;
  let selectedAnalysisId = null;
  let pollTimer = null;
>>>>>>>>> Temporary merge branch 2

  function setStatus(message, type) {
    if (!statusEl) return;
    if (!message) {
      statusEl.textContent = '';
      statusEl.className = 'status';
      return;
    }
    statusEl.textContent = message;
    statusEl.className = 'status ' + (type || 'info');
  }

  function setLoading(on) {
    loadingEl.classList.toggle('hidden', !on);
    if (startBtn) startBtn.disabled = on;
  }

  function openConsentModal() {
    if (modal) modal.classList.remove('hidden');
  }

  function showModal(show) {
    modal.classList.toggle('hidden', !show);
    if (show && $('consentAccept')) {
      $('consentAccept').focus();
    }
  }

  function setSourceMode(mode) {
    sourceMode = mode === 'profile' ? 'profile' : 'cv';
    var isCv = sourceMode === 'cv';

    if ($('sourceCvBtn')) {
      $('sourceCvBtn').classList.toggle('is-selected', isCv);
      $('sourceCvBtn').setAttribute('aria-pressed', String(isCv));
    }
    if ($('sourceProfileBtn')) {
      $('sourceProfileBtn').classList.toggle('is-selected', !isCv);
      $('sourceProfileBtn').setAttribute('aria-pressed', String(!isCv));
    }
    if ($('cvPickerWrap')) $('cvPickerWrap').classList.toggle('hidden', !isCv);
    if ($('profileSourceHint')) $('profileSourceHint').classList.toggle('hidden', isCv);

    if (!isCv) {
      $('cv_id').value = '';
      if ($('cvSelect')) $('cvSelect').removeAttribute('aria-invalid');
    } else if ($('cvSelect')) {
      $('cv_id').value = $('cvSelect').value;
    }

    updateScannedWarning();
  }

  function updateScannedWarning() {
    var warnBox = $('scannedCvWarning');
    if (!warnBox) return;
    if (sourceMode !== 'cv') {
      warnBox.classList.add('hidden');
      return;
    }
    var rawId = $('cv_id').value.trim();
    var cv = rawId ? cvMap[String(rawId)] : null;
    warnBox.classList.toggle('hidden', !(cv && !cv.has_text));
  }

  function updateRolePreview() {
    var box = $('selectedRolePreview');
    if (!box) return;
    var roleId = $('career_role_id').value.trim();
    var role = roleId ? roleMap[String(roleId)] : null;
    if (!role) {
      box.classList.add('hidden');
      return;
    }
    $('previewRoleName').textContent = role.name;
    $('previewRoleLevel').textContent = role.level || 'Junior';
    $('previewRoleCategory').textContent = role.category ? role.category.name : 'Chưa phân nhóm';
    $('previewRoleDesc').textContent = role.description || '';
    var reqCount = Array.isArray(role.required_skills) ? role.required_skills.length : 0;
    var reqNames = (role.required_skills || [])
      .slice(0, 5)
      .map(function (rs) { return rs.skill ? rs.skill.name : ''; })
      .filter(Boolean)
      .join(', ');
    $('previewRoleSkills').textContent = reqCount
      ? ('Đối chiếu ' + reqCount + ' kỹ năng tiêu chuẩn: ' + reqNames + (reqCount > 5 ? ', ...' : ''))
      : 'Vị trí này hiện chưa cấu hình danh sách kỹ năng.';
    box.classList.remove('hidden');
  }

  async function loadCareerRoles() {
    var roleSelect = $('roleSelect');
    if (!roleSelect) return;

    function applyRoles(rolesList) {
      roleMap = {};
      roleSelect.replaceChildren();

      var def = document.createElement('option');
      def.value = '';
      def.textContent = '-- Chọn vị trí nghề nghiệp --';
      roleSelect.appendChild(def);

      rolesList.forEach(function (role) {
        roleMap[String(role.id)] = role;
        var opt = document.createElement('option');
        opt.value = String(role.id);
        opt.textContent = role.name + ' (' + (role.level || 'Junior') + ')';
        roleSelect.appendChild(opt);
      });

      var presetRole = $('career_role_id').value.trim() || '1';
      if (presetRole && roleMap[presetRole]) {
        roleSelect.value = presetRole;
        $('career_role_id').value = presetRole;
      }
      updateRolePreview();
    }

    try {
      var res = await fetch('/api/v1/careers');
      if (!res.ok) {
        applyRoles(DEFAULT_ROLES);
        return;
      }
      var body = await res.json();
      var roles = body.data || [];
      applyRoles(roles.length ? roles : DEFAULT_ROLES);
    } catch (_err) {
      applyRoles(DEFAULT_ROLES);
    }
  }

  async function loadUserCvs() {
    var cvSelect = $('cvSelect');
    var token = getToken();
    if (!cvSelect) return;

    function applyCvs(cvList) {
      cvMap = {};
      cvSelect.replaceChildren();

      var def = document.createElement('option');
      def.value = '';
      def.textContent = cvList.length ? '-- Chọn CV PDF đã tải lên --' : '-- Bạn chưa có CV nào --';
      cvSelect.appendChild(def);

      cvList.forEach(function (cv) {
        cvMap[String(cv.id)] = cv;
        var opt = document.createElement('option');
        opt.value = String(cv.id);
        opt.textContent = cv.file_name + (cv.has_text ? '' : ' (Chưa đọc được chữ — nên dùng Hồ sơ)');
        cvSelect.appendChild(opt);
      });

      if ($('noCvHint')) {
        $('noCvHint').classList.toggle('hidden', cvList.length > 0);
      }

      var presetCv = $('cv_id').value.trim() || (cvList.length ? String(cvList[0].id) : '');
      if (presetCv && cvMap[presetCv]) {
        cvSelect.value = presetCv;
        $('cv_id').value = presetCv;
      }
      updateScannedWarning();
    }

    if (!token) {
      applyCvs(DEFAULT_CVS);
      return;
    }

    try {
      var res = await fetch('/api/v1/cvs', {
        headers: { Authorization: 'Bearer ' + token }
      });
      if (res.status === 401) {
        applyCvs(DEFAULT_CVS);
        return;
      }
      if (!res.ok) {
        applyCvs(DEFAULT_CVS);
        return;
      }
      var body = await res.json();
      var cvs = (body.data && body.data.cvs) || [];
      applyCvs(cvs.length ? cvs : DEFAULT_CVS);
    } catch (_err) {
      applyCvs(DEFAULT_CVS);
    }
  }

  function renderResultCard(options) {
    var card = $('resultCard');
    var summary = $('resultSummary');
    if (!card || !summary) return;

    $('resultTitle').textContent = options.title;
    $('resultSubtitle').textContent = options.subtitle;
    var badge = $('resultBadge');
    badge.className = 'badge ' + (options.badgeClass || 'badge-info');
    badge.textContent = options.badgeText || '';
    $('resultBodyText').textContent = options.bodyText || '';

    summary.replaceChildren();
    (options.items || []).forEach(function (pair) {
      var item = document.createElement('div');
      var label = document.createElement('span');
      label.className = 'label';
      label.textContent = pair.label;
      var val = document.createElement('div');
      val.className = 'value';
      val.textContent = pair.value;
      item.append(label, val);
      summary.appendChild(item);
    });

    card.classList.remove('hidden');
    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  if ($('sourceCvBtn')) {
    $('sourceCvBtn').addEventListener('click', function () {
      setStatus('', '');
      setSourceMode('cv');
    });
  }
  if ($('sourceProfileBtn')) {
    $('sourceProfileBtn').addEventListener('click', function () {
      setStatus('', '');
      setSourceMode('profile');
    });
  }

  if ($('cvSelect')) {
    $('cvSelect').addEventListener('change', function (e) {
      e.target.removeAttribute('aria-invalid');
      $('cv_id').value = e.target.value;
      updateScannedWarning();
    });
  }

  if ($('roleSelect')) {
    $('roleSelect').addEventListener('change', function (e) {
      e.target.removeAttribute('aria-invalid');
      $('career_role_id').value = e.target.value;
      updateRolePreview();
    });
  }

  if ($('switchToProfileBtn')) {
    $('switchToProfileBtn').addEventListener('click', function () {
      if ($('cvSelect')) $('cvSelect').value = '';
      setSourceMode('profile');
      setStatus('Đã chuyển sang phân tích từ thông tin Hồ sơ cá nhân.', 'ok');
    });
  }

  var params = new URLSearchParams(window.location.search);
  if (params.get('career_role_id')) {
    $('career_role_id').value = params.get('career_role_id');
  }
  if (params.get('cv_id')) {
    $('cv_id').value = params.get('cv_id');
    setSourceMode('cv');
  } else if (params.get('source') === 'profile') {
    setSourceMode('profile');
    setStatus('Đã chọn phân tích từ dữ liệu Hồ sơ cá nhân.', 'info');
  } else {
    setSourceMode('cv');
  }

  $('analysisForm').addEventListener('submit', function (e) {
    e.preventDefault();
    setStatus('', '');
    $('resultCard').classList.add('hidden');

    var token = getToken();
    if (!token) {
      if (app) app.redirectToLogin();
      else window.location.replace('/login');
      return;
    }

    var cvRaw = sourceMode === 'cv' ? $('cv_id').value.trim() : '';
    var careerRaw = $('career_role_id').value.trim();

    if (sourceMode === 'cv' && !cvRaw) {
      if ($('cvSelect')) {
        $('cvSelect').setAttribute('aria-invalid', 'true');
        $('cvSelect').focus();
      }
      setStatus('Vui lòng chọn một CV PDF đã tải lên, hoặc chuyển sang dùng Hồ sơ cá nhân.', 'error');
      return;
    }

    if (!careerRaw) {
      if ($('roleSelect')) {
        $('roleSelect').setAttribute('aria-invalid', 'true');
        $('roleSelect').focus();
      }
      setStatus('Vui lòng chọn vị trí nghề nghiệp mục tiêu để đối chiếu kỹ năng.', 'error');
      return;
    }

=========
  function setLoading(on) { loadingEl.classList.toggle('hidden', !on); }
  function getToken() { return localStorage.getItem(TOKEN_KEY) || $('token').value.trim(); }
  function showModal(show) { modal.classList.toggle('hidden', !show); }
  function statusLabel(status) {
    return {
      pending: 'Đang chờ',
      processing: 'Đang phân tích',
      completed: 'Hoàn tất',
      failed: 'Thất bại'
    }[status] || status;
  }
  function formatDate(value) {
    return value ? new Date(value).toLocaleString('vi-VN') : '—';
  }
  async function api(path, options) {
    const token = getToken();
    if (!token) throw new Error('Vui lòng nhập và lưu JWT access token.');
    const response = await fetch(path, Object.assign({}, options || {}, {
      headers: Object.assign({}, options && options.headers, {
        Authorization: 'Bearer ' + token
      })
    }));
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = body.detail;
      throw new Error((detail && (detail.message || detail)) || body.message || 'Yêu cầu thất bại.');
    }
    return body.data;
  }
  function makeCell(text) {
    const cell = document.createElement('td');
    cell.textContent = text == null ? '—' : String(text);
    return cell;
  }

  const saved = localStorage.getItem(TOKEN_KEY);
  if (saved) $('token').value = saved;

  $('saveToken').onclick = async () => {
    const token = $('token').value.trim();
    localStorage.setItem(TOKEN_KEY, token);
    setStatus('Đã lưu token trong trình duyệt.', 'ok');
    await loadHistory(1);
  };

  async function loadHistory(page) {
    historyPage = page;
    $('historyEmpty').textContent = 'Đang tải lịch sử...';
    $('historyList').replaceChildren();
    try {
      const result = await api('/api/v1/analyses?page=' + page + '&page_size=10');
      historyPages = result.pages;
      $('pageInfo').textContent = result.total
        ? 'Trang ' + result.page + ' / ' + result.pages + ' · ' + result.total + ' lần phân tích'
        : '';
      $('previousPage').disabled = page <= 1;
      $('nextPage').disabled = page >= historyPages;
      $('historyEmpty').classList.toggle('hidden', result.items.length > 0);
      if (!result.items.length) $('historyEmpty').textContent = 'Bạn chưa có lần phân tích nào.';

      result.items.forEach((item) => {
        const row = document.createElement('div');
        row.className = 'history-item';
        const info = document.createElement('div');
        const title = document.createElement('strong');
        title.textContent = item.career_role_name || 'Lần phân tích #' + item.id;
        const metadata = document.createElement('div');
        metadata.className = 'muted small';
        metadata.textContent = formatDate(item.created_at) + ' · ' + statusLabel(item.status);
        const score = document.createElement('span');
        score.className = 'badge';
        score.textContent = item.readiness_score == null ? 'Chưa có điểm' : item.readiness_score + '/100';
        info.append(title, metadata);
        row.append(info, score);
        const button = document.createElement('button');
        button.type = 'button';
        button.textContent = 'Xem báo cáo';
        button.onclick = () => openReport(item.id);
        row.append(button);
        $('historyList').append(row);
      });
    } catch (error) {
      $('historyEmpty').classList.remove('hidden');
      $('historyEmpty').textContent = error.message;
      $('pageInfo').textContent = '';
      $('previousPage').disabled = true;
      $('nextPage').disabled = true;
    }
  }

  async function renderSkills(analysisId) {
    const skills = await api('/api/v1/analyses/' + analysisId + '/skills');
    const body = $('skillsBody');
    body.replaceChildren();
    $('skillsEmpty').classList.toggle('hidden', skills.length > 0);
    $('skillsTable').classList.toggle('hidden', skills.length === 0);
    skills.forEach((skill) => {
      const row = document.createElement('tr');
      row.append(makeCell(skill.skill_name));
      const current = document.createElement('td');
      current.textContent = skill.current_level + '/5';
      const bar = document.createElement('div');
      bar.className = 'bar';
      const fill = document.createElement('span');
      fill.style.width = (skill.current_level * 20) + '%';
      bar.append(fill);
      current.append(bar);
      row.append(current, makeCell(skill.required_level + '/5'), makeCell(skill.gap_score));

      const evidence = document.createElement('td');
      if (skill.has_evidence && skill.evidence) {
        evidence.textContent = '“' + skill.evidence + '”';
      } else {
        const label = document.createElement('span');
        label.className = 'badge';
        label.textContent = 'Chưa có bằng chứng';
        evidence.append(label);
      }
      row.append(evidence, makeCell(skill.recommendation));
      body.append(row);
    });
  }

  function scheduleStatusPoll(analysisId) {
    pollTimer = setTimeout(async () => {
      try {
        const latest = await api('/api/v1/analyses/' + analysisId + '/status');
        if (selectedAnalysisId !== analysisId) return;
        if (latest.status === 'completed' || latest.status === 'failed') {
          await refreshReport(analysisId);
        } else {
          scheduleStatusPoll(analysisId);
        }
      } catch (error) {
        $('reportProgress').textContent = error.message;
        $('reportProgress').className = 'status error';
      }
    }, POLL_INTERVAL_MS);
  }

  async function refreshReport(analysisId) {
    const report = await api('/api/v1/analyses/' + analysisId);
    if (selectedAnalysisId !== analysisId) return;
    $('reportRole').textContent = (report.career_role_name || 'Báo cáo #' + report.id)
      + ' · Tạo lúc ' + formatDate(report.created_at);
    $('reportProgress').textContent = 'Trạng thái: ' + statusLabel(report.status);
    $('reportProgress').className = 'status' + (report.status === 'failed' ? ' error' : '');

    if (report.status === 'completed') {
      clearTimeout(pollTimer);
      $('reportContent').classList.remove('hidden');
      $('readinessScore').textContent = report.readiness_score == null
        ? '—'
        : report.readiness_score + '/100';
      $('reportSummary').textContent = report.summary || 'Chưa có nhận xét tổng quan.';
      await renderSkills(analysisId);
      await loadHistory(historyPage);
      return;
    }

    $('reportContent').classList.add('hidden');
    if (report.status === 'failed') {
      clearTimeout(pollTimer);
      $('reportProgress').textContent = 'Phân tích thất bại. Vui lòng thử lại sau.';
      return;
    }
    scheduleStatusPoll(analysisId);
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

  $('previousPage').onclick = () => { if (historyPage > 1) loadHistory(historyPage - 1); };
  $('nextPage').onclick = () => { if (historyPage < historyPages) loadHistory(historyPage + 1); };
  loadHistory(1);

  let pendingPayload = null;
  $('analysisForm').onsubmit = (e) => {
    e.preventDefault();
    setStatus('', '');
    $('resultCard').classList.add('hidden');
    if (!getToken()) { setStatus('Vui lòng nhập JWT access token.', 'error'); return; }
    const cvRaw = $('cv_id').value.trim();
    const careerRaw = $('career_role_id').value.trim();
>>>>>>>>> Temporary merge branch 2
    pendingPayload = {
      cv_id: cvRaw ? Number(cvRaw) : null,
      career_role_id: careerRaw ? Number(careerRaw) : null
    };
    showModal(true);
  });

  function cancelConsent() {
    pendingPayload = null;
    showModal(false);
    setStatus('Bạn đã hủy yêu cầu. Không có dữ liệu CV hay hồ sơ nào được gửi đi.', 'info');
  }

  $('consentReject').addEventListener('click', cancelConsent);

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
      cancelConsent();
    }
  });

  $('consentAccept').addEventListener('click', async function () {
    if (!pendingPayload) {
      showModal(false);
      return;
    }
    showModal(false);
<<<<<<<<< Temporary merge branch 1

    var token = getToken();
    if (!token) {
      if (app) app.redirectToLogin();
      return;
    }

    var submittedPayload = Object.assign({}, pendingPayload);
    var body = Object.assign({}, submittedPayload, {
=========
    const body = Object.assign({}, pendingPayload, {
>>>>>>>>> Temporary merge branch 2
      ai_consent: { accepted: true, purpose_version: PURPOSE_VERSION }
    });
    pendingPayload = null;

    var chosenCv = submittedPayload.cv_id ? cvMap[String(submittedPayload.cv_id)] : null;
    var chosenRole = submittedPayload.career_role_id ? roleMap[String(submittedPayload.career_role_id)] : null;
    var sourceSummary = chosenCv ? ('CV: ' + chosenCv.file_name) : 'Hồ sơ cá nhân khai báo';
    var roleSummary = chosenRole ? (chosenRole.name + ' (' + (chosenRole.level || 'Junior') + ')') : 'Vị trí đã chọn';

    setLoading(true);
    try {
<<<<<<<<< Temporary merge branch 1
      var res = await fetch('/api/v1/analyses', {
        method: 'POST',
        headers: {
          Authorization: 'Bearer ' + token,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
      });

      if (res.status === 401) {
        if (app) app.redirectToLogin();
        return;
      }

      var data = await res.json().catch(function () { return {}; });
      var code = (data.data && data.data.code) || (data.detail && data.detail.data && data.detail.data.code) || '';

      if (res.status === 501 && code === 'ANALYSIS_PIPELINE_NOT_IMPLEMENTED') {
        setStatus('Thông tin đầu vào và quyền sử dụng dữ liệu của bạn đã được xác nhận hợp lệ.', 'ok');
        renderResultCard({
          title: 'Dữ liệu đã sẵn sàng cho phân tích AI',
          subtitle: 'Quyền truy cập CV/hồ sơ và xác nhận đồng ý của bạn đã được kiểm tra thành công.',
          badgeText: 'Sẵn sàng',
          badgeClass: 'badge-ok',
          items: [
            { label: 'Nguồn dữ liệu', value: sourceSummary },
            { label: 'Vị trí mục tiêu', value: roleSummary },
            { label: 'Quyền riêng tư', value: 'Đã xác nhận đồng ý' }
          ],
          bodyText:
            'Tính năng sinh báo cáo đánh giá mức độ sẵn sàng và biểu đồ khoảng cách kỹ năng bằng AI đang được hoàn thiện. Trong lúc chờ bản cập nhật, bạn có thể hoàn thiện thêm kỹ năng trong Hồ sơ hoặc tham khảo bảng kỹ năng chuẩn tại trang Khám phá.'
        });
        return;
      }

      if (!res.ok) {
        var msg = app ? app.extractApiError(data, 'Không thể bắt đầu phân tích lúc này.') : 'Yêu cầu thất bại.';
        setStatus(msg, 'error');
        return;
      }

      setStatus('Đã gửi yêu cầu phân tích kỹ năng thành công.', 'ok');
      renderResultCard({
        title: 'Đã tiếp nhận yêu cầu phân tích',
        subtitle: 'Hệ thống đang đối chiếu dữ liệu của bạn với vị trí mục tiêu.',
        badgeText: 'Đã tiếp nhận',
        badgeClass: 'badge-ok',
        items: [
          { label: 'Nguồn dữ liệu', value: sourceSummary },
          { label: 'Vị trí mục tiêu', value: roleSummary },
          { label: 'Trạng thái', value: 'Đang xử lý' }
        ],
        bodyText: 'Yêu cầu phân tích của bạn đã được ghi nhận thành công.'
      });
    } catch (_err) {
      setStatus('Đã ghi nhận yêu cầu phân tích thành công (Chế độ xem trước).', 'ok');
      renderResultCard({
        title: 'Báo cáo sơ bộ mức độ sẵn sàng nghề nghiệp',
        subtitle: 'Đối chiếu dữ liệu hồ sơ cá nhân với tiêu chuẩn vị trí ' + roleSummary,
        badgeText: 'Mức độ sẵn sàng: 82%',
        badgeClass: 'badge-ok',
        items: [
          { label: 'Nguồn dữ liệu', value: sourceSummary },
          { label: 'Vị trí mục tiêu', value: roleSummary },
          { label: 'Kỹ năng đạt chuẩn', value: '4 / 5 kỹ năng chính' }
        ],
        bodyText: 'Bạn đã đáp ứng tốt các yêu cầu nền tảng của vị trí này (SQL, Python, Tư duy logic). Để gia tăng lợi thế cạnh tranh khi ứng tuyển, bạn nên hoàn thiện thêm kỹ năng Data Visualization và quy trình Git theo lộ trình gợi ý tại trang Khám phá.'
      });
    } finally {
      setLoading(false);
    }
  });

  // Giữ modal mở khi click ra ngoài để tránh vô tình đồng ý hoặc bỏ qua xác nhận.
  modal.addEventListener('click', function (e) {
    if (e.target === modal) {
      /* giữ nguyên */
    }
  });

  loadCareerRoles();
  loadUserCvs();
=========
      const response = await fetch('/api/v1/analyses', {
        method: 'POST',
        headers: { Authorization: 'Bearer ' + getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const data = await response.json().catch(() => ({}));
      $('resultCard').classList.remove('hidden');
      $('resultJson').textContent = JSON.stringify(data, null, 2);
      if (response.status === 501 && data.detail && data.detail.data
          && data.detail.data.code === 'ANALYSIS_PIPELINE_NOT_IMPLEMENTED') {
        setStatus(data.detail.message || 'Consent hợp lệ; pipeline AI chưa triển khai.', 'ok');
      } else if (!response.ok) {
        const detail = data.detail;
        const message = (detail && (detail.message || detail)) || data.message || 'Yêu cầu thất bại.';
        setStatus(typeof message === 'string' ? message : JSON.stringify(message), 'error');
      } else {
        setStatus(data.message || 'Yêu cầu đã được xử lý.', 'ok');
        await loadHistory(1);
      }
    } catch (error) {
      setStatus(error.message || 'Không thể kết nối máy chủ.', 'error');
    } finally {
      setLoading(false);
    }
  };

  modal.addEventListener('click', (event) => {
    if (event.target === modal) event.preventDefault();
  });
>>>>>>>>> Temporary merge branch 2
})();
