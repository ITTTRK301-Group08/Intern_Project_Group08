(function () {
  const TOKEN_KEY = 'acm_access_token';
  const MAX_SIZE = 5 * 1024 * 1024;
  const $ = (id) => document.getElementById(id);
  const statusEl = $('status');
  const loadingEl = $('loading');

  function setStatus(message, type) { statusEl.textContent = message || ''; statusEl.className = 'status' + (type ? ' ' + type : ''); }
  function setLoading(on) { loadingEl.classList.toggle('hidden', !on); }
  function getToken() { return localStorage.getItem(TOKEN_KEY) || $('token').value.trim(); }

  const saved = localStorage.getItem(TOKEN_KEY);
  if (saved) $('token').value = saved;
  $('saveToken').onclick = () => { localStorage.setItem(TOKEN_KEY, $('token').value.trim()); setStatus('Đã lưu token trong trình duyệt.', 'ok'); };

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
      const cv = (body.data && body.data.cv) || {};
      $('resultCard').classList.remove('hidden');
      $('resName').textContent = cv.file_name || '';
      $('resSize').textContent = (cv.file_size || 0) + ' bytes';
      const text = cv.extracted_text || '';
      $('resExtract').textContent = text.trim() ? 'Thành công (đã trích xuất văn bản)' : 'Không trích xuất được văn bản có ý nghĩa';
      $('resText').value = text;
      setStatus(body.message || 'Upload CV thành công.', 'ok');
    } catch (err) {
      setStatus('Không thể kết nối máy chủ.', 'error');
    } finally { setLoading(false); }
  };
})();
