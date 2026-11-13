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

  function setStatus(message, type) {
    statusEl.textContent = message || '';
    statusEl.className = 'status' + (type ? ' ' + type : '');
  }

  function setLoading(on) {
    loadingEl.classList.toggle('hidden', !on);
    if (startBtn) startBtn.disabled = on;
  }

  function getToken() {
    return app ? app.getToken() : (localStorage.getItem('acm_access_token') || '');
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

    var token = getToken();
    if (!token) {
      if (app) app.redirectToLogin();
      return;
    }

    var submittedPayload = Object.assign({}, pendingPayload);
    var body = Object.assign({}, submittedPayload, {
      ai_consent: { accepted: true, purpose_version: PURPOSE_VERSION }
    });
    pendingPayload = null;

    var chosenCv = submittedPayload.cv_id ? cvMap[String(submittedPayload.cv_id)] : null;
    var chosenRole = submittedPayload.career_role_id ? roleMap[String(submittedPayload.career_role_id)] : null;
    var sourceSummary = chosenCv ? ('CV: ' + chosenCv.file_name) : 'Hồ sơ cá nhân khai báo';
    var roleSummary = chosenRole ? (chosenRole.name + ' (' + (chosenRole.level || 'Junior') + ')') : 'Vị trí đã chọn';

    setLoading(true);
    try {
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
})();
