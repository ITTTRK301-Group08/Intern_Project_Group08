(function () {
  const TOKEN_KEY = 'acm_access_token';
  const PURPOSE_VERSION = 'v1';
  const $ = (id) => document.getElementById(id);
  const statusEl = $('status');
  const loadingEl = $('loading');
  const modal = $('consentModal');
  let cvMap = {};

  function setStatus(message, type) {
    statusEl.textContent = message || '';
    statusEl.className = 'status' + (type ? ' ' + type : '');
  }
  function setLoading(on) { loadingEl.classList.toggle('hidden', !on); }
  function getToken() { return localStorage.getItem(TOKEN_KEY) || $('token').value.trim(); }
  function showModal(show) { modal.classList.toggle('hidden', !show); }

  function updateScannedWarning() {
    const warnBox = $('scannedCvWarning');
    if (!warnBox) return;
    const rawId = $('cv_id').value.trim();
    const cv = rawId ? cvMap[String(rawId)] : null;
    if (cv && !cv.has_text) {
      warnBox.classList.remove('hidden');
    } else {
      warnBox.classList.add('hidden');
    }
  }

  async function loadCareerRoles() {
    const roleSelect = $('roleSelect');
    if (!roleSelect) return;
    try {
      const res = await fetch('/api/v1/careers');
      if (!res.ok) return;
      const body = await res.json();
      const roles = body.data || [];
      roleSelect.replaceChildren();
      const def = document.createElement('option');
      def.value = '';
      def.textContent = '-- Chọn vị trí nghề nghiệp --';
      roleSelect.appendChild(def);
      roles.forEach((role) => {
        const opt = document.createElement('option');
        opt.value = String(role.id);
        opt.textContent = role.name + ' (' + (role.level || 'Junior') + ')';
        roleSelect.appendChild(opt);
      });
      if ($('career_role_id').value.trim()) {
        roleSelect.value = $('career_role_id').value.trim();
      }
    } catch (_err) {
      // keep manual input usable even if catalog fails to preload
    }
  }

  async function loadUserCvs() {
    const cvSelect = $('cvSelect');
    const token = getToken();
    if (!cvSelect || !token) return;
    try {
      const res = await fetch('/api/v1/cvs', {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      if (!res.ok) return;
      const body = await res.json();
      const cvs = (body.data && body.data.cvs) || [];
      cvMap = {};
      cvSelect.replaceChildren();
      const def = document.createElement('option');
      def.value = '';
      def.textContent = '-- Không chọn CV (Phân tích từ dữ liệu hồ sơ khai báo) --';
      cvSelect.appendChild(def);
      cvs.forEach((cv) => {
        cvMap[String(cv.id)] = cv;
        const opt = document.createElement('option');
        opt.value = String(cv.id);
        opt.textContent = '#' + cv.id + ' - ' + cv.file_name + (cv.has_text ? '' : ' (⚠️ Không trích xuất được văn bản)');
        cvSelect.appendChild(opt);
      });
      if ($('cv_id').value.trim()) {
        cvSelect.value = $('cv_id').value.trim();
      }
      updateScannedWarning();
    } catch (_err) {
      // ignore preload errors
    }
  }

  const saved = localStorage.getItem(TOKEN_KEY);
  if (saved) $('token').value = saved;
  $('saveToken').onclick = () => {
    localStorage.setItem(TOKEN_KEY, $('token').value.trim());
    setStatus('Đã lưu token trong trình duyệt.', 'ok');
    loadUserCvs();
  };

  if ($('cvSelect')) {
    $('cvSelect').addEventListener('change', (e) => {
      $('cv_id').value = e.target.value;
      updateScannedWarning();
    });
  }
  $('cv_id').addEventListener('input', () => {
    if ($('cvSelect')) $('cvSelect').value = $('cv_id').value.trim();
    updateScannedWarning();
  });

  if ($('roleSelect')) {
    $('roleSelect').addEventListener('change', (e) => {
      $('career_role_id').value = e.target.value;
    });
  }
  $('career_role_id').addEventListener('input', () => {
    if ($('roleSelect')) $('roleSelect').value = $('career_role_id').value.trim();
  });

  if ($('switchToProfileBtn')) {
    $('switchToProfileBtn').addEventListener('click', () => {
      $('cv_id').value = '';
      if ($('cvSelect')) $('cvSelect').value = '';
      updateScannedWarning();
      setStatus('Đã chuyển sang chế độ phân tích từ dữ liệu hồ sơ khai báo (không dùng CV ảnh quét).', 'ok');
    });
  }

  const params = new URLSearchParams(window.location.search);
  if (params.get('career_role_id')) {
    $('career_role_id').value = params.get('career_role_id');
  }
  if (params.get('source') === 'profile') {
    $('cv_id').value = '';
    setStatus('Chế độ phân tích từ dữ liệu hồ sơ khai báo đã được chọn (bỏ trống CV).', 'ok');
  }

  let pendingPayload = null;

  $('analysisForm').onsubmit = (e) => {
    e.preventDefault();
    setStatus('', '');
    $('resultCard').classList.add('hidden');
    const token = getToken();
    if (!token) { setStatus('Vui lòng nhập JWT access token.', 'error'); return; }
    const cvRaw = $('cv_id').value.trim();
    const careerRaw = $('career_role_id').value.trim();
    pendingPayload = {
      cv_id: cvRaw ? Number(cvRaw) : null,
      career_role_id: careerRaw ? Number(careerRaw) : null
    };
    // Never send analysis request before explicit user consent.
    showModal(true);
  };

  $('consentReject').onclick = () => {
    pendingPayload = null;
    showModal(false);
    setStatus('Bạn đã từ chối. Quy trình dừng lại và không gửi dữ liệu CV/hồ sơ đến AI.', '');
  };

  $('consentAccept').onclick = async () => {
    if (!pendingPayload) { showModal(false); return; }
    showModal(false);
    const token = getToken();
    const body = Object.assign({}, pendingPayload, {
      ai_consent: { accepted: true, purpose_version: PURPOSE_VERSION }
    });
    pendingPayload = null;
    setLoading(true);
    try {
      const res = await fetch('/api/v1/analyses', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const data = await res.json().catch(() => ({}));
      $('resultCard').classList.remove('hidden');
      $('resultJson').textContent = JSON.stringify(data, null, 2);
      if (res.status === 501 && data.data && data.data.code === 'ANALYSIS_PIPELINE_NOT_IMPLEMENTED') {
        setStatus(data.message || 'Consent hợp lệ; pipeline AI chưa triển khai (Task 4).', 'ok');
      } else if (!res.ok) {
        const msg = (data.detail && (data.detail.message || data.detail)) || data.message || 'Yêu cầu thất bại.';
        setStatus(typeof msg === 'string' ? msg : JSON.stringify(msg), 'error');
      } else {
        setStatus(data.message || 'Yêu cầu đã được xử lý.', 'ok');
      }
    } catch (err) {
      setStatus('Không thể kết nối máy chủ.', 'error');
    } finally { setLoading(false); }
  };

  // Close modal only via explicit actions (no implicit accept).
  modal.addEventListener('click', (e) => { if (e.target === modal) { /* keep open */ } });

  loadCareerRoles();
  if (saved) loadUserCvs();
})();
