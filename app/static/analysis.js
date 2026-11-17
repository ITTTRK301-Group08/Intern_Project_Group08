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

  var historyPage = 1;
  var historyTotalPages = 1;
  var pollTimer = null;

  var isDirectMode =
    window.location.protocol === 'file:' ||
    window.location.pathname.indexOf('/app/static/') !== -1 ||
    !window.location.host;

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

  var DEFAULT_HISTORY = [
    {
      id: 1,
      career_role_name: 'Data Analyst',
      career_role_id: 1,
      readiness_score: 82,
      status: 'completed',
      created_at: new Date(Date.now() - 2 * 86400000).toISOString(),
      summary: 'Ứng viên có nền tảng tốt về truy vấn dữ liệu SQL và lập trình Python cơ bản. Cần bổ sung kinh nghiệm về trực quan hóa dữ liệu (Tableau/PowerBI) và kỹ năng quản lý mã nguồn Git để đạt độ sẵn sàng tối đa.'
    },
    {
      id: 2,
      career_role_name: 'Backend Developer',
      career_role_id: 3,
      readiness_score: 68,
      status: 'completed',
      created_at: new Date(Date.now() - 6 * 86400000).toISOString(),
      summary: 'Đáp ứng tốt kiến thức cơ bản về cơ sở dữ liệu và API RESTful. Khoảng cách kỹ năng cần cải thiện là kiến trúc bất đồng bộ FastAPI và tối ưu hóa hiệu năng truy vấn nâng cao.'
    }
  ];

  var DEFAULT_SKILLS_GAP = {
    1: [
      { skill_name: 'Python', current_level: 3, target_level: 3, gap_score: 0, has_evidence: true, evidence: 'Đã xây dựng các script xử lý dữ liệu với pandas, numpy trong đồ án môn học.', recommendation: 'Rèn luyện thêm kỹ thuật tối ưu hóa vector hóa (vectorization).' },
      { skill_name: 'SQL', current_level: 4, target_level: 4, gap_score: 0, has_evidence: true, evidence: 'Thành thạo JOIN, Window functions, Aggregation trên PostgreSQL và MySQL.', recommendation: 'Tìm hiểu thêm về indexing và query execution plan.' },
      { skill_name: 'Data Visualization', current_level: 2, target_level: 3, gap_score: 1, has_evidence: true, evidence: 'Có kinh nghiệm vẽ biểu đồ seaborn/matplotlib cơ bản.', recommendation: 'Thực hành thiết kế dashboard báo cáo thực tế trên PowerBI hoặc Tableau.' },
      { skill_name: 'Git', current_level: 2, target_level: 3, gap_score: 1, has_evidence: false, evidence: 'Chưa thấy minh chứng rõ ràng về Git flow trong CV.', recommendation: 'Tạo tài khoản GitHub và đóng góp ít nhất 2 dự án có phân nhánh chuẩn.' }
    ],
    2: [
      { skill_name: 'Python', current_level: 3, target_level: 4, gap_score: 1, has_evidence: true, evidence: 'Kinh nghiệm viết script Python 2 năm.', recommendation: 'Thực hành lập trình hướng đối tượng OOP nâng cao và type hints.' },
      { skill_name: 'FastAPI', current_level: 2, target_level: 3, gap_score: 1, has_evidence: true, evidence: 'Đã viết 1 đồ án backend sử dụng FastAPI.', recommendation: 'Học sâu về Dependency Injection, Pydantic v2 validation và BackgroundTasks.' },
      { skill_name: 'SQL', current_level: 3, target_level: 4, gap_score: 1, has_evidence: true, evidence: 'Thiết kế cơ sở dữ liệu quan hệ đạt chuẩn 3NF.', recommendation: 'Luyện tập tối ưu hóa câu truy vấn chậm và phân mảnh cơ sở dữ liệu.' }
    ]
  };

  var cvMap = {};
  var roleMap = {};
  var sourceMode = 'cv';
  var pendingPayload = null;

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

  function setLoading(show) {
    if (loadingEl) loadingEl.classList.toggle('hidden', !show);
    if (startBtn) startBtn.disabled = Boolean(show);
  }

  function openConsentModal() {
    if (modal) modal.classList.remove('hidden');
  }

  function closeConsentModal() {
    if (modal) modal.classList.add('hidden');
    pendingPayload = null;
  }

  function getAuthToken() {
    return (app && typeof app.getToken === 'function') ? app.getToken() : (localStorage.getItem('acm_access_token') || '');
  }

  function formatRelativeDate(isoStr) {
    if (!isoStr) return '';
    try {
      var d = new Date(isoStr);
      return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch (_e) {
      return isoStr;
    }
  }

  function updateRolePreview(roleId) {
    var role = roleMap[String(roleId)];
    var preview = $('selectedRolePreview');
    if (!role || !preview) return;

    var nameEl = $('previewRoleName');
    var levelEl = $('previewRoleLevel');
    var catEl = $('previewRoleCategory');
    var descEl = $('previewRoleDesc');
    var skillsEl = $('previewRoleSkills');

    if (nameEl) nameEl.textContent = role.name || 'Vị trí nghề nghiệp';
    if (levelEl) levelEl.textContent = role.level || 'Fresher';
    if (catEl) catEl.textContent = (role.category && role.category.name) || 'Tiêu chuẩn ngành';
    if (descEl) descEl.textContent = role.description || '';

    if (skillsEl) {
      var skillNames = (role.required_skills || []).map(function (s) {
        return (s.skill && s.skill.name) || s.name || '';
      }).filter(Boolean);
      skillsEl.textContent = skillNames.length
        ? 'Đối chiếu ' + skillNames.length + ' kỹ năng tiêu chuẩn: ' + skillNames.slice(0, 5).join(', ') + (skillNames.length > 5 ? '...' : '')
        : 'Chưa có kỹ năng tiêu chuẩn được định nghĩa cho vị trí này.';
    }
  }

  function populateRoleSelect(roles) {
    var select = $('roleSelect');
    if (!select) return;
    select.replaceChildren();

    var emptyOpt = document.createElement('option');
    emptyOpt.value = '';
    emptyOpt.textContent = '-- Chọn vị trí nghề nghiệp mục tiêu --';
    select.appendChild(emptyOpt);

    roles.forEach(function (role) {
      roleMap[String(role.id)] = role;
      var opt = document.createElement('option');
      opt.value = String(role.id);
      opt.textContent = role.name + (role.level ? ' (' + role.level + ')' : '');
      select.appendChild(opt);
    });

    if (roles.length > 0) {
      select.value = String(roles[0].id);
      $('career_role_id').value = String(roles[0].id);
      updateRolePreview(roles[0].id);
    }
  }

  function populateCvSelect(cvs) {
    var select = $('cvSelect');
    var noCvHint = $('noCvHint');
    if (!select) return;
    select.replaceChildren();

    var emptyOpt = document.createElement('option');
    emptyOpt.value = '';
    emptyOpt.textContent = '-- Chọn CV PDF đã tải lên --';
    select.appendChild(emptyOpt);

    cvs.forEach(function (cv) {
      cvMap[String(cv.id)] = cv;
      var opt = document.createElement('option');
      opt.value = String(cv.id);
      var sizeKb = Math.round((cv.file_size || 0) / 1024);
      opt.textContent = (cv.file_name || 'CV #' + cv.id) + ' (' + sizeKb + ' KB' + (cv.is_active ? ' · Hiện tại' : '') + ')';
      select.appendChild(opt);
    });

    if (cvs.length > 0) {
      select.value = String(cvs[0].id);
      $('cv_id').value = String(cvs[0].id);
      if (noCvHint) noCvHint.classList.add('hidden');
      checkSelectedCvText(cvs[0].id);
    } else {
      if (noCvHint) noCvHint.classList.remove('hidden');
      setSourceMode('profile');
    }
  }

  function checkSelectedCvText(cvId) {
    var warning = $('scannedCvWarning');
    if (!warning) return;
    var cv = cvMap[String(cvId)];
    if (cv && cv.has_text === false) {
      warning.classList.remove('hidden');
    } else {
      warning.classList.add('hidden');
    }
  }

  function setSourceMode(mode) {
    sourceMode = mode;
    var cvBtn = $('sourceCvBtn');
    var profileBtn = $('sourceProfileBtn');
    var cvWrap = $('cvPickerWrap');
    var profileHint = $('profileSourceHint');

    if (mode === 'cv') {
      if (cvBtn) {
        cvBtn.classList.add('is-selected');
        cvBtn.setAttribute('aria-pressed', 'true');
      }
      if (profileBtn) {
        profileBtn.classList.remove('is-selected');
        profileBtn.setAttribute('aria-pressed', 'false');
      }
      if (cvWrap) cvWrap.classList.remove('hidden');
      if (profileHint) profileHint.classList.add('hidden');
      var cvVal = $('cvSelect') ? $('cvSelect').value : '';
      if ($('cv_id')) $('cv_id').value = cvVal;
      checkSelectedCvText(cvVal);
    } else {
      if (profileBtn) {
        profileBtn.classList.add('is-selected');
        profileBtn.setAttribute('aria-pressed', 'true');
      }
      if (cvBtn) {
        cvBtn.classList.remove('is-selected');
        cvBtn.setAttribute('aria-pressed', 'false');
      }
      if (cvWrap) cvWrap.classList.add('hidden');
      if (profileHint) profileHint.classList.remove('hidden');
      if ($('cv_id')) $('cv_id').value = '';
      if ($('scannedCvWarning')) $('scannedCvWarning').classList.add('hidden');
    }
  }

  function loadCareerRoles() {
    if (isDirectMode) {
      populateRoleSelect(DEFAULT_ROLES);
      return;
    }
    fetch('/api/v1/catalog/roles')
      .then(function (r) {
        if (!r.ok) throw new Error('Không thể tải danh sách vị trí');
        return r.json();
      })
      .then(function (res) {
        var roles = (res && res.data) || [];
        populateRoleSelect(roles);
      })
      .catch(function () {
        populateRoleSelect([]);
        setStatus('Không thể tải danh sách vị trí mục tiêu. Vui lòng thử lại.', 'error');
      });
  }

  function loadUserCvs() {
    if (isDirectMode) {
      populateCvSelect(DEFAULT_CVS);
      return;
    }
    var token = getAuthToken();
    fetch('/api/v1/cvs', {
      headers: { Authorization: 'Bearer ' + token }
    })
      .then(function (r) {
        if (!r.ok) throw new Error('Không thể tải danh sách CV');
        return r.json();
      })
      .then(function (res) {
        var cvs = (res && res.data) || [];
        populateCvSelect(cvs);
      })
      .catch(function () {
        populateCvSelect([]);
        setStatus('Không thể tải danh sách CV của bạn. Vui lòng thử lại.', 'error');
      });
  }

  // --- Lịch sử phân tích & Hiển thị báo cáo chi tiết ---

  function renderHistoryList(items) {
    var container = $('historyList');
    var emptyEl = $('historyEmpty');
    if (!container) return;
    container.replaceChildren();

    if (!items || items.length === 0) {
      if (emptyEl) emptyEl.classList.remove('hidden');
      return;
    }
    if (emptyEl) emptyEl.classList.add('hidden');

    items.forEach(function (analysis) {
      var item = document.createElement('div');
      item.className = 'history-item';

      var meta = document.createElement('div');
      meta.className = 'history-meta';

      var title = document.createElement('div');
      title.className = 'history-title';
      title.textContent = analysis.career_role_name || 'Phiên phân tích #' + analysis.id;

      var sub = document.createElement('div');
      sub.className = 'history-sub';
      var statusBadge = analysis.status === 'completed'
        ? 'Hoàn tất'
        : analysis.status === 'failed'
          ? 'Thất bại'
          : analysis.status === 'processing'
            ? 'Đang xử lý...'
            : 'Chờ xử lý';
      var scoreText = analysis.readiness_score != null ? ' · Điểm sẵn sàng: ' + analysis.readiness_score + '/100' : '';
      sub.textContent = 'Thời gian: ' + formatRelativeDate(analysis.created_at) + ' · ' + statusBadge + scoreText;

      meta.appendChild(title);
      meta.appendChild(sub);

      var viewBtn = document.createElement('button');
      viewBtn.type = 'button';
      viewBtn.className = 'btn secondary-btn small';
      viewBtn.textContent = 'Xem chi tiết →';
      viewBtn.onclick = function () {
        loadReport(analysis.id, analysis);
      };

      item.appendChild(meta);
      item.appendChild(viewBtn);
      container.appendChild(item);
    });
  }

  function updatePaginationControls(page, totalPages) {
    var prevBtn = $('previousPage');
    var nextBtn = $('nextPage');
    var info = $('pageInfo');

    if (info) info.textContent = 'Trang ' + page + ' / ' + Math.max(1, totalPages);
    if (prevBtn) {
      prevBtn.disabled = (page <= 1);
      prevBtn.onclick = function () {
        if (page > 1) loadHistory(page - 1);
      };
    }
    if (nextBtn) {
      nextBtn.disabled = (page >= totalPages);
      nextBtn.onclick = function () {
        if (page < totalPages) loadHistory(page + 1);
      };
    }
  }

  function loadHistory(page) {
    historyPage = page || 1;
    if (isDirectMode) {
      historyTotalPages = 1;
      renderHistoryList(DEFAULT_HISTORY);
      updatePaginationControls(historyPage, historyTotalPages);
      return;
    }

    var token = getAuthToken();
    fetch('/api/v1/analyses?page=' + historyPage + '&page_size=5', {
      headers: { Authorization: 'Bearer ' + token }
    })
      .then(function (r) {
        if (!r.ok) throw new Error('Không thể tải lịch sử phân tích');
        return r.json();
      })
      .then(function (res) {
        if (res && res.data) {
          var items = res.data.items || [];
          historyTotalPages = res.data.pages || Math.max(1, Math.ceil((res.data.total || 0) / 5));
          renderHistoryList(items);
          updatePaginationControls(historyPage, historyTotalPages);
        } else {
          renderHistoryList([]);
          updatePaginationControls(1, 1);
        }
      })
      .catch(function () {
        renderHistoryList([]);
        updatePaginationControls(1, 1);
        setStatus('Không thể tải lịch sử phân tích. Vui lòng thử lại.', 'error');
      });
  }

  function loadReport(analysisId, cachedAnalysis) {
    if (pollTimer) clearInterval(pollTimer);

    var card = $('reportCard');
    var content = $('reportContent');
    var progress = $('reportProgress');
    var roleEl = $('reportRole');
    var scoreEl = $('readinessScore');
    var summaryEl = $('reportSummary');
    var table = $('skillsTable');
    var body = $('skillsBody');
    var skillsEmpty = $('skillsEmpty');

    if (card) {
      card.classList.remove('hidden');
      card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    if (cachedAnalysis && roleEl) {
      roleEl.textContent = 'Vị trí mục tiêu: ' + (cachedAnalysis.career_role_name || 'Tiêu chuẩn ngành');
    }

    if (isDirectMode) {
      if (progress) progress.textContent = '';
      if (content) content.classList.remove('hidden');
      var mock = cachedAnalysis || DEFAULT_HISTORY[0];
      if (scoreEl) scoreEl.textContent = String(mock.readiness_score || 80);
      if (summaryEl) summaryEl.textContent = mock.summary || 'Phân tích năng lực hoàn tất.';

      var mockSkills = DEFAULT_SKILLS_GAP[analysisId] || DEFAULT_SKILLS_GAP[1];
      renderSkillsTable(mockSkills);
      return;
    }

    var token = getAuthToken();
    var headers = { Authorization: 'Bearer ' + token };

    if (progress) progress.textContent = 'Đang tải chi tiết báo cáo...';

    Promise.all([
      fetch('/api/v1/analyses/' + analysisId, { headers: headers }).then(function (r) {
        if (!r.ok) throw new Error('Không thể tải báo cáo');
        return r.json();
      }),
      fetch('/api/v1/analyses/' + analysisId + '/skills', { headers: headers }).then(function (r) {
        if (!r.ok) throw new Error('Không thể tải chi tiết kỹ năng');
        return r.json();
      })
    ])
      .then(function (results) {
        var reportData = results[0] && results[0].data;
        var skillsData = results[1] && results[1].data;

        if (!reportData) {
          if (progress) progress.textContent = 'Không tìm thấy chi tiết báo cáo.';
          return;
        }

        if (roleEl) roleEl.textContent = 'Vị trí mục tiêu: ' + (reportData.career_role_name || 'Tiêu chuẩn ngành');
        if (progress) progress.textContent = '';

        if (reportData.status === 'pending' || reportData.status === 'processing') {
          if (progress) progress.textContent = 'Hệ thống đang phân tích dữ liệu kỹ năng của bạn...';
          if (content) content.classList.add('hidden');
          pollReportStatus(analysisId);
          return;
        }

        if (content) content.classList.remove('hidden');
        if (scoreEl) scoreEl.textContent = reportData.readiness_score != null ? String(reportData.readiness_score) : '--';
        if (summaryEl) summaryEl.textContent = reportData.summary || 'Chưa có tóm tắt đánh giá.';

        renderSkillsTable(skillsData || []);
      })
      .catch(function () {
        if (progress) progress.textContent = 'Không thể tải báo cáo từ máy chủ. Vui lòng thử lại.';
        if (content) content.classList.add('hidden');
      });
  }

  function pollReportStatus(analysisId) {
    var token = getAuthToken();
    pollTimer = setInterval(function () {
      fetch('/api/v1/analyses/' + analysisId + '/status', {
        headers: { Authorization: 'Bearer ' + token }
      })
        .then(function (r) { return r.json(); })
        .then(function (res) {
          var status = res && res.data && res.data.status;
          if (status === 'completed' || status === 'failed') {
            clearInterval(pollTimer);
            loadReport(analysisId);
            loadHistory(historyPage);
          }
        })
        .catch(function () {
          clearInterval(pollTimer);
        });
    }, POLL_INTERVAL_MS);
  }

  function renderSkillsTable(skills) {
    var table = $('skillsTable');
    var body = $('skillsBody');
    var skillsEmpty = $('skillsEmpty');
    if (!table || !body) return;

    body.replaceChildren();

    if (!skills || skills.length === 0) {
      table.classList.add('hidden');
      if (skillsEmpty) skillsEmpty.classList.remove('hidden');
      return;
    }

    if (skillsEmpty) skillsEmpty.classList.add('hidden');
    table.classList.remove('hidden');

    skills.forEach(function (s) {
      var tr = document.createElement('tr');

      var tdSkill = document.createElement('td');
      tdSkill.innerHTML = '<strong>' + (s.skill_name || 'Kỹ năng') + '</strong>';

      var tdCurrent = document.createElement('td');
      tdCurrent.innerHTML = '<span class="skill-level-pill">Mức ' + (s.current_level != null ? s.current_level : 0) + '</span>';

      var tdTarget = document.createElement('td');
      tdTarget.innerHTML = '<span class="skill-level-pill" style="border-color:var(--primary);color:var(--primary-deep)">Mức ' + (s.target_level != null ? s.target_level : 3) + '</span>';

      var tdGap = document.createElement('td');
      var gap = s.gap_score != null ? s.gap_score : Math.max(0, (s.target_level || 0) - (s.current_level || 0));
      var gapBadgeClass = gap === 0 ? 'badge badge-ok' : (gap === 1 ? 'badge badge-info' : 'badge badge-warn');
      tdGap.innerHTML = '<span class="' + gapBadgeClass + '">' + (gap === 0 ? 'Đạt chuẩn' : 'Thiếu ' + gap + ' bậc') + '</span>';

      var tdEvidence = document.createElement('td');
      tdEvidence.textContent = s.evidence || (s.has_evidence ? 'Có minh chứng trong hồ sơ' : 'Chưa ghi nhận');
      tdEvidence.className = 'small muted';

      var tdRec = document.createElement('td');
      tdRec.textContent = s.recommendation || 'Tham gia khóa học đề xuất để rèn luyện.';
      tdRec.className = 'small';

      tr.appendChild(tdSkill);
      tr.appendChild(tdCurrent);
      tr.appendChild(tdTarget);
      tr.appendChild(tdGap);
      tr.appendChild(tdEvidence);
      tr.appendChild(tdRec);

      body.appendChild(tr);
    });
  }

  function renderResultCard(data) {
    var card = $('resultCard');
    if (!card) return;

    $('resultTitle').textContent = data.title || 'Kết quả phân tích';
    $('resultSubtitle').textContent = data.subtitle || '';
    var badge = $('resultBadge');
    if (badge) {
      badge.textContent = data.badgeText || '';
      badge.className = 'badge ' + (data.badgeClass || 'badge-info');
    }

    var summaryContainer = $('resultSummary');
    if (summaryContainer) {
      summaryContainer.replaceChildren();
      (data.items || []).forEach(function (item) {
        var div = document.createElement('div');
        div.className = 'detail-item';
        div.innerHTML = '<span class="detail-label">' + item.label + '</span><strong class="detail-value">' + item.value + '</strong>';
        summaryContainer.appendChild(div);
      });
    }

    var bodyEl = $('resultBodyText');
    if (bodyEl) bodyEl.textContent = data.bodyText || '';

    card.classList.remove('hidden');
    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  // --- Sự kiện tương tác ---

  $('sourceCvBtn').addEventListener('click', function () { setSourceMode('cv'); });
  $('sourceProfileBtn').addEventListener('click', function () { setSourceMode('profile'); });

  $('cvSelect').addEventListener('change', function () {
    var val = this.value;
    $('cv_id').value = val;
    checkSelectedCvText(val);
  });

  $('roleSelect').addEventListener('change', function () {
    var val = this.value;
    $('career_role_id').value = val;
    updateRolePreview(val);
  });

  var switchToProfileBtn = $('switchToProfileBtn');
  if (switchToProfileBtn) {
    switchToProfileBtn.addEventListener('click', function () { setSourceMode('profile'); });
  }

  var closeReportBtn = $('closeReportBtn');
  if (closeReportBtn) {
    closeReportBtn.addEventListener('click', function () {
      var card = $('reportCard');
      if (card) card.classList.add('hidden');
      if (pollTimer) clearInterval(pollTimer);
    });
  }

  $('consentReject').addEventListener('click', function () {
    closeConsentModal();
    setStatus('Bạn đã từ chối chia sẻ dữ liệu. Yêu cầu phân tích đã được hủy bỏ an toàn.', 'info');
  });

  $('analysisForm').addEventListener('submit', function (e) {
    e.preventDefault();
    setStatus('');

    var roleId = $('career_role_id').value || $('roleSelect').value;
    if (!roleId) {
      setStatus('Vui lòng chọn vị trí nghề nghiệp mục tiêu.', 'error');
      return;
    }

    var payload = {
      career_role_id: parseInt(roleId, 10),
    };

    if (sourceMode === 'cv') {
      var cvId = $('cv_id').value || $('cvSelect').value;
      if (!cvId) {
        setStatus('Vui lòng chọn CV để phân tích hoặc chuyển sang dùng Hồ sơ cá nhân.', 'error');
        return;
      }
      payload.cv_id = parseInt(cvId, 10);
    }

    pendingPayload = payload;
    openConsentModal();
  });

  $('consentAccept').addEventListener('click', async function () {
    if (!pendingPayload) return;
    var payload = Object.assign({}, pendingPayload);
    payload.ai_consent = { accepted: true, purpose_version: PURPOSE_VERSION };
    closeConsentModal();
    setLoading(true);
    setStatus('Đang gửi yêu cầu và đối chiếu thông tin năng lực...', 'info');

    var role = roleMap[String(payload.career_role_id)];
    var roleSummary = role ? (role.name + ' (' + (role.level || 'Fresher') + ')') : 'Vị trí đã chọn';
    var sourceSummary = payload.cv_id ? 'CV PDF #' + payload.cv_id : 'Hồ sơ cá nhân';

    if (isDirectMode) {
      setTimeout(function () {
        setLoading(false);
        setStatus('Đã ghi nhận yêu cầu phân tích thành công (Chế độ xem trước).', 'ok');
        renderResultCard({
          title: 'Báo cáo sơ bộ mức độ sẵn sàng nghề nghiệp',
          subtitle: 'Đối chiếu dữ liệu với tiêu chuẩn vị trí ' + roleSummary,
          badgeText: 'Mức độ sẵn sàng: 82%',
          badgeClass: 'badge-ok',
          items: [
            { label: 'Nguồn dữ liệu', value: sourceSummary },
            { label: 'Vị trí mục tiêu', value: roleSummary },
            { label: 'Kỹ năng đạt chuẩn', value: '4 / 5 kỹ năng chính' }
          ],
          bodyText: 'Bạn đã đáp ứng tốt các yêu cầu nền tảng của vị trí này. Để gia tăng lợi thế cạnh tranh, bạn có thể tham khảo thêm Lộ trình 30 ngày hoặc Dashboard radar kỹ năng.'
        });
        loadHistory(1);
      }, 600);
      return;
    }

    try {
      var token = getAuthToken();
      var res = await fetch('/api/v1/analyses', {
        method: 'POST',
        headers: {
          Authorization: 'Bearer ' + token,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });
      var data = await res.json().catch(function () { return {}; });

      if (!res.ok) {
        var msg = (app && typeof app.extractApiError === 'function')
          ? app.extractApiError(data, 'Không thể bắt đầu phân tích lúc này.')
          : (data.message || data.detail || 'Yêu cầu thất bại.');
        setStatus(typeof msg === 'string' ? msg : JSON.stringify(msg), 'error');
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
      loadHistory(1);
      if (data && data.data && data.data.id) {
        loadReport(data.data.id);
      }
    } catch (_err) {
      setStatus('Không thể kết nối để gửi yêu cầu phân tích. Vui lòng thử lại.', 'error');
    } finally {
      setLoading(false);
    }
  });

  if (modal) {
    modal.addEventListener('click', function (e) {
      if (e.target === modal) {
        /* giữ nguyên */
      }
    });
  }

  loadCareerRoles();
  loadUserCvs();
  loadHistory(1);
})();
