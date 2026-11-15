(function () {
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

  function setStatus(message, type) {
    statusEl.textContent = message || '';
    statusEl.className = 'status' + (type ? ' ' + type : '');
  }
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
    pendingPayload = {
      cv_id: cvRaw ? Number(cvRaw) : null,
      career_role_id: careerRaw ? Number(careerRaw) : null
    };
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
    const body = Object.assign({}, pendingPayload, {
      ai_consent: { accepted: true, purpose_version: PURPOSE_VERSION }
    });
    pendingPayload = null;
    setLoading(true);
    try {
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
})();
