(function () {
  const TOKEN_KEY = 'acm_access_token';
  const MAX_SIZE = 5 * 1024 * 1024;
  const $ = (id) => document.getElementById(id);
  const statusEl = $('status');
  const loadingEl = $('loading');
  let activeDetailCvId = null;

  function setStatus(message, type) {
    statusEl.textContent = message || '';
    statusEl.className = 'status' + (type ? ' ' + type : '');
  }
  function setLoading(on) { loadingEl.classList.toggle('hidden', !on); }
  function getToken() { return localStorage.getItem(TOKEN_KEY) || $('token').value.trim(); }

  function formatBytes(bytes) {
    const size = Number(bytes || 0);
    if (size < 1024) return size + ' bytes';
    if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB (' + size + ' bytes)';
    return (size / (1024 * 1024)).toFixed(2) + ' MB';
  }

  function formatDate(iso) {
    if (!iso) return '-';
    const dt = new Date(iso);
    if (Number.isNaN(dt.getTime())) return String(iso);
    return dt.toLocaleString('vi-VN');
  }

  function renderWarning(warning, hasText) {
    const box = $('scanWarningBox');
    if (hasText || !warning) {
      box.classList.add('hidden');
      return;
    }
    $('warnCause').textContent = warning.cause || 'File PDF có thể là ảnh quét không chứa lớp văn bản.';
    $('warnGuidance').textContent = warning.guidance || 'Vui lòng cập nhật Hồ sơ cá nhân để chuyển sang phân tích từ dữ liệu hồ sơ khai báo.';
    const actionsList = $('warnActions');
    actionsList.replaceChildren();
    (warning.recommended_actions || []).forEach((item) => {
      const li = document.createElement('li');
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
    if ($('resultHeading')) $('resultHeading').textContent = headingText || 'Kết quả CV';
    $('resName').textContent = cv.file_name || '';
    $('resSize').textContent = formatBytes(cv.file_size);
    const text = cv.extracted_text || '';
    const hasText = cv.has_text !== undefined ? Boolean(cv.has_text) : Boolean(text.trim());
    $('resExtract').textContent = hasText
      ? 'Thành công (đã trích xuất văn bản)'
      : 'Cảnh báo: Không trích xuất được văn bản (nghi vấn PDF ảnh quét)';
    if ($('resState')) {
      $('resState').textContent = cv.is_active === false ? 'Đã ẩn (xóa mềm)' : 'Đang hoạt động';
    }
    $('resText').value = text;
    renderWarning(warning, hasText);
  }

  async function loadCvList() {
    const token = getToken();
    const tbody = $('cvListBody');
    const countEl = $('cvListCount');
    if (!token) {
      countEl.textContent = '';
      tbody.replaceChildren();
      const tr = document.createElement('tr');
      const td = document.createElement('td');
      td.colSpan = 7;
      td.className = 'muted';
      td.textContent = 'Nhập JWT token để tải danh sách CV.';
      tr.appendChild(td);
      tbody.appendChild(tr);
      return;
    }

    const includeInactive = Boolean($('showInactiveCvs') && $('showInactiveCvs').checked);
    setLoading(true);
    try {
      const res = await fetch('/api/v1/cvs?include_inactive=' + includeInactive, {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        const msg = (body.detail && (body.detail.message || body.detail)) || body.message || 'Không tải được danh sách CV.';
        setStatus(typeof msg === 'string' ? msg : JSON.stringify(msg), 'error');
        return;
      }

      const cvs = (body.data && body.data.cvs) || [];
      countEl.textContent = cvs.length + ' phiên bản';
      tbody.replaceChildren();

      if (!cvs.length) {
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = 7;
        td.className = 'muted';
        td.textContent = 'Chưa có CV nào trong danh sách.';
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
      }

      cvs.forEach((cv) => {
        const tr = document.createElement('tr');
        if (!cv.is_active) tr.className = 'cv-row-inactive';

        const tdName = document.createElement('td');
        const nameStrong = document.createElement('strong');
        nameStrong.textContent = cv.file_name || ('CV #' + cv.id);
        tdName.appendChild(nameStrong);

        const tdSize = document.createElement('td');
        tdSize.textContent = formatBytes(cv.file_size);

        const tdDate = document.createElement('td');
        tdDate.textContent = formatDate(cv.created_at);

        const tdExtract = document.createElement('td');
        const extBadge = document.createElement('span');
        extBadge.className = 'badge ' + (cv.has_text ? 'badge-ok' : 'badge-warn');
        extBadge.textContent = cv.has_text ? 'Có văn bản' : 'Không có văn bản';
        tdExtract.appendChild(extBadge);

        const tdAnalysis = document.createElement('td');
        const anaBadge = document.createElement('span');
        if (cv.has_analysis) {
          anaBadge.className = 'badge badge-info';
          anaBadge.textContent = 'Đã phân tích (' + (cv.analysis_count || 1) + ')';
        } else {
          anaBadge.className = 'badge badge-muted';
          anaBadge.textContent = 'Chưa phân tích';
        }
        tdAnalysis.appendChild(anaBadge);

        const tdActive = document.createElement('td');
        const actBadge = document.createElement('span');
        actBadge.className = 'badge ' + (cv.is_active ? 'badge-ok' : 'badge-muted');
        actBadge.textContent = cv.is_active ? 'Hoạt động' : 'Đã ẩn (xóa mềm)';
        tdActive.appendChild(actBadge);

        const tdActions = document.createElement('td');
        const actionGroup = document.createElement('div');
        actionGroup.className = 'action-group';

        const viewBtn = document.createElement('button');
        viewBtn.type = 'button';
        viewBtn.className = 'secondary small';
        viewBtn.textContent = 'Chi tiết';
        viewBtn.addEventListener('click', () => viewCvDetail(cv.id));
        actionGroup.appendChild(viewBtn);

        if (cv.is_active) {
          const delBtn = document.createElement('button');
          delBtn.type = 'button';
          delBtn.className = 'danger small';
          delBtn.textContent = cv.has_analysis ? 'Ẩn CV' : 'Xóa';
          delBtn.addEventListener('click', () => deleteCv(cv));
          actionGroup.appendChild(delBtn);
        }

        tdActions.appendChild(actionGroup);
        tr.append(tdName, tdSize, tdDate, tdExtract, tdAnalysis, tdActive, tdActions);
        tbody.appendChild(tr);
      });
    } catch (_err) {
      setStatus('Không thể kết nối máy chủ.', 'error');
    } finally {
      setLoading(false);
    }
  }

  async function viewCvDetail(cvId) {
    const token = getToken();
    if (!token) { setStatus('Vui lòng nhập JWT access token.', 'error'); return; }
    const includeInactive = Boolean($('showInactiveCvs') && $('showInactiveCvs').checked);
    setLoading(true);
    try {
      const res = await fetch('/api/v1/cvs/' + cvId + '?include_inactive=' + includeInactive, {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        const msg = (body.detail && (body.detail.message || body.detail)) || body.message || 'Không lấy được chi tiết CV.';
        setStatus(typeof msg === 'string' ? msg : JSON.stringify(msg), 'error');
        return;
      }
      const data = body.data || {};
      const cv = data.cv || {};
      renderCvResult(cv, data.warning || null, 'Chi tiết phiên bản CV #' + cv.id);
      if (!cv.has_text && data.warning) {
        setStatus('CV này không trích xuất được văn bản. Vui lòng xem cảnh báo và hướng dẫn bên dưới.', 'warning');
      } else {
        setStatus('Đã tải chi tiết CV #' + cv.id + '.', 'ok');
      }
      $('resultCard').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch (_err) {
      setStatus('Không thể kết nối máy chủ.', 'error');
    } finally {
      setLoading(false);
    }
  }

  async function deleteCv(cv) {
    const token = getToken();
    if (!token) { setStatus('Vui lòng nhập JWT access token.', 'error'); return; }
    const confirmMsg = cv.has_analysis
      ? 'CV "' + cv.file_name + '" đã gắn với báo cáo phân tích lịch sử. Hệ thống sẽ thực hiện XÓA MỀM (ẩn trạng thái hoạt động) để bảo toàn lịch sử. Bạn có chắc muốn tiếp tục?'
      : 'Bạn có chắc muốn xóa vĩnh viễn CV "' + cv.file_name + '"?';
    if (!window.confirm(confirmMsg)) return;

    setLoading(true);
    try {
      const res = await fetch('/api/v1/cvs/' + cv.id, {
        method: 'DELETE',
        headers: { 'Authorization': 'Bearer ' + token }
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        const msg = (body.detail && (body.detail.message || body.detail)) || body.message || 'Xóa CV thất bại.';
        setStatus(typeof msg === 'string' ? msg : JSON.stringify(msg), 'error');
        return;
      }
      const delResult = body.data || {};
      if (activeDetailCvId && Number(cv.id) === activeDetailCvId) {
        if (delResult.deletion_type === 'soft') {
          if ($('resState')) $('resState').textContent = 'Đã ẩn (xóa mềm)';
        } else {
          activeDetailCvId = null;
          $('resultCard').classList.add('hidden');
        }
      }
      setStatus(body.message || 'Thao tác thành công.', 'ok');
      await loadCvList();
    } catch (_err) {
      setStatus('Không thể kết nối máy chủ.', 'error');
    } finally {
      setLoading(false);
    }
  }

  const saved = localStorage.getItem(TOKEN_KEY);
  if (saved) $('token').value = saved;
  $('saveToken').onclick = () => {
    localStorage.setItem(TOKEN_KEY, $('token').value.trim());
    setStatus('Đã lưu token trong trình duyệt.', 'ok');
    loadCvList();
  };

  if ($('refreshCvs')) $('refreshCvs').onclick = loadCvList;
  if ($('showInactiveCvs')) $('showInactiveCvs').onchange = loadCvList;

  $('cvFile').onchange = (e) => {
    const f = e.target.files && e.target.files[0];
    $('fileInfo').textContent = f ? ('Tên: ' + f.name + ' | Dung lượng: ' + f.size + ' bytes') : '';
  };

  $('cvForm').onsubmit = async (e) => {
    e.preventDefault();
    setStatus('', '');
    const file = $('cvFile').files && $('cvFile').files[0];
    if (!file) { setStatus('Vui lòng chọn file PDF.', 'error'); return; }
    if (file.size > MAX_SIZE) { setStatus('File vượt quá 5MB. Vui lòng chọn file nhỏ hơn.', 'error'); return; }
    const token = getToken();
    if (!token) { setStatus('Vui lòng nhập JWT access token.', 'error'); return; }

    const form = new FormData();
    form.append('file', file); // browser sets multipart boundary automatically
    setLoading(true);
    try {
      const res = await fetch('/api/v1/cvs', { method: 'POST', headers: { 'Authorization': 'Bearer ' + token }, body: form });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = body.detail;
        const msg = Array.isArray(detail) ? detail.map((d) => d.msg || JSON.stringify(d)).join('; ') : (detail || body.message || 'Tải lên thất bại');
        setStatus(msg, 'error');
        return;
      }
      const data = body.data || {};
      const cv = data.cv || {};
      const warning = data.warning || null;
      const hasText = data.has_text !== undefined ? Boolean(data.has_text) : Boolean((cv.extracted_text || '').trim());
      renderCvResult(cv, warning, 'Kết quả tải lên CV');
      setStatus(body.message || 'Upload CV thành công.', hasText ? 'ok' : 'warning');
      await loadCvList();
    } catch (err) {
      setStatus('Không thể kết nối máy chủ.', 'error');
    } finally { setLoading(false); }
  };

  if (saved) loadCvList();
})();
