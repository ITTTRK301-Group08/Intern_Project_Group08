(function () {
  const TOKEN_KEY = 'acm_access_token';
  const $ = (id) => document.getElementById(id);
  const statusEl = $('status');
  const loadingEl = $('loading');

  function setStatus(message, type) {
    statusEl.textContent = message || '';
    statusEl.className = 'status' + (type ? ' ' + type : '');
  }
  function setLoading(on) { loadingEl.classList.toggle('hidden', !on); }
  function getToken() { return localStorage.getItem(TOKEN_KEY) || $('token').value.trim(); }
  function authHeaders() {
    const token = getToken();
    return token ? { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' };
  }

  function strengthRow(value) {
    const row = document.createElement('div');
    row.className = 'item-row';
    row.innerHTML = '<input maxlength="100" placeholder="Điểm mạnh" /><button type="button" class="secondary small">Xóa</button>';
    row.querySelector('input').value = value || '';
    row.querySelector('button').onclick = () => row.remove();
    return row;
  }
  function skillRow(skill) {
    const row = document.createElement('div');
    row.className = 'item-row';
    let opts = '';
    for (let i = 0; i <= 5; i++) opts += '<option value="' + i + '"' + ((skill && Number(skill.level) === i) ? ' selected' : '') + '>' + i + '</option>';
    row.innerHTML = '<input maxlength="150" placeholder="Tên kỹ năng" /><select aria-label="Mức">' + opts + '</select><button type="button" class="secondary small">Xóa</button>';
    row.querySelector('input').value = (skill && skill.skill_name) || '';
    row.querySelector('button').onclick = () => row.remove();
    return row;
  }

  function renderProfile(data) {
    $('viewEmail').textContent = data.email || '-';
    $('full_name').value = data.full_name || '';
    $('major').value = data.major || '';
    $('university').value = data.university || '';
    $('career_goal').value = data.career_goal || '';
    $('bio').value = data.bio || '';
    const strengthsList = $('strengthsList');
    strengthsList.innerHTML = '';
    (data.strengths || []).forEach((s) => strengthsList.appendChild(strengthRow(s)));
    const skillsList = $('skillsList');
    skillsList.innerHTML = '';
    (data.self_assessed_skills || []).forEach((s) => skillsList.appendChild(skillRow(s)));
  }

  function collectPayload() {
    const strengths = Array.from($('strengthsList').querySelectorAll('input')).map((i) => i.value.trim()).filter(Boolean);
    const skills = Array.from($('skillsList').querySelectorAll('.item-row')).map((row) => {
      const name = row.querySelector('input').value.trim();
      const level = Number(row.querySelector('select').value);
      return name ? { skill_name: name, level: level } : null;
    }).filter(Boolean);
    return {
      full_name: $('full_name').value.trim(),
      major: $('major').value.trim() || null,
      university: $('university').value.trim() || null,
      strengths: strengths,
      self_assessed_skills: skills,
      career_goal: $('career_goal').value.trim() || null,
      bio: $('bio').value.trim() || null
    };
  }

  async function api(path, options) {
    setLoading(true);
    setStatus('', '');
    try {
      const res = await fetch(path, Object.assign({ headers: authHeaders() }, options || {}));
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = body.detail;
        const msg = Array.isArray(detail) ? detail.map((d) => d.msg || JSON.stringify(d)).join('; ') : (detail || body.message || 'Yêu cầu thất bại');
        throw new Error(msg);
      }
      return body;
    } finally { setLoading(false); }
  }

  async function loadProfile() {
    try {
      const body = await api('/api/v1/profile/me', { method: 'GET' });
      renderProfile(body.data || {});
      setStatus(body.message || 'Đã tải hồ sơ.', 'ok');
    } catch (e) {
      if (String(e.message).toLower().includes('not found')) {
        setStatus('Chưa có hồ sơ. Vui lòng nhập họ tên và lưu để tạo hồ sơ.', '');
      } else {
        setStatus(e.message, 'error');
      }
    }
  }

  $('saveToken').onclick = () => { localStorage.setItem(TOKEN_KEY, $('token').value.trim()); setStatus('Đã lưu token trong trình duyệt.', 'ok'); };
  $('loadProfile').onclick = loadProfile;
  $('addStrength').onclick = () => $('strengthsList').appendChild(strengthRow(''));
  $('addSkill').onclick = () => $('skillsList').appendChild(skillRow({ level: 0 }));
  $('profileForm').onsubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = collectPayload();
      const body = await api('/api/v1/profile/me', { method: 'PUT', body: JSON.stringify(payload) });
      renderProfile(body.data || {});
      setStatus(body.message || 'Cập nhật thành công.', 'ok');
    } catch (e2) { setStatus(e2.message, 'error'); }
  };

  const saved = localStorage.getItem(TOKEN_KEY);
  if (saved) $('token').value = saved;
})();
