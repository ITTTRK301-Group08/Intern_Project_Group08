(function () {
  'use strict';

  const TOKEN_KEY = 'acm_access_token';
  const PURPOSE_VERSION = 'v1';
  const POLL_INTERVAL_MS = 2500;
  const POLL_MAX_ATTEMPTS = 120;
  const $ = (id) => document.getElementById(id);

  let cvMap = {};
  let rolesAvailable = false;
  let submitting = false;
  let pendingPayload = null;
  let currentAnalysisId = null;
  let pollRunId = 0;

  const STATUS_LABELS = {
    pending: 'Đang chờ',
    processing: 'Đang xử lý',
    completed: 'Hoàn thành',
    failed: 'Thất bại'
  };

  const FAILURE_MESSAGES = {
    AI_TIMEOUT: 'Dịch vụ AI phản hồi quá thời gian chờ. Vui lòng thử lại sau.',
    AI_RATE_LIMITED: 'Dịch vụ AI đang giới hạn số lượng yêu cầu. Vui lòng thử lại sau.',
    AI_AUTHENTICATION_FAILED: 'Không thể xác thực với dịch vụ AI. Vui lòng liên hệ quản trị viên.',
    AI_INVALID_REQUEST: 'Yêu cầu gửi tới dịch vụ AI không hợp lệ. Vui lòng thử lại sau.',
    AI_UNAVAILABLE: 'Dịch vụ AI đang không khả dụng. Vui lòng thử lại sau.',
    AI_INVALID_RESPONSE: 'Dịch vụ AI trả về dữ liệu không hợp lệ. Vui lòng thử lại sau.',
    AI_UNKNOWN_ERROR: 'Đã xảy ra lỗi không xác định từ dịch vụ AI. Vui lòng thử lại sau.',
    ANALYSIS_INVALID_AI_RESULT: 'AI trả về kết quả không đầy đủ hoặc không khớp với kỹ năng của vị trí. Vui lòng thử lại sau.',
    ANALYSIS_INTERNAL_ERROR: 'Đã xảy ra lỗi trong quá trình phân tích. Vui lòng thử lại sau.',
    ANALYSIS_DATABASE_ERROR: 'Không thể lưu kết quả phân tích. Vui lòng thử lại sau.'
  };

  function setStatus(message, type) {
    const el = $('status');
    if (!el) return;
    el.textContent = message || '';
    el.className = 'status' + (type ? ' ' + type : '');
  }

  function setLoading(on) {
    const el = $('loading');
    if (el) el.classList.toggle('hidden', !on);
  }

  function getToken() {
    try { return localStorage.getItem(TOKEN_KEY) || ''; } catch (_err) { return ''; }
  }

  function showModal(show) {
    const modal = $('consentModal');
    if (modal) modal.classList.toggle('hidden', !show);
  }

  function redirectToLogin() {
    try { localStorage.removeItem(TOKEN_KEY); } catch (_err) { /* bỏ qua */ }
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.replace('/login?next=' + next);
  }

  function authHeaders(withJson) {
    const headers = { 'Authorization': 'Bearer ' + getToken() };
    if (withJson) headers['Content-Type'] = 'application/json';
    return headers;
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  // Đọc body dạng text trước để không vỡ khi backend trả về nội dung không phải JSON.
  async function requestJson(path, options) {
    const res = await fetch(path, options);
    const raw = await res.text();
    let data = null;
    if (raw) {
      try { data = JSON.parse(raw); } catch (_err) { data = null; }
    }
    return { res: res, data: data };
  }

  // Đọc mã lỗi nghiệp vụ từ envelope lỗi của backend (mã nằm trong detail.data.code).
  function readErrorCode(body) {
    if (body && body.detail && body.detail.data && typeof body.detail.data.code === 'string') {
      return body.detail.data.code;
    }
    if (body && body.data && typeof body.data.code === 'string') {
      return body.data.code;
    }
    return '';
  }

  function describeValidationErrors(detail) {
    const fields = detail
      .map((item) => (item && Array.isArray(item.loc) ? String(item.loc[item.loc.length - 1]) : ''))
      .filter(Boolean);
    if (fields.indexOf('ai_consent') >= 0) {
      return 'Vui lòng xác nhận đồng ý sử dụng dữ liệu cho AI.';
    }
    if (fields.indexOf('career_role_id') >= 0) {
      return 'Vui lòng chọn vị trí nghề nghiệp mục tiêu hợp lệ.';
    }
    if (fields.indexOf('cv_id') >= 0) {
      return 'CV đã chọn không hợp lệ. Vui lòng kiểm tra lại.';
    }
    return 'Thông tin gửi lên không hợp lệ. Vui lòng kiểm tra lại.';
  }

  function describeHttpError(status, body) {
    const code = readErrorCode(body);

    if (code === 'AI_CONSENT_REQUIRED') {
      return 'Vui lòng xác nhận đồng ý sử dụng dữ liệu cho AI.';
    }
    if (code === 'AI_CONSENT_VERSION_UNSUPPORTED') {
      return 'Phiên bản mục đích đồng ý không hợp lệ hoặc không được hỗ trợ. Vui lòng tải lại trang và thử lại.';
    }
    if (code === 'CV_NOT_FOUND') {
      return 'Không tìm thấy CV hoặc CV không còn khả dụng. Vui lòng chọn CV khác.';
    }
    if (code === 'CV_FORBIDDEN') {
      return 'Bạn không có quyền sử dụng CV này.';
    }
    if (code === 'ANALYSIS_CAREER_ROLE_NOT_FOUND') {
      return 'Vị trí nghề nghiệp không tồn tại hoặc đã bị xóa. Vui lòng chọn vị trí khác.';
    }
    if (code === 'ANALYSIS_CAREER_ROLE_INACTIVE') {
      return 'Vị trí nghề nghiệp đã ngừng hoạt động. Vui lòng chọn vị trí khác.';
    }
    if (code === 'ANALYSIS_ROLE_SKILLS_REQUIRED') {
      return 'Vị trí nghề nghiệp chưa có kỹ năng yêu cầu nên chưa thể phân tích. Vui lòng chọn vị trí khác.';
    }
    if (code === 'ANALYSIS_NOT_FOUND') {
      return 'Không tìm thấy báo cáo phân tích.';
    }
    if (code === 'ANALYSIS_DATABASE_ERROR') {
      return 'Không thể lưu yêu cầu phân tích. Vui lòng thử lại sau.';
    }

    if (status === 422 && body && Array.isArray(body.detail)) {
      return describeValidationErrors(body.detail);
    }
    if (status === 401) {
      return 'Phiên đăng nhập không hợp lệ hoặc đã hết hạn. Vui lòng đăng nhập lại.';
    }
    if (status === 429) {
      return 'Bạn đã gửi quá nhiều yêu cầu. Vui lòng chờ một lúc rồi thử lại.';
    }
    if (status >= 500) {
      return 'Đã xảy ra lỗi khi xử lý yêu cầu. Vui lòng thử lại sau.';
    }

    const detail = body && body.detail;
    if (detail && typeof detail.message === 'string' && detail.message) {
      return detail.message;
    }
    if (typeof detail === 'string' && detail) {
      return detail;
    }
    if (body && typeof body.message === 'string' && body.message) {
      return body.message;
    }
    return 'Yêu cầu thất bại. Vui lòng thử lại.';
  }

  function failureText(reason) {
    if (!reason) {
      return 'Không thể hoàn tất phân tích vì lỗi không xác định. Vui lòng thử lại sau.';
    }
    return FAILURE_MESSAGES[reason] || 'Không thể hoàn tất phân tích. Vui lòng thử lại sau.';
  }

  // Backend lưu thời gian theo UTC nhưng có thể trả chuỗi không kèm hậu tố múi giờ.
  function parseBackendDate(value) {
    if (typeof value !== 'string') return new Date(value);
    const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value);
    return new Date(hasTimezone ? value : value + 'Z');
  }

  function formatDateTime(value) {
    if (!value) return '-';
    const date = parseBackendDate(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleString('vi-VN', { dateStyle: 'medium', timeStyle: 'short' });
  }

  function formatDateOnly(value) {
    if (!value) return '-';
    const date = typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)
      ? new Date(value + 'T00:00:00')
      : parseBackendDate(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleDateString('vi-VN', { dateStyle: 'medium' });
  }

  function formatNumber(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return '--';
    return Number.isInteger(number) ? String(number) : number.toFixed(1);
  }

  function statusLabel(status) {
    return STATUS_LABELS[status] || status || '-';
  }

  function roleText(analysis) {
    const role = analysis && analysis.career_role;
    if (!role) return 'Vị trí không còn khả dụng';
    return role.name + (role.level ? ' (' + role.level + ')' : '');
  }

  function updateStatusBadge(status) {
    const badge = $('panelStatus');
    if (!badge) return;
    badge.className = 'badge ' + (status || '');
    badge.textContent = statusLabel(status);
  }

  function refreshStartState() {
    const button = $('startAnalysisBtn');
    if (button) button.disabled = submitting || !rolesAvailable;
  }
<<<<<<< HEAD
  function setLoading(on) { loadingEl.classList.toggle('hidden', !on); }
  function getToken() { return localStorage.getItem(TOKEN_KEY) || ''; }
  function showModal(show) { modal.classList.toggle('hidden', !show); }
  function wait(milliseconds) {
    return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
  }

  function renderAnalysisResult(result) {
    $('resultSummary').textContent = result.summary || (
      result.status === 'failed'
        ? 'Phân tích không hoàn tất. Hãy thử lại sau.'
        : 'Đang chờ hệ thống xử lý yêu cầu.'
    );
    const hasScore = Number.isInteger(result.readiness_score);
    $('readinessPanel').classList.toggle('hidden', !hasScore);
    if (hasScore) {
      $('readinessValue').textContent = result.readiness_score + '/100';
      $('readinessMeter').value = result.readiness_score;
    }

    const rows = $('skillGapRows');
    rows.replaceChildren();
    (result.skill_gaps || []).forEach((gap) => {
      const row = document.createElement('tr');
      const values = [
        gap.skill_name,
        gap.current_level + '/5',
        gap.target_level + '/5',
        gap.gap === 0 ? 'Đạt' : gap.gap + ' mức',
        String(gap.weight),
        gap.is_required ? 'Bắt buộc' : 'Khuyến khích'
      ];
      values.forEach((value) => {
        const cell = document.createElement('td');
        cell.textContent = value;
        row.appendChild(cell);
      });
      rows.appendChild(row);
    });
  }

  async function pollAnalysis(analysisId, token) {
    for (let attempt = 0; attempt < 60; attempt += 1) {
      const response = await fetch('/api/v1/analyses/' + encodeURIComponent(analysisId), {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = body.detail;
        throw new Error(
          (detail && (detail.message || detail)) ||
          body.message ||
          'Không thể kiểm tra trạng thái phân tích.'
        );
      }

      const result = body.data;
      renderAnalysisResult(result);
      if (result.status === 'completed') {
        setStatus(result.summary || 'Phân tích đã hoàn tất.', 'ok');
        return;
      }
      if (result.status === 'failed') {
        setStatus(result.summary || 'Phân tích không hoàn tất. Hãy thử lại sau.', 'error');
        return;
      }

      setStatus(
        result.status === 'running'
          ? 'Đang đối chiếu dữ liệu và tính mức sẵn sàng...'
          : 'Yêu cầu đã được tiếp nhận, đang chờ xử lý...'
      );
      await wait(1000);
    }

    setStatus(
      'Yêu cầu vẫn đang xử lý. Tải lại trang kết quả sau ít phút để kiểm tra.',
      'error'
    );
  }
=======
>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1

  function updateScannedWarning() {
    const warnBox = $('scannedCvWarning');
    const select = $('cvSelect');
    if (!warnBox || !select) return;
    const cv = select.value ? cvMap[String(select.value)] : null;
    warnBox.classList.toggle('hidden', !(cv && cv.has_text === false));
  }

  function showPanel() {
    const panel = $('analysisPanel');
    if (panel) panel.classList.remove('hidden');
  }

  function setPanelSubtitle(text) {
    const el = $('panelSubtitle');
    if (el) el.textContent = text || '';
  }

  function renderProcessing(analysis) {
    showPanel();
    updateStatusBadge(analysis && analysis.status ? analysis.status : 'processing');
    const completedBox = $('completedBox');
    const failedBox = $('failedBox');
    const processingBox = $('processingBox');
    if (completedBox) completedBox.classList.add('hidden');
    if (failedBox) failedBox.classList.add('hidden');
    if (processingBox) processingBox.classList.remove('hidden');

    if (analysis && analysis.career_role) {
      const parts = [roleText(analysis)];
      if (analysis.created_at) parts.push('Tạo lúc ' + formatDateTime(analysis.created_at));
      setPanelSubtitle(parts.join(' · '));
    } else if (analysis && analysis.id != null) {
      setPanelSubtitle('Báo cáo #' + analysis.id);
    }
    const text = $('processingText');
    if (text) {
      text.textContent = 'Quá trình này có thể mất vài chục giây. Trang sẽ tự cập nhật khi có kết quả (mã báo cáo #'
        + (analysis && analysis.id != null ? analysis.id : currentAnalysisId) + ').';
    }
  }

  function renderFailed(analysis) {
    showPanel();
    updateStatusBadge('failed');
    const completedBox = $('completedBox');
    const processingBox = $('processingBox');
    const failedBox = $('failedBox');
    if (completedBox) completedBox.classList.add('hidden');
    if (processingBox) processingBox.classList.add('hidden');
    if (failedBox) failedBox.classList.remove('hidden');

    if (analysis && (analysis.career_role || analysis.created_at)) {
      const parts = [roleText(analysis)];
      if (analysis.created_at) parts.push('Tạo lúc ' + formatDateTime(analysis.created_at));
      setPanelSubtitle(parts.join(' · '));
    }
    const text = $('failedText');
    if (text) text.textContent = failureText(analysis && analysis.failure_reason);
  }

  function renderSkillList(gaps, container) {
    if (!container) return;
    container.replaceChildren();
    if (!gaps.length) {
      const empty = document.createElement('p');
      empty.className = 'muted';
      empty.textContent = 'Báo cáo không có dữ liệu kỹ năng.';
      container.append(empty);
      return;
    }

    const sorted = gaps.slice().sort((a, b) => {
      const gapDiff = Number(b.gap_score || 0) - Number(a.gap_score || 0);
      if (gapDiff !== 0) return gapDiff;
      return Number(b.required_level || 0) - Number(a.required_level || 0);
    });

    sorted.forEach((gap) => {
      const card = document.createElement('article');
      card.className = 'skill-card';

      const head = document.createElement('div');
      head.className = 'skill-card-head';
      const name = document.createElement('strong');
      name.textContent = gap.skill && gap.skill.name ? gap.skill.name : 'Kỹ năng #' + gap.skill_id;
      const badge = document.createElement('span');
      const gapScore = Number(gap.gap_score || 0);
      if (gapScore > 0) {
        badge.className = 'badge processing';
        badge.textContent = 'Thiếu ' + formatNumber(gapScore) + ' mức';
      } else {
        badge.className = 'badge completed';
        badge.textContent = 'Đạt yêu cầu';
      }
      head.append(name, badge);

      const currentRow = buildLevelRow('Hiện tại', gap.current_level, 'current');
      const requiredRow = buildLevelRow('Yêu cầu', gap.required_level, 'required');

      const evidence = document.createElement('p');
      evidence.className = 'evidence' + (gap.has_evidence ? '' : ' missing');
      evidence.textContent = gap.has_evidence && gap.evidence
        ? 'Bằng chứng: ' + gap.evidence
        : 'Chưa tìm thấy bằng chứng trong CV/hồ sơ nên kỹ năng được tính ở mức 0.';

      card.append(head, currentRow, requiredRow, evidence);

      if (gap.recommendation) {
        const recommendation = document.createElement('p');
        recommendation.className = 'recommendation';
        recommendation.textContent = 'Gợi ý cải thiện: ' + gap.recommendation;
        card.append(recommendation);
      }

      container.append(card);
    });
  }

  function buildLevelRow(labelText, value, kind) {
    const row = document.createElement('div');
    row.className = 'level-row';
    const label = document.createElement('span');
    label.textContent = labelText + ' ' + formatNumber(value) + '/5';
    const bar = document.createElement('div');
    bar.className = 'bar ' + kind;
    const fill = document.createElement('span');
    const ratio = Math.max(0, Math.min(5, Number(value) || 0)) / 5;
    fill.style.width = (ratio * 100).toFixed(0) + '%';
    bar.append(fill);
    row.append(label, bar, document.createElement('span'));
    return row;
  }

  function polarPoint(cx, cy, radius, index, count) {
    const angle = -Math.PI / 2 + (index * 2 * Math.PI) / count;
    return {
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
      cos: Math.cos(angle),
      sin: Math.sin(angle)
    };
  }

  function createSvgElement(tag, attributes, text) {
    const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.keys(attributes || {}).forEach((key) => node.setAttribute(key, attributes[key]));
    if (text != null) node.textContent = text;
    return node;
  }

  function renderRadar(gaps, container) {
    if (!container) return;
    container.replaceChildren();
    if (!gaps.length) {
      const empty = document.createElement('p');
      empty.className = 'muted';
      empty.textContent = 'Chưa có dữ liệu kỹ năng để vẽ biểu đồ.';
      container.append(empty);
      return;
    }

    const skills = gaps.map((gap) => ({
      name: gap.skill && gap.skill.name ? gap.skill.name : 'Kỹ năng #' + gap.skill_id,
      current: Math.max(0, Math.min(5, Number(gap.current_level) || 0)),
      required: Math.max(0, Math.min(5, Number(gap.required_level) || 0))
    }));

    // Radar cần tối thiểu 3 trục; với ít kỹ năng hơn, hiển thị thanh so sánh dễ đọc hơn.
    if (skills.length < 3) {
      container.append(renderLevelBars(skills));
      return;
    }

    const width = 460;
    const height = 400;
    const cx = 230;
    const cy = 200;
    const radius = 140;
    const svg = createSvgElement('svg', {
      viewBox: '0 0 ' + width + ' ' + height,
      role: 'img',
      'aria-label': 'Biểu đồ radar so sánh mức kỹ năng hiện tại và mức yêu cầu'
    });

    // Lưới 5 mức và trục cho từng kỹ năng.
    for (let level = 1; level <= 5; level += 1) {
      const ringRadius = (radius * level) / 5;
      const points = skills.map((_skill, index) => {
        const point = polarPoint(cx, cy, ringRadius, index, skills.length);
        return point.x.toFixed(1) + ',' + point.y.toFixed(1);
      }).join(' ');
      svg.append(createSvgElement('polygon', {
        points: points,
        fill: 'none',
        stroke: level === 5 ? '#c8d9d2' : '#e2ece7',
        'stroke-width': level === 5 ? 1.6 : 1
      }));
    }

    skills.forEach((_skill, index) => {
      const point = polarPoint(cx, cy, radius, index, skills.length);
      svg.append(createSvgElement('line', {
        x1: cx,
        y1: cy,
        x2: point.x.toFixed(1),
        y2: point.y.toFixed(1),
        stroke: '#e2ece7',
        'stroke-width': 1
      }));
    });

    function polygonFor(key, fill, stroke) {
      const points = skills.map((skill, index) => {
        const point = polarPoint(cx, cy, (radius * skill[key]) / 5, index, skills.length);
        return point.x.toFixed(1) + ',' + point.y.toFixed(1);
      }).join(' ');
      return createSvgElement('polygon', {
        points: points,
        fill: fill,
        stroke: stroke,
        'stroke-width': 2,
        'stroke-linejoin': 'round'
      });
    }

    svg.append(polygonFor('required', 'rgba(215, 237, 133, .45)', '#9cbb3c'));
    svg.append(polygonFor('current', 'rgba(143, 211, 200, .45)', '#087c72'));

    skills.forEach((skill, index) => {
      const point = polarPoint(cx, cy, radius + 26, index, skills.length);
      let anchor = 'middle';
      if (point.cos > 0.25) anchor = 'start';
      if (point.cos < -0.25) anchor = 'end';
      const label = skill.name.length > 20 ? skill.name.slice(0, 17) + '…' : skill.name;
      const text = createSvgElement('text', {
        x: point.x.toFixed(1),
        y: point.y.toFixed(1),
        'text-anchor': anchor,
        'dominant-baseline': 'middle',
        'font-size': '12',
        fill: '#153247'
      }, label);
      const title = createSvgElement('title', {}, skill.name + ': hiện tại ' + skill.current + '/5, yêu cầu ' + skill.required + '/5');
      text.append(title);
      svg.append(text);
    });

    container.append(svg);
  }

  function renderLevelBars(skills) {
    const wrapper = document.createElement('div');
    const note = document.createElement('p');
    note.className = 'muted small';
    note.textContent = 'Cần ít nhất 3 kỹ năng để vẽ radar. Dưới đây là so sánh mức hiện tại và mức yêu cầu.';
    wrapper.append(note);

    skills.forEach((skill) => {
      const card = document.createElement('article');
      card.className = 'skill-card';
      const head = document.createElement('div');
      head.className = 'skill-card-head';
      const name = document.createElement('strong');
      name.textContent = skill.name;
      head.append(name);
      card.append(head);
      card.append(buildLevelRow('Hiện tại', skill.current, 'current'));
      card.append(buildLevelRow('Yêu cầu', skill.required, 'required'));
      wrapper.append(card);
    });
    return wrapper;
  }

  function renderCompleted(analysis) {
    showPanel();
    updateStatusBadge('completed');
    const processingBox = $('processingBox');
    const failedBox = $('failedBox');
    const completedBox = $('completedBox');
    if (processingBox) processingBox.classList.add('hidden');
    if (failedBox) failedBox.classList.add('hidden');
    if (completedBox) completedBox.classList.remove('hidden');

    const parts = [roleText(analysis)];
    if (analysis.completed_at) parts.push('Hoàn thành lúc ' + formatDateTime(analysis.completed_at));
    setPanelSubtitle(parts.join(' · '));

    const readiness = Number(analysis.readiness_score);
    const percentage = Number.isFinite(readiness) ? Math.max(0, Math.min(100, readiness)) : 0;
    const readinessValue = $('readinessValue');
    if (readinessValue) {
      readinessValue.textContent = Number.isFinite(readiness) ? formatNumber(readiness) : '--';
    }
    const ring = $('readinessRing');
    if (ring) {
      ring.style.background = 'conic-gradient(var(--primary) ' + percentage + '%, #e6efe9 ' + percentage + '% 100%)';
    }

    const roleEl = $('analysisRole');
    if (roleEl) roleEl.textContent = roleText(analysis);
    const sourceEl = $('analysisSource');
    if (sourceEl) sourceEl.textContent = analysis.market_source || '-';
    const benchmarkEl = $('analysisBenchmark');
    if (benchmarkEl) benchmarkEl.textContent = formatDateOnly(analysis.benchmark_date);
    const summaryEl = $('analysisSummary');
    if (summaryEl) summaryEl.textContent = analysis.summary || 'AI không cung cấp tóm tắt cho báo cáo này.';

    renderRadar(analysis.skill_gaps || [], $('radarContainer'));
    renderSkillList(analysis.skill_gaps || [], $('skillList'));
  }

  async function loadAnalysisDetail(analysisId, scroll) {
    if (!analysisId) return;
    // Hủy vòng polling cũ trước khi mở báo cáo khác.
    pollRunId += 1;
    currentAnalysisId = analysisId;
    setLoading(true);
    try {
      const result = await requestJson('/api/v1/analyses/' + analysisId, {
        headers: authHeaders(false)
      });
      const res = result.res;
      const data = result.data;

      if (res.status === 401) { redirectToLogin(); return; }
      if (!res.ok) {
        setStatus(describeHttpError(res.status, data), 'error');
        return;
      }

      const analysis = data && data.data;
      if (!analysis) {
        setStatus('Phản hồi từ máy chủ không hợp lệ. Vui lòng thử lại.', 'error');
        return;
      }

      if (analysis.status === 'completed') {
        renderCompleted(analysis);
      } else if (analysis.status === 'failed') {
        renderFailed(analysis);
      } else {
        renderProcessing(analysis);
        void pollStatus(analysisId);
      }

      if (scroll) {
        const panel = $('analysisPanel');
        if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    } catch (_err) {
      setStatus('Không thể kết nối máy chủ. Vui lòng kiểm tra kết nối rồi thử lại.', 'error');
    } finally {
      setLoading(false);
    }
  }

  async function pollStatus(analysisId) {
    const runId = ++pollRunId;
    let attempts = 0;

    while (runId === pollRunId && attempts < POLL_MAX_ATTEMPTS) {
      await sleep(POLL_INTERVAL_MS);
      if (runId !== pollRunId) return;
      attempts += 1;

      try {
        const result = await requestJson('/api/v1/analyses/' + analysisId + '/status', {
          headers: authHeaders(false)
        });
        if (runId !== pollRunId) return;

        if (result.res.status === 401) { redirectToLogin(); return; }
        if (!result.res.ok) {
          if (result.res.status === 404) {
            setStatus('Không tìm thấy báo cáo phân tích.', 'error');
            return;
          }
          continue;
        }

        const statusData = result.data && result.data.data;
        if (!statusData) continue;
        updateStatusBadge(statusData.status);

        if (statusData.status === 'completed') {
          await loadAnalysisDetail(analysisId, false);
          loadHistory(true);
          return;
        }
        if (statusData.status === 'failed') {
          renderFailed(statusData);
          loadHistory(true);
          return;
        }

        renderProcessing(statusData);
      } catch (_err) {
        // Lỗi mạng tạm thời: tiếp tục thử cho tới giới hạn.
      }
    }

    if (runId === pollRunId) {
      setStatus('Báo cáo vẫn đang xử lý lâu hơn dự kiến. Vui lòng xem lại lịch sử sau hoặc tải lại trang.', 'error');
    }
  }

  function historyStatusBadge(status) {
    const badge = document.createElement('span');
    badge.className = 'badge ' + (status || '');
    badge.textContent = statusLabel(status);
    return badge;
  }

  function renderHistory(analyses) {
    const list = $('historyList');
    const empty = $('historyEmpty');
    if (!list) return;
    list.replaceChildren();
    if (empty) empty.classList.add('hidden');

    analyses.forEach((analysis) => {
      const item = document.createElement('article');
      item.className = 'history-item';

      const main = document.createElement('div');
      const title = document.createElement('div');
      title.className = 'history-title';
      title.textContent = roleText(analysis);
      const meta = document.createElement('div');
      meta.className = 'history-meta';
      const metaParts = ['#' + analysis.id, formatDateTime(analysis.created_at)];
      if (analysis.readiness_score != null) {
        metaParts.push('Sẵn sàng ' + formatNumber(analysis.readiness_score) + '%');
      }
      meta.textContent = metaParts.join(' · ');
      main.append(title, meta);

      const side = document.createElement('div');
      side.className = 'history-side';
      side.append(historyStatusBadge(analysis.status));

      if (analysis.readiness_score != null && analysis.status === 'completed') {
        const score = document.createElement('span');
        score.className = 'history-score';
        score.textContent = formatNumber(analysis.readiness_score) + '%';
        side.append(score);
      }

      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'secondary small';
      button.textContent = analysis.status === 'processing' || analysis.status === 'pending'
        ? 'Theo dõi'
        : 'Xem chi tiết';
      button.addEventListener('click', () => {
        loadAnalysisDetail(analysis.id, true);
      });
      side.append(button);

      item.append(main, side);
      list.append(item);
    });
  }

  function showHistoryMessage(message) {
    const list = $('historyList');
    const empty = $('historyEmpty');
    if (list) list.replaceChildren();
    if (empty) {
      empty.textContent = message;
      empty.classList.remove('hidden');
    }
  }

  async function loadHistory(silent) {
    const loadingEl = $('historyLoading');
    if (!silent && loadingEl) loadingEl.classList.remove('hidden');
    try {
      const result = await requestJson('/api/v1/analyses?limit=20', {
        headers: authHeaders(false)
      });
      if (result.res.status === 401) { redirectToLogin(); return; }
      if (!result.res.ok) {
        if (!silent) showHistoryMessage('Không tải được lịch sử phân tích. Vui lòng tải lại trang hoặc thử lại sau.');
        return;
      }
      const analyses = (result.data && result.data.data && result.data.data.analyses) || [];
      if (!analyses.length) {
        showHistoryMessage('Bạn chưa có báo cáo phân tích nào. Hãy tạo báo cáo đầu tiên ở phía trên.');
        return;
      }
      renderHistory(analyses);
    } catch (_err) {
      if (!silent) showHistoryMessage('Không thể kết nối máy chủ để tải lịch sử. Vui lòng kiểm tra kết nối rồi thử lại.');
    } finally {
      if (loadingEl) loadingEl.classList.add('hidden');
    }
  }

  async function loadCareerRoles() {
    const roleSelect = $('roleSelect');
    if (!roleSelect) return;
    try {
      const result = await requestJson('/api/v1/careers');
      if (!result.res.ok) {
        setStatus('Không tải được danh sách vị trí nghề nghiệp. Vui lòng tải lại trang hoặc thử lại sau.', 'error');
        return;
      }
      const roles = Array.isArray(result.data && result.data.data) ? result.data.data : [];
      const available = roles.filter((role) => (
        role
        && role.is_active !== false
        && Array.isArray(role.required_skills)
        && role.required_skills.length > 0
      ));

      roleSelect.replaceChildren();
      const def = document.createElement('option');
      def.value = '';
      def.textContent = available.length
        ? '-- Chọn vị trí nghề nghiệp --'
        : '-- Chưa có vị trí nghề nghiệp khả dụng --';
      roleSelect.appendChild(def);

      available.forEach((role) => {
        const opt = document.createElement('option');
        opt.value = String(role.id);
        opt.textContent = role.name + ' (' + (role.level || 'Junior') + ')';
        roleSelect.appendChild(opt);
      });

      rolesAvailable = available.length > 0;
      refreshStartState();

      if (!rolesAvailable) {
        setStatus('Hiện chưa có vị trí nghề nghiệp nào đang hoạt động và đủ dữ liệu kỹ năng để phân tích. Vui lòng quay lại sau.', 'error');
        return;
      }

      const params = new URLSearchParams(window.location.search);
      const preselect = params.get('career_role_id');
      if (preselect && available.some((role) => String(role.id) === preselect)) {
        roleSelect.value = preselect;
      }
    } catch (_err) {
      rolesAvailable = false;
      refreshStartState();
      setStatus('Không thể kết nối máy chủ để tải danh sách vị trí nghề nghiệp. Vui lòng kiểm tra kết nối rồi tải lại trang.', 'error');
    }
  }

  async function loadUserCvs() {
    const cvSelect = $('cvSelect');
    if (!cvSelect) return;
    const token = getToken();
    if (!token) { redirectToLogin(); return; }

    try {
      const result = await requestJson('/api/v1/cvs', { headers: authHeaders(false) });
      if (result.res.status === 401) { redirectToLogin(); return; }
      if (!result.res.ok) return;

      const cvs = (result.data && result.data.data && result.data.data.cvs) || [];
      cvMap = {};
      cvSelect.replaceChildren();
      const def = document.createElement('option');
      def.value = '';
      def.textContent = cvs.length
        ? '-- Phân tích từ dữ liệu hồ sơ khai báo --'
        : '-- Chưa có CV nào, phân tích từ dữ liệu hồ sơ khai báo --';
      cvSelect.appendChild(def);

      cvs.forEach((cv) => {
        cvMap[String(cv.id)] = cv;
        const opt = document.createElement('option');
        opt.value = String(cv.id);
        opt.textContent = '#' + cv.id + ' - ' + cv.file_name
          + (cv.has_text === false ? ' (⚠️ Không trích xuất được văn bản)' : '');
        cvSelect.appendChild(opt);
      });

      const params = new URLSearchParams(window.location.search);
      if (params.get('source') === 'profile') {
        cvSelect.value = '';
      }
      updateScannedWarning();
    } catch (_err) {
      // Danh sách CV chỉ là tiện ích; người dùng vẫn có thể phân tích từ hồ sơ.
    }
  }

  function bindEvents() {
    const form = $('analysisForm');
    if (form) {
      form.addEventListener('submit', (event) => {
        event.preventDefault();
        if (submitting) {
          setStatus('Đang xử lý yêu cầu trước đó. Vui lòng chờ trong giây lát.', 'error');
          return;
        }
        const roleSelect = $('roleSelect');
        const cvSelect = $('cvSelect');
        if (!roleSelect || !roleSelect.value) {
          setStatus('Vui lòng chọn vị trí nghề nghiệp mục tiêu trước khi phân tích.', 'error');
          if (roleSelect) roleSelect.focus();
          return;
        }
        if (!getToken()) { redirectToLogin(); return; }

<<<<<<< HEAD
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
  const existingAnalysisId = params.get('analysis_id');
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
    if (!token) { window.location.replace('/login'); return; }
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
    setStatus('Bạn đã từ chối. Hệ thống không xử lý dữ liệu CV hoặc hồ sơ.', '');
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
      if (!res.ok) {
        const msg = (data.detail && (data.detail.message || data.detail)) || data.message || 'Yêu cầu thất bại.';
        setStatus(typeof msg === 'string' ? msg : JSON.stringify(msg), 'error');
      } else if (res.status === 202 && data.data && data.data.id) {
        const resultUrl = new URL(window.location.href);
        resultUrl.searchParams.set('analysis_id', data.data.id);
        window.history.replaceState({}, '', resultUrl);
        setStatus(data.message || 'Đã tiếp nhận yêu cầu phân tích.', 'ok');
        await pollAnalysis(data.data.id, token);
      } else {
        setStatus(data.message || 'Yêu cầu đã được xử lý.', 'ok');
      }
    } catch (err) {
      setStatus('Không thể kết nối máy chủ.', 'error');
    } finally { setLoading(false); }
  };
=======
        pendingPayload = {
          cv_id: cvSelect && cvSelect.value ? Number(cvSelect.value) : null,
          career_role_id: Number(roleSelect.value)
        };
        setStatus('', '');
        showModal(true);
      });
    }
>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1

    const cvSelect = $('cvSelect');
    if (cvSelect) {
      cvSelect.addEventListener('change', () => {
        updateScannedWarning();
        setStatus('', '');
      });
    }

<<<<<<< HEAD
  loadCareerRoles();
  loadUserCvs();
  if (/^[1-9]\d*$/.test(existingAnalysisId || '') && getToken()) {
    $('resultCard').classList.remove('hidden');
    pollAnalysis(existingAnalysisId, getToken()).catch((err) => {
      setStatus(err.message || 'Không thể kiểm tra kết quả phân tích.', 'error');
    });
=======
    const switchBtn = $('switchToProfileBtn');
    if (switchBtn) {
      switchBtn.addEventListener('click', () => {
        const select = $('cvSelect');
        if (select) select.value = '';
        updateScannedWarning();
        setStatus('Đã chuyển sang chế độ phân tích từ dữ liệu hồ sơ khai báo (không dùng CV ảnh quét).', 'ok');
      });
    }

    const rejectBtn = $('consentReject');
    if (rejectBtn) {
      rejectBtn.addEventListener('click', () => {
        pendingPayload = null;
        showModal(false);
        setStatus('Bạn đã từ chối. Quy trình dừng lại và không gửi dữ liệu CV/hồ sơ đến AI.', '');
      });
    }

    const acceptBtn = $('consentAccept');
    if (acceptBtn) {
      acceptBtn.addEventListener('click', async () => {
        if (submitting) return;
        if (!pendingPayload) {
          showModal(false);
          setStatus('Không có yêu cầu phân tích nào đang chờ xác nhận. Vui lòng bấm "Bắt đầu phân tích" để tiếp tục.', 'error');
          return;
        }
        if (!getToken()) {
          showModal(false);
          redirectToLogin();
          return;
        }

        const payloadSnapshot = pendingPayload;
        const body = {
          cv_id: payloadSnapshot.cv_id,
          career_role_id: payloadSnapshot.career_role_id,
          ai_consent: { accepted: true, purpose_version: PURPOSE_VERSION }
        };
        // Chỉ xóa payload sau khi đã tạo body, tránh dùng lại consent cho lần gửi sau.
        pendingPayload = null;
        submitting = true;
        refreshStartState();
        acceptBtn.disabled = true;
        showModal(false);
        setLoading(true);
        setStatus('Đang gửi yêu cầu phân tích tới máy chủ...', '');

        try {
          const result = await requestJson('/api/v1/analyses', {
            method: 'POST',
            headers: authHeaders(true),
            body: JSON.stringify(body)
          });

          if (result.res.status === 401) { redirectToLogin(); return; }
          if (!result.res.ok) {
            setStatus(describeHttpError(result.res.status, result.data), 'error');
            if (readErrorCode(result.data) === 'AI_CONSENT_REQUIRED') {
              pendingPayload = payloadSnapshot;
              showModal(true);
            }
            return;
          }

          const created = result.data && result.data.data;
          if (!created || created.id == null) {
            setStatus('Phản hồi từ máy chủ không hợp lệ. Vui lòng thử lại.', 'error');
            return;
          }

          setStatus((result.data && result.data.message) || 'Đã tạo yêu cầu phân tích. Hệ thống đang xử lý.', 'ok');
          currentAnalysisId = created.id;
          renderProcessing(created);
          const panel = $('analysisPanel');
          if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
          loadHistory(true);
          void pollStatus(created.id);
        } catch (_err) {
          setStatus('Không thể kết nối máy chủ. Vui lòng kiểm tra kết nối rồi thử lại.', 'error');
        } finally {
          submitting = false;
          acceptBtn.disabled = false;
          refreshStartState();
          setLoading(false);
        }
      });
    }

    const modal = $('consentModal');
    if (modal) {
      // Chỉ đóng modal bằng hành động rõ ràng (không tự đồng ý khi bấm ra ngoài).
      modal.addEventListener('click', (event) => {
        if (event.target === modal) event.stopPropagation();
      });
    }
  }

  function init() {
    bindEvents();
    const params = new URLSearchParams(window.location.search);
    if (params.get('source') === 'profile') {
      setStatus('Chế độ phân tích từ dữ liệu hồ sơ khai báo đã được chọn (bỏ trống CV).', 'ok');
    }
    loadCareerRoles();
    loadUserCvs();
    loadHistory();

    const preloadId = params.get('analysis_id');
    if (preloadId) loadAnalysisDetail(Number(preloadId), true);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1
  }
})();
