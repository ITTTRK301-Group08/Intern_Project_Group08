(function () {
  const TOKEN_KEY = 'acm_access_token';
  const PURPOSE_VERSION = 'v1';
  const $ = (id) => document.getElementById(id);
  const statusEl = $('status');
  const loadingEl = $('loading');
  const modal = $('consentModal');

  function setStatus(message, type) {
    statusEl.textContent = message || '';
    statusEl.className = 'status' + (type ? ' ' + type : '');
  }
  function setLoading(on) { loadingEl.classList.toggle('hidden', !on); }
  function getToken() { return localStorage.getItem(TOKEN_KEY) || $('token').value.trim(); }
  function showModal(show) { modal.classList.toggle('hidden', !show); }

  const saved = localStorage.getItem(TOKEN_KEY);
  if (saved) $('token').value = saved;
  $('saveToken').onclick = () => {
    localStorage.setItem(TOKEN_KEY, $('token').value.trim());
    setStatus('Đã lưu token trong trình duyệt.', 'ok');
  };

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
})();
