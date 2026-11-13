(function () {
  'use strict';

  if (window.__LaBanCvLoaded__) return;
  window.__LaBanCvLoaded__ = true;

  var app = window.LaBanApp;
  var MAX_SIZE = 5 * 1024 * 1024;
  var $ = function (id) { return document.getElementById(id); };
  var statusEl = $('status');
  var loadingEl = $('loading');
  var uploadBtn = $('uploadBtn');
  var activeDetailCvId = null;
  var pendingDeleteCv = null;
  var droppedFile = null;

  var DEMO_CVS = [
    {
      id: 1,
      file_name: 'CV_NguyenVanAn_DataAnalyst.pdf',
      file_size: 1258291,
      created_at: new Date().toISOString(),
      has_text: true,
      has_analysis: true,
      analysis_count: 1,
      is_active: true,
      extracted_text: 'HỌ VÀ TÊN: NGUYỄN VĂN AN\nEmail: an.nguyen@example.com | Điện thoại: 0912 345 678\nMục tiêu nghề nghiệp: Ứng tuyển vị trí Data Analyst (Intern)\nHọc vấn: Đại học Bách Khoa — Chuyên ngành Kỹ thuật phần mềm (GPA: 3.4/4.0)\nKỹ năng chính: Python (Pandas, NumPy), SQL (MySQL, PostgreSQL), Power BI, Git, Excel nâng cao.\nDự án nổi bật: Xây dựng dashboard phân tích xu hướng mua hàng của người tiêu dùng thương mại điện tử; tối ưu hóa truy vấn SQL giảm 40% thời gian xử lý dữ liệu.'
    }
  ];

  function setStatus(message, type) {
    statusEl.textContent = message || '';
    statusEl.className = 'status' + (type ? ' ' + type : '');
  }

  function setLoading(on) {
    loadingEl.classList.toggle('hidden', !on);
  }

  function setUploading(busy) {
    if (!uploadBtn) return;
    uploadBtn.disabled = busy;
    uploadBtn.textContent = busy ? 'Đang tải lên...' : 'Tải CV lên';
  }

  function requireToken() {
    var token = app ? app.getToken() : (localStorage.getItem('acm_access_token') || '');
    if (!token) {
      var isDirect = window.location.protocol === 'file:' || window.location.pathname.indexOf('.html') >= 0 || !window.location.host;
      if (isDirect) {
        token = 'demo_student_token';
        try { localStorage.setItem('acm_access_token', token); } catch (_) {}
        return token;
      }
      if (app) app.redirectToLogin();
      else window.location.replace('/login');
      return null;
    }
    return token;
  }

  function formatBytes(bytes) {
    return app ? app.formatBytes(bytes) : (bytes + ' B');
  }

  function formatDate(iso) {
    return app ? app.formatDate(iso) : (iso || '-');
  }

  function formatWarningCause(warning) {
    var raw = (warning && warning.cause ? String(warning.cause) : '').toLowerCase();
    if (raw.indexOf('anh quet') >= 0 && raw.indexOf('mot phan') < 0) {
      return 'Tệp PDF này là bản ảnh quét (chỉ chứa hình ảnh, không có lớp văn bản) nên hệ thống chưa thể đọc nội dung chữ.';
    }
    if (raw.indexOf('qua ngan') >= 0) {
      return 'Nội dung chữ trích xuất được quá ngắn hoặc không đủ thông tin (có thể là tệp ảnh quét một phần).';
    }
    if (raw.indexOf('khong trich xuat duoc') >= 0) {
      return 'Không trích xuất được nội dung văn bản từ tệp PDF (có thể là tệp dạng ảnh quét).';
    }
    return (warning && warning.cause) || 'Tệp PDF có thể là bản ảnh quét chưa có lớp văn bản.';
  }

  function renderWarning(warning, hasText) {
    var box = $('scanWarningBox');
    if (hasText || !warning) {
      box.classList.add('hidden');
      return;
    }

    $('warnCause').textContent = formatWarningCause(warning);
    $('warnGuidance').textContent =
      'Bạn có thể xuất lại CV thành PDF có lớp văn bản (từ Word hoặc Google Docs), hoặc dùng trực tiếp thông tin Hồ sơ cá nhân để phân tích.';

    var actionsList = $('warnActions');
    actionsList.replaceChildren();
    var tips = [
      'Cập nhật đầy đủ điểm mạnh, kỹ năng tự đánh giá và kinh nghiệm trong Hồ sơ cá nhân.',
      'Chuyển sang trang Phân tích kỹ năng và chọn nguồn dữ liệu từ Hồ sơ cá nhân.',
      'Hoặc xuất lại CV PDF dạng văn bản (không dùng ảnh chụp/scan) rồi tải lên lại.'
    ];
    tips.forEach(function (item) {
      var li = document.createElement('li');
      li.textContent = item;
      actionsList.appendChild(li);
    });

    $('warnProfileLink').href = warning.profile_url || '/profile';
    $('warnAnalysisLink').href = warning.analysis_url || '/analysis?source=profile';
    box.classList.remove('hidden');
  }

  function renderCvResult(cv, warning, headingText) {
    activeDetailCvId = cv && cv.id ? Number(cv.id) : null;
    $('resultCard').classList.remove('hidden');
    if ($('resultHeading')) {
      $('resultHeading').textContent = headingText || ('Chi tiết: ' + (cv.file_name || 'CV'));
    }
    $('resName').textContent = cv.file_name || 'Chưa rõ tên tệp';
    $('resSize').textContent = formatBytes(cv.file_size);

    var text = cv.extracted_text || '';
    var hasText = cv.has_text !== undefined ? Boolean(cv.has_text) : Boolean(text.trim());
    $('resExtract').textContent = hasText
      ? 'Đọc thành công (đủ dữ liệu chữ)'
      : 'Chưa đọc được văn bản (nghi vấn PDF ảnh quét)';

    if ($('resState')) {
      $('resState').textContent = cv.is_active === false ? 'Đã lưu trữ' : 'Đang hoạt động';
    }

    $('resText').value = text;
    if ($('extractedTextWrap')) {
      $('extractedTextWrap').classList.toggle('hidden', !hasText);
    }
    if ($('analyzeWithCvLink')) {
      $('analyzeWithCvLink').href = activeDetailCvId
        ? ('/analysis?cv_id=' + encodeURIComponent(activeDetailCvId))
        : '/analysis';
    }

    renderWarning(warning, hasText);
  }

  function showDeleteModal(cv) {
    pendingDeleteCv = cv;
    var modal = $('deleteConfirmModal');
    var titleEl = $('deleteModalTitle');
    var msgEl = $('deleteModalMessage');
    var confirmBtn = $('deleteConfirmBtn');
    if (!modal || !msgEl || !confirmBtn) return;

    if (cv.has_analysis) {
      titleEl.textContent = 'Lưu trữ CV khỏi danh sách chính?';
      msgEl.textContent =
        'CV "' + cv.file_name + '" đã từng dùng cho báo cáo phân tích trước đó. Hệ thống sẽ chuyển CV này sang trạng thái lưu trữ (ẩn khỏi danh sách mặc định) để không làm mất lịch sử phân tích của bạn.';
      confirmBtn.textContent = 'Ẩn / Lưu trữ CV';
    } else {
      titleEl.textContent = 'Xóa CV này?';
      msgEl.textContent =
        'Bạn có chắc muốn xóa vĩnh viễn CV "' + cv.file_name + '"? Thao tác này không thể hoàn tác.';
      confirmBtn.textContent = 'Xóa vĩnh viễn';
    }
    modal.classList.remove('hidden');
  }

  function hideDeleteModal() {
    pendingDeleteCv = null;
    if ($('deleteConfirmModal')) {
      $('deleteConfirmModal').classList.add('hidden');
    }
  }

  async function executeDeleteCv(cv) {
    var token = requireToken();
    if (!token || !cv) return;

    setLoading(true);
    try {
      var res = await fetch('/api/v1/cvs/' + cv.id, {
        method: 'DELETE',
        headers: { Authorization: 'Bearer ' + token }
      });
      if (res.status === 401) {
        if (app) app.redirectToLogin();
        return;
      }
      var body = await res.json().catch(function () { return {}; });
      if (!res.ok) {
        var errMsg = app ? app.extractApiError(body, 'Không thể xóa CV lúc này.') : 'Xóa CV thất bại.';
        setStatus(errMsg, 'error');
        return;
      }

      var delResult = body.data || {};
      if (activeDetailCvId && Number(cv.id) === activeDetailCvId) {
        if (delResult.deletion_type === 'soft') {
          if ($('resState')) $('resState').textContent = 'Đã lưu trữ';
        } else {
          activeDetailCvId = null;
          $('resultCard').classList.add('hidden');
        }
      }

      var okMsg = delResult.deletion_type === 'soft'
        ? 'Đã chuyển CV "' + cv.file_name + '" sang trạng thái lưu trữ để giữ lịch sử phân tích.'
        : 'Đã xóa CV "' + cv.file_name + '" thành công.';
      setStatus(okMsg, 'ok');
      await loadCvList();
    } catch (_err) {
      setStatus('Không thể kết nối máy chủ để xóa CV.', 'error');
    } finally {
      setLoading(false);
    }
  }

  function renderCvRows(cvs, includeInactive) {
    var tbody = $('cvListBody');
    var countEl = $('cvListCount');
    if (!tbody) return;
    if (countEl) countEl.textContent = cvs.length + ' phiên bản';
    tbody.replaceChildren();

    if (!cvs.length) {
      var trEmpty = document.createElement('tr');
      var tdEmpty = document.createElement('td');
      tdEmpty.colSpan = 7;
      tdEmpty.className = 'muted';
      tdEmpty.textContent = includeInactive
        ? 'Bạn chưa tải lên CV nào.'
        : 'Chưa có CV đang hoạt động. Hãy tải lên một tệp PDF ở khung phía trên.';
      trEmpty.appendChild(tdEmpty);
      tbody.appendChild(trEmpty);
      return;
    }

    cvs.forEach(function (cv) {
      var tr = document.createElement('tr');
      if (!cv.is_active) tr.className = 'cv-row-inactive';

      var tdName = document.createElement('td');
      var nameStrong = document.createElement('strong');
      nameStrong.textContent = cv.file_name || 'CV PDF';
      tdName.appendChild(nameStrong);

      var tdSize = document.createElement('td');
      tdSize.textContent = formatBytes(cv.file_size);

      var tdDate = document.createElement('td');
      tdDate.textContent = formatDate(cv.created_at);

      var tdExtract = document.createElement('td');
      var extBadge = document.createElement('span');
      extBadge.className = 'badge ' + (cv.has_text ? 'badge-ok' : 'badge-warn');
      extBadge.textContent = cv.has_text ? 'Đọc được chữ' : 'Không có chữ';
      tdExtract.appendChild(extBadge);

      var tdAnalysis = document.createElement('td');
      var anaBadge = document.createElement('span');
      if (cv.has_analysis) {
        anaBadge.className = 'badge badge-info';
        anaBadge.textContent = 'Đã phân tích (' + (cv.analysis_count || 1) + ')';
      } else {
        anaBadge.className = 'badge badge-muted';
        anaBadge.textContent = 'Chưa phân tích';
      }
      tdAnalysis.appendChild(anaBadge);

      var tdActive = document.createElement('td');
      var actBadge = document.createElement('span');
      actBadge.className = 'badge ' + (cv.is_active ? 'badge-ok' : 'badge-muted');
      actBadge.textContent = cv.is_active ? 'Đang dùng' : 'Đã lưu trữ';
      tdActive.appendChild(actBadge);

      var tdActions = document.createElement('td');
      var actionGroup = document.createElement('div');
      actionGroup.className = 'action-group';

      var viewBtn = document.createElement('button');
      viewBtn.type = 'button';
      viewBtn.className = 'secondary small';
      viewBtn.textContent = 'Xem chi tiết';
      viewBtn.addEventListener('click', function () { viewCvDetail(cv.id); });
      actionGroup.appendChild(viewBtn);

      if (cv.is_active) {
        var delBtn = document.createElement('button');
        delBtn.type = 'button';
        delBtn.className = 'danger small';
        delBtn.textContent = cv.has_analysis ? 'Lưu trữ' : 'Xóa';
        delBtn.addEventListener('click', function () { showDeleteModal(cv); });
        actionGroup.appendChild(delBtn);
      }

      tdActions.appendChild(actionGroup);
      tr.append(tdName, tdSize, tdDate, tdExtract, tdAnalysis, tdActive, tdActions);
      tbody.appendChild(tr);
    });
  }

  async function loadCvList() {
    var token = requireToken();
    var includeInactive = Boolean($('showInactiveCvs') && $('showInactiveCvs').checked);
    if (!token) {
      renderCvRows(DEMO_CVS, includeInactive);
      return;
    }

    setLoading(true);
    try {
      var res = await fetch('/api/v1/cvs?include_inactive=' + includeInactive, {
        headers: { Authorization: 'Bearer ' + token }
      });
      if (res.status === 401) {
        if (app) app.redirectToLogin();
        return;
      }
      var body = await res.json().catch(function () { return {}; });
      if (!res.ok) {
        renderCvRows(DEMO_CVS, includeInactive);
        return;
      }

      var cvs = (body.data && body.data.cvs) || [];
      renderCvRows(cvs.length ? cvs : DEMO_CVS, includeInactive);
    } catch (_err) {
      renderCvRows(DEMO_CVS, includeInactive);
    } finally {
      setLoading(false);
    }
  }

  async function viewCvDetail(cvId) {
    var token = requireToken();
    if (!token) return;
    var includeInactive = Boolean($('showInactiveCvs') && $('showInactiveCvs').checked);
    setLoading(true);
    setStatus('', '');
    try {
      var res = await fetch('/api/v1/cvs/' + cvId + '?include_inactive=' + includeInactive, {
        headers: { Authorization: 'Bearer ' + token }
      });
      if (res.status === 401) {
        if (app) app.redirectToLogin();
        return;
      }
      var body = await res.json().catch(function () { return {}; });
      if (!res.ok) {
        var msg = app ? app.extractApiError(body, 'Không lấy được chi tiết CV.') : 'Không lấy được chi tiết CV.';
        setStatus(msg, 'error');
        return;
      }
      var data = body.data || {};
      var cv = data.cv || {};
      renderCvResult(cv, data.warning || null, 'Chi tiết: ' + (cv.file_name || 'CV'));
      if (!cv.has_text && data.warning) {
        setStatus('CV này chưa trích xuất được nội dung chữ. Vui lòng xem gợi ý xử lý bên dưới.', 'warning');
      }
      $('resultCard').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch (_err) {
      var demo = DEMO_CVS.find(function (c) { return String(c.id) === String(cvId); }) || DEMO_CVS[0];
      renderCvResult(demo, null, 'Chi tiết: ' + demo.file_name);
      setStatus('Đang ở chế độ xem trước (Offline). Đã hiển thị CV mẫu.', 'ok');
    } finally {
      setLoading(false);
    }
  }

  function showSelectedFileInfo(file) {
    var infoEl = $('fileInfo');
    if (!infoEl) return;
    if (!file) {
      infoEl.textContent = '';
      infoEl.classList.add('hidden');
      return;
    }
    infoEl.textContent = 'Tệp đã chọn: ' + file.name + ' (' + formatBytes(file.size) + ')';
    infoEl.classList.remove('hidden');

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setStatus('Chỉ hỗ trợ tệp định dạng PDF (.pdf). Vui lòng chọn lại.', 'error');
    } else if (file.size > MAX_SIZE) {
      setStatus('Dung lượng tệp vượt quá 5 MB. Vui lòng nén hoặc chọn tệp nhỏ hơn.', 'error');
    } else {
      setStatus('', '');
    }
  }

  var dropzone = $('cvDropzone');
  var fileInput = $('cvFile');
  if (dropzone && fileInput) {
    ['dragenter', 'dragover'].forEach(function (evtName) {
      dropzone.addEventListener(evtName, function (e) {
        e.preventDefault();
        dropzone.classList.add('is-dragover');
      });
    });
    ['dragleave', 'drop'].forEach(function (evtName) {
      dropzone.addEventListener(evtName, function (e) {
        e.preventDefault();
        dropzone.classList.remove('is-dragover');
      });
    });
    dropzone.addEventListener('drop', function (e) {
      var files = e.dataTransfer && e.dataTransfer.files;
      if (files && files.length) {
        droppedFile = files[0];
        try {
          fileInput.files = files;
        } catch (_) {
          /* dùng fallback droppedFile nếu trình duyệt chặn gán input.files */
        }
        showSelectedFileInfo(files[0]);
      }
    });
    fileInput.addEventListener('change', function (e) {
      droppedFile = null;
      var f = e.target.files && e.target.files[0];
      showSelectedFileInfo(f || null);
    });
  }

  if ($('closeResultCard')) {
    $('closeResultCard').addEventListener('click', function () {
      activeDetailCvId = null;
      $('resultCard').classList.add('hidden');
    });
  }

  if ($('deleteCancelBtn')) {
    $('deleteCancelBtn').addEventListener('click', hideDeleteModal);
  }
  if ($('deleteConfirmBtn')) {
    $('deleteConfirmBtn').addEventListener('click', function () {
      var cv = pendingDeleteCv;
      hideDeleteModal();
      if (cv) executeDeleteCv(cv);
    });
  }
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && $('deleteConfirmModal') && !$('deleteConfirmModal').classList.contains('hidden')) {
      hideDeleteModal();
    }
  });
  if ($('deleteConfirmModal')) {
    $('deleteConfirmModal').addEventListener('click', function (e) {
      if (e.target === $('deleteConfirmModal')) hideDeleteModal();
    });
  }

  if ($('refreshCvs')) $('refreshCvs').addEventListener('click', loadCvList);
  if ($('showInactiveCvs')) $('showInactiveCvs').addEventListener('change', loadCvList);

  $('cvForm').addEventListener('submit', async function (e) {
    e.preventDefault();
    setStatus('', '');

    var file = (fileInput && fileInput.files && fileInput.files[0]) || droppedFile;
    if (!file) {
      setStatus('Vui lòng chọn một tệp CV định dạng PDF.', 'error');
      return;
    }
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setStatus('Chỉ hỗ trợ tệp định dạng PDF (.pdf).', 'error');
      return;
    }
    if (file.size === 0) {
      setStatus('Tệp PDF bạn chọn đang bị trống.', 'error');
      return;
    }
    if (file.size > MAX_SIZE) {
      setStatus('Dung lượng tệp vượt quá 5 MB. Vui lòng chọn tệp nhỏ hơn.', 'error');
      return;
    }

    var token = requireToken();
    if (!token) return;

    var form = new FormData();
    form.append('file', file);
    setUploading(true);
    setLoading(true);
    try {
      var res = await fetch('/api/v1/cvs', {
        method: 'POST',
        headers: { Authorization: 'Bearer ' + token },
        body: form
      });
      if (res.status === 401) {
        if (app) app.redirectToLogin();
        return;
      }
      var body = await res.json().catch(function () { return {}; });
      if (!res.ok) {
        var errMsg = app ? app.extractApiError(body, 'Tải lên CV thất bại.') : 'Tải lên CV thất bại.';
        setStatus(errMsg, 'error');
        return;
      }

      var data = body.data || {};
      var cv = data.cv || {};
      var warning = data.warning || null;
      var hasText = data.has_text !== undefined ? Boolean(data.has_text) : Boolean((cv.extracted_text || '').trim());

      renderCvResult(cv, warning, 'Kết quả tải lên: ' + (cv.file_name || 'CV mới'));
      setStatus(
        hasText
          ? 'Đã tải lên và đọc nội dung CV thành công.'
          : 'CV đã được tải lên nhưng chưa đọc được văn bản. Vui lòng xem hướng dẫn bên dưới.',
        hasText ? 'ok' : 'warning'
      );

      droppedFile = null;
      $('cvForm').reset();
      showSelectedFileInfo(null);
      await loadCvList();
    } catch (_err) {
      var demo = DEMO_CVS[0];
      renderCvResult(demo, null, 'Chi tiết: ' + demo.file_name);
      setStatus('Đang ở chế độ xem trước (Offline). Đã hiển thị CV mẫu.', 'ok');
    } finally {
      setUploading(false);
      setLoading(false);
    }
  });

  window.viewCvDetail = viewCvDetail;
  loadCvList();
})();
