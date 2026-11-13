(function () {
  'use strict';

  const TOKEN_KEY = 'acm_access_token';
  const PURPOSE_VERSION = 'v1';
  const $ = (id) => document.getElementById(id);

  let rolesAvailable = false;
  let submitting = false;
  let busy = false;
  let pendingRoleId = null;
  let currentSession = null;
  let currentIndex = 0;

  const STATUS_LABELS = {
    in_progress: 'Đang thực hiện',
    completed: 'Hoàn thành',
    abandoned: 'Đã bỏ dở'
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

  async function requestJson(path, options) {
    const res = await fetch(path, options);
    const raw = await res.text();
    let data = null;
    if (raw) {
      try { data = JSON.parse(raw); } catch (_err) { data = null; }
    }
    return { res: res, data: data };
  }

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
    if (fields.indexOf('career_role_id') >= 0) {
      return 'Vui lòng chọn vị trí nghề nghiệp hợp lệ.';
    }
    if (fields.indexOf('ai_consent') >= 0) {
      return 'Vui lòng xác nhận đồng ý sử dụng dữ liệu cho AI.';
    }
    if (fields.indexOf('answer_text') >= 0) {
      return 'Câu trả lời không được để trống hoặc quá dài.';
    }
    if (fields.indexOf('question_id') >= 0) {
      return 'Câu hỏi gửi lên không hợp lệ. Vui lòng tải lại phiên.';
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
    if (code === 'INTERVIEW_CAREER_ROLE_NOT_FOUND') {
      return 'Vị trí nghề nghiệp không tồn tại hoặc đã bị xóa. Vui lòng chọn vị trí khác.';
    }
    if (code === 'INTERVIEW_CAREER_ROLE_INACTIVE') {
      return 'Vị trí nghề nghiệp đã ngừng hoạt động. Vui lòng chọn vị trí khác.';
    }
    if (code === 'INTERVIEW_ROLE_SKILLS_REQUIRED') {
      return 'Vị trí nghề nghiệp chưa có kỹ năng yêu cầu nên chưa thể tạo câu hỏi phỏng vấn. Vui lòng chọn vị trí khác.';
    }
    if (code === 'INTERVIEW_AI_TIMEOUT') {
      return 'Dịch vụ AI phản hồi quá thời gian chờ. Vui lòng thử lại sau.';
    }
    if (code === 'INTERVIEW_AI_RATE_LIMITED') {
      return 'Dịch vụ AI đang giới hạn số lượng yêu cầu. Vui lòng thử lại sau.';
    }
    if (code === 'INTERVIEW_AI_AUTHENTICATION_FAILED' || code === 'INTERVIEW_AI_UNAVAILABLE') {
      return 'Dịch vụ AI đang không khả dụng. Vui lòng thử lại sau.';
    }
    if (code === 'INTERVIEW_AI_INVALID_REQUEST' || code === 'INTERVIEW_AI_INVALID_RESPONSE') {
      return 'Dịch vụ AI trả về dữ liệu chưa hợp lệ. Vui lòng thử lại sau.';
    }
    if (code === 'INTERVIEW_AI_DUPLICATE_QUESTIONS') {
      return 'Dịch vụ AI sinh câu hỏi trùng lặp. Vui lòng thử lại sau.';
    }
    if (code === 'INTERVIEW_DATABASE_ERROR') {
      return 'Không thể lưu dữ liệu phiên phỏng vấn. Vui lòng thử lại sau.';
    }
    if (code === 'INTERVIEW_NOT_FOUND') {
      return 'Không tìm thấy phiên phỏng vấn.';
    }
    if (code === 'INTERVIEW_QUESTION_NOT_FOUND') {
      return 'Không tìm thấy câu hỏi trong phiên phỏng vấn. Vui lòng tải lại phiên.';
    }
    if (code === 'INTERVIEW_ANSWER_ALREADY_EXISTS') {
      return 'Câu hỏi này đã được trả lời. Hệ thống sẽ tải lại phiên để cập nhật.';
    }
    if (code === 'INTERVIEW_NOT_IN_PROGRESS') {
      return 'Phiên phỏng vấn không còn ở trạng thái có thể trả lời.';
    }
    if (code === 'INTERVIEW_ABANDONED') {
      return 'Phiên phỏng vấn đã bị bỏ dở và không thể tiếp tục. Vui lòng tạo phiên mới.';
    }
    if (code === 'INTERVIEW_INCOMPLETE') {
      return 'Vui lòng trả lời đầy đủ tất cả câu hỏi trước khi hoàn thành phiên.';
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

  function formatNumber(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return '--';
    return Number.isInteger(number) ? String(number) : number.toFixed(1);
  }

  function formatStatus(value) {
    return STATUS_LABELS[value] || value || '-';
  }

  function sortedQuestions(session) {
    const questions = Array.isArray(session && session.questions) ? session.questions.slice() : [];
    questions.sort((a, b) => Number(a.question_order || 0) - Number(b.question_order || 0));
    return questions;
  }

  function roleText(session) {
    const role = session && session.career_role;
    if (!role) return 'Vị trí không còn khả dụng';
    return role.name + (role.level ? ' (' + role.level + ')' : '');
  }

  function answeredCount(questions) {
    return questions.filter((question) => question.answer != null).length;
  }

  function refreshStartState() {
    const button = $('startBtn');
    if (button) button.disabled = submitting || !rolesAvailable;
  }

  function showPanel() {
    const panel = $('sessionPanel');
    if (panel) panel.classList.remove('hidden');
  }

  function setProgress(percent, trackValue) {
    const bar = $('progressBar');
    const track = $('progressTrack');
    const value = Math.max(0, Math.min(100, percent));
    if (bar) bar.style.width = value + '%';
    if (track) track.setAttribute('aria-valuenow', String(Math.round(trackValue == null ? value : trackValue)));
  }

  function renderSessionMeta(session) {
    const questions = sortedQuestions(session);
    const answered = answeredCount(questions);
    const total = questions.length;
    const status = session.status;

    const statusEl = $('sessionStatus');
    if (statusEl) {
      statusEl.className = 'badge ' + (status || '');
      statusEl.textContent = formatStatus(status);
    }

    const roleEl = $('sessionRole');
    if (roleEl) roleEl.textContent = roleText(session);
    const idEl = $('sessionId');
    if (idEl) idEl.textContent = session.id != null ? '#' + session.id : '-';
    const answeredEl = $('sessionAnswered');
    if (answeredEl) answeredEl.textContent = answered + '/' + (total || 3);
    const totalEl = $('sessionTotal');
    if (totalEl) {
      totalEl.textContent = session.total_score != null ? formatNumber(session.total_score) + '/100' : '-';
    }
    const createdEl = $('sessionCreatedAt');
    if (createdEl) createdEl.textContent = formatDateTime(session.created_at);
    const completedEl = $('sessionCompletedAt');
    if (completedEl) completedEl.textContent = formatDateTime(session.completed_at);

    const subtitleParts = [roleText(session)];
    if (session.created_at) subtitleParts.push('Tạo lúc ' + formatDateTime(session.created_at));
    const subtitle = $('sessionSubtitle');
    if (subtitle) subtitle.textContent = subtitleParts.join(' · ');

    const percent = total ? (answered / total) * 100 : 0;
    setProgress(status === 'completed' ? 100 : percent, percent);

    const progressText = $('progressText');
    if (progressText) {
      if (status === 'completed') {
        progressText.textContent = 'Bạn đã hoàn thành đủ ' + total + '/' + total + ' câu hỏi.';
      } else if (status === 'abandoned') {
        progressText.textContent = 'Phiên đã bỏ dở với ' + answered + '/' + (total || 3) + ' câu đã trả lời.';
      } else if (answered === total && total > 0) {
        progressText.textContent = 'Bạn đã trả lời đủ ' + total + ' câu. Hãy hoàn thành phiên để xem điểm tổng.';
      } else {
        progressText.textContent = 'Đã trả lời ' + answered + '/' + (total || 3) + ' câu.';
      }
    }
  }

  function clearElement(el) {
    if (el) el.replaceChildren();
  }

  function renderCriteria(question) {
    const list = $('questionCriteria');
    clearElement(list);
    const criteria = Array.isArray(question.evaluation_criteria) ? question.evaluation_criteria : [];
    if (!criteria.length) {
      const li = document.createElement('li');
      li.textContent = 'Chưa có tiêu chí cụ thể.';
      list.append(li);
      return;
    }
    criteria.forEach((criterion) => {
      const li = document.createElement('li');
      li.textContent = criterion;
      list.append(li);
    });
  }

  function setAnswerControls(disabled) {
    const submitBtn = $('submitAnswerBtn');
    const nextBtn = $('nextQuestionBtn');
    const textarea = $('answerText');
    if (submitBtn) submitBtn.disabled = disabled;
    if (nextBtn) nextBtn.disabled = disabled;
    if (textarea) textarea.disabled = disabled;
  }

  function renderQuestion(index) {
    if (!currentSession) return;
    const questions = sortedQuestions(currentSession);
    if (!questions.length) return;
    currentIndex = Math.max(0, Math.min(index, questions.length - 1));
    const question = questions[currentIndex];
    const isLast = currentIndex === questions.length - 1;
    const answer = question.answer;

    const box = $('questionBox');
    if (box) box.classList.remove('hidden');
    const resultArea = $('resultArea');
    if (resultArea) resultArea.classList.add('hidden');
    const notice = $('stateNotice');
    if (notice) notice.classList.add('hidden');

    const stepEl = $('questionStep');
    if (stepEl) stepEl.textContent = 'Câu ' + (currentIndex + 1) + '/' + questions.length;
    const competencyEl = $('questionCompetency');
    if (competencyEl) competencyEl.textContent = question.competency || 'Năng lực chung';
    const textEl = $('questionText');
    if (textEl) textEl.textContent = question.question_text || '';
    renderCriteria(question);

    const textarea = $('answerText');
    const submitBtn = $('submitAnswerBtn');
    const nextBtn = $('nextQuestionBtn');
    const feedback = $('answerFeedback');
    const feedbackText = $('answerFeedbackText');
    const answerScore = $('answerScore');

    if (answer) {
      if (textarea) {
        textarea.value = answer.answer_text || '';
        textarea.disabled = true;
      }
      if (submitBtn) submitBtn.classList.add('hidden');
      if (feedback) feedback.classList.remove('hidden');
      if (answerScore) answerScore.textContent = formatNumber(answer.score);
      if (feedbackText) feedbackText.textContent = answer.feedback || 'AI không cung cấp nhận xét thêm.';
      if (nextBtn) {
        nextBtn.classList.remove('hidden');
        nextBtn.textContent = isLast ? 'Hoàn thành phiên phỏng vấn' : 'Câu tiếp theo';
      }
    } else {
      if (textarea) {
        textarea.value = '';
        textarea.disabled = false;
      }
      if (submitBtn) submitBtn.classList.remove('hidden');
      if (feedback) feedback.classList.add('hidden');
      if (nextBtn) nextBtn.classList.add('hidden');
      setStatus('', '');
    }
  }

  function showQuestionFlow(session) {
    const questions = sortedQuestions(session);
    const firstUnanswered = questions.findIndex((question) => question.answer == null);
    const resultArea = $('resultArea');
    if (resultArea) resultArea.classList.add('hidden');
    const notice = $('stateNotice');
    if (notice) notice.classList.add('hidden');
    const box = $('questionBox');
    if (box) box.classList.remove('hidden');

    if (!questions.length) {
      if (box) box.classList.add('hidden');
      return;
    }
    if (firstUnanswered === -1) {
      renderQuestion(questions.length - 1);
    } else {
      renderQuestion(firstUnanswered);
    }
  }

  function renderResultList(session) {
    const list = $('resultList');
    if (!list) return;
    list.replaceChildren();
    const questions = sortedQuestions(session);

    questions.forEach((question, index) => {
      const item = document.createElement('article');
      item.className = 'result-item';

      const head = document.createElement('div');
      head.className = 'result-item-head';
      const order = document.createElement('span');
      order.className = 'question-index';
      order.textContent = String(question.question_order || index + 1);
      const competency = document.createElement('strong');
      competency.textContent = question.competency || 'Năng lực chung';
      head.append(order, competency);

      const badge = document.createElement('span');
      if (question.answer) {
        badge.className = 'badge completed';
        badge.textContent = formatNumber(question.answer.score) + '/100';
      } else {
        badge.className = 'badge abandoned';
        badge.textContent = 'Chưa trả lời';
      }
      head.append(badge);

      const questionText = document.createElement('p');
      questionText.className = 'result-question';
      questionText.textContent = question.question_text || '';
      item.append(head, questionText);

      if (question.answer) {
        const answerLabel = document.createElement('div');
        answerLabel.className = 'label';
        answerLabel.textContent = 'Câu trả lời';
        const answerText = document.createElement('p');
        answerText.className = 'result-answer';
        answerText.textContent = question.answer.answer_text || '';
        const feedbackLabel = document.createElement('div');
        feedbackLabel.className = 'label';
        feedbackLabel.textContent = 'Nhận xét của AI';
        const feedbackText = document.createElement('p');
        feedbackText.className = 'result-feedback';
        feedbackText.textContent = question.answer.feedback || '';
        item.append(answerLabel, answerText, feedbackLabel, feedbackText);
      }

      list.append(item);
    });
  }

  function showResult(session, abandoned) {
    const box = $('questionBox');
    if (box) box.classList.add('hidden');
    const resultArea = $('resultArea');
    if (resultArea) resultArea.classList.remove('hidden');

    const notice = $('stateNotice');
    if (notice) {
      if (abandoned) {
        notice.textContent = 'Phiên phỏng vấn đã bị bỏ dở do quá 24 giờ không tương tác hoặc do bạn đã bắt đầu phiên mới cùng vị trí. Bạn không thể tiếp tục trả lời phiên này.';
        notice.classList.remove('hidden');
      } else {
        notice.classList.add('hidden');
      }
    }

    const scoreEl = $('resultScore');
    if (scoreEl) {
      scoreEl.textContent = !abandoned && session.total_score != null
        ? formatNumber(session.total_score)
        : '--';
    }
    const summary = $('resultSummary');
    if (summary) {
      summary.textContent = abandoned
        ? 'Phiên đã bỏ dở nên không có điểm tổng. Bạn có thể bắt đầu phiên mới ở phía trên.'
        : 'Điểm tổng là trung bình cộng điểm của ' + sortedQuestions(session).length + ' câu trả lời.';
    }
    renderResultList(session);
  }

  function renderSession(session, scroll) {
    if (!session || typeof session !== 'object') {
      setStatus('Phản hồi từ máy chủ không hợp lệ. Vui lòng thử lại.', 'error');
      return;
    }
    currentSession = session;
    showPanel();
    renderSessionMeta(session);

    if (session.status === 'completed') {
      showResult(session, false);
    } else if (session.status === 'abandoned') {
      showResult(session, true);
    } else {
      showQuestionFlow(session);
    }

    if (scroll) {
      const panel = $('sessionPanel');
      if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  async function loadSession(sessionId, scroll) {
    if (!sessionId) return;
    setLoading(true);
    try {
      const result = await requestJson('/api/v1/interviews/' + sessionId, {
        headers: authHeaders(false)
      });
      if (result.res.status === 401) { redirectToLogin(); return; }
      if (!result.res.ok) {
        setStatus(describeHttpError(result.res.status, result.data), 'error');
        return;
      }
      const session = result.data && result.data.data;
      renderSession(session, scroll !== false);
    } catch (_err) {
      setStatus('Không thể kết nối máy chủ. Vui lòng kiểm tra kết nối rồi thử lại.', 'error');
    } finally {
      setLoading(false);
    }
  }

  async function submitCurrentAnswer() {
    if (busy || !currentSession) return;
    const questions = sortedQuestions(currentSession);
    const question = questions[currentIndex];
    if (!question) return;
    if (question.answer) {
      setStatus('Câu hỏi này đã được trả lời.', 'error');
      return;
    }
    if (!getToken()) { redirectToLogin(); return; }

    const textarea = $('answerText');
    const answerText = textarea ? textarea.value.trim() : '';
    if (!answerText) {
      setStatus('Vui lòng nhập câu trả lời trước khi gửi.', 'error');
      if (textarea) textarea.focus();
      return;
    }

    busy = true;
    setAnswerControls(true);
    const submitBtn = $('submitAnswerBtn');
    if (submitBtn) submitBtn.disabled = true;
    setLoading(true);
    setStatus('AI đang chấm điểm câu trả lời...', '');

    try {
      const result = await requestJson('/api/v1/interviews/' + currentSession.id + '/answers', {
        method: 'POST',
        headers: authHeaders(true),
        body: JSON.stringify({ question_id: question.id, answer_text: answerText })
      });

      if (result.res.status === 401) { redirectToLogin(); return; }
      if (!result.res.ok) {
        setStatus(describeHttpError(result.res.status, result.data), 'error');
        const code = readErrorCode(result.data);
        if (code === 'INTERVIEW_ANSWER_ALREADY_EXISTS'
          || code === 'INTERVIEW_NOT_IN_PROGRESS'
          || code === 'INTERVIEW_ABANDONED'
          || code === 'INTERVIEW_INCOMPLETE') {
          await loadSession(currentSession.id, false);
        }
        return;
      }

      const stored = result.data && result.data.data;
      if (!stored) {
        setStatus('Phản hồi từ máy chủ không hợp lệ. Vui lòng thử lại.', 'error');
        return;
      }
      question.answer = stored;
      renderSessionMeta(currentSession);
      renderQuestion(currentIndex);
      setStatus('Đã chấm điểm câu trả lời. ' + (currentIndex + 1 < questions.length
        ? 'Bấm "Câu tiếp theo" để tiếp tục.'
        : 'Bấm "Hoàn thành phiên phỏng vấn" để xem điểm tổng.'), 'ok');
      loadHistory(true);
    } catch (_err) {
      setStatus('Không thể kết nối máy chủ. Vui lòng kiểm tra kết nối rồi thử lại.', 'error');
    } finally {
      busy = false;
      setAnswerControls(false);
      // Câu đã có câu trả lời phải giữ textarea ở trạng thái chỉ đọc.
      const questionsAfter = sortedQuestions(currentSession);
      const currentQuestion = questionsAfter[currentIndex];
      const textareaAfter = $('answerText');
      if (textareaAfter && currentQuestion && currentQuestion.answer) {
        textareaAfter.disabled = true;
      }
      setLoading(false);
    }
  }

  async function completeSession() {
    if (busy || !currentSession) return;
    if (!getToken()) { redirectToLogin(); return; }

    busy = true;
    setLoading(true);
    setStatus('Đang hoàn thành phiên phỏng vấn...', '');
    const nextBtn = $('nextQuestionBtn');
    if (nextBtn) nextBtn.disabled = true;

    try {
      const result = await requestJson('/api/v1/interviews/' + currentSession.id + '/complete', {
        method: 'POST',
        headers: authHeaders(false)
      });

      if (result.res.status === 401) { redirectToLogin(); return; }
      if (!result.res.ok) {
        setStatus(describeHttpError(result.res.status, result.data), 'error');
        const code = readErrorCode(result.data);
        if (code === 'INTERVIEW_ABANDONED' || code === 'INTERVIEW_NOT_IN_PROGRESS') {
          await loadSession(currentSession.id, false);
        }
        return;
      }

      const session = result.data && result.data.data;
      renderSession(session, false);
      setStatus((result.data && result.data.message) || 'Hoàn thành phiên phỏng vấn thành công.', 'ok');
      loadHistory(true);
      const panel = $('sessionPanel');
      if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (_err) {
      setStatus('Không thể kết nối máy chủ. Vui lòng kiểm tra kết nối rồi thử lại.', 'error');
    } finally {
      busy = false;
      if (nextBtn) nextBtn.disabled = false;
      setLoading(false);
    }
  }

  function handleNext() {
    if (!currentSession) return;
    const questions = sortedQuestions(currentSession);
    if (!questions.length) return;

    const nextAnswered = questions.every((question) => question.answer != null);
    if (nextAnswered) {
      completeSession();
      return;
    }

    let nextIndex = questions.findIndex((question, index) => index > currentIndex && question.answer == null);
    if (nextIndex === -1) {
      nextIndex = questions.findIndex((question) => question.answer == null);
    }
    renderQuestion(nextIndex === -1 ? questions.length - 1 : nextIndex);
  }

  function historyStatusBadge(status) {
    const badge = document.createElement('span');
    badge.className = 'badge ' + (status || '');
    badge.textContent = formatStatus(status);
    return badge;
  }

  function renderHistory(sessions) {
    const list = $('historyList');
    const empty = $('historyEmpty');
    if (!list) return;
    list.replaceChildren();
    if (empty) empty.classList.add('hidden');

    sessions.forEach((session) => {
      const item = document.createElement('article');
      item.className = 'history-item';

      const main = document.createElement('div');
      const title = document.createElement('div');
      title.className = 'history-title';
      title.textContent = roleText(session);
      const meta = document.createElement('div');
      meta.className = 'history-meta';
      const metaParts = ['#' + session.id, formatDateTime(session.created_at)];
      if (session.total_score != null) {
        metaParts.push('Điểm ' + formatNumber(session.total_score) + '/100');
      }
      meta.textContent = metaParts.join(' · ');
      main.append(title, meta);

      const side = document.createElement('div');
      side.className = 'history-side';
      side.append(historyStatusBadge(session.status));

      if (session.total_score != null) {
        const score = document.createElement('span');
        score.className = 'history-score';
        score.textContent = formatNumber(session.total_score) + '/100';
        side.append(score);
      }

      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'secondary small';
      button.textContent = session.status === 'in_progress' ? 'Tiếp tục' : 'Xem lại';
      button.addEventListener('click', () => {
        loadSession(session.id, true);
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
      const result = await requestJson('/api/v1/interviews?limit=20', {
        headers: authHeaders(false)
      });
      if (result.res.status === 401) { redirectToLogin(); return; }
      if (!result.res.ok) {
        if (!silent) showHistoryMessage('Không tải được lịch sử phỏng vấn. Vui lòng tải lại trang hoặc thử lại sau.');
        return;
      }
      const sessions = (result.data && result.data.data && result.data.data.interviews) || [];
      if (!sessions.length) {
        showHistoryMessage('Bạn chưa có phiên phỏng vấn nào. Hãy bắt đầu phiên đầu tiên ở phía trên.');
        return;
      }
      renderHistory(sessions);
    } catch (_err) {
      if (!silent) showHistoryMessage('Không thể kết nối máy chủ để tải lịch sử. Vui lòng kiểm tra kết nối rồi thử lại.');
    } finally {
      if (loadingEl) loadingEl.classList.add('hidden');
    }
  }

  async function loadCareerRoles() {
    const roleSelect = $('careerRole');
    if (!roleSelect) return;
    setStatus('Đang tải danh sách vị trí nghề nghiệp...', '');
    refreshStartState();

    try {
      const result = await requestJson('/api/v1/careers');
      if (!result.res.ok) {
        setStatus('Không tải được danh sách vị trí nghề nghiệp. Vui lòng tải lại trang hoặc thử lại sau.', 'error');
        return;
      }

      const roles = Array.isArray(result.data && result.data.data) ? result.data.data : [];
      // Backend chỉ tạo được phiên khi vị trí có ít nhất một kỹ năng yêu cầu.
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
      const hint = $('roleHint');
      if (hint) {
        hint.textContent = rolesAvailable
          ? 'Có ' + available.length + ' vị trí khả dụng. Mỗi phiên gồm đúng 3 câu hỏi.'
          : '';
      }

      if (!rolesAvailable) {
        setStatus('Hiện chưa có vị trí nghề nghiệp nào đang hoạt động và đủ dữ liệu kỹ năng để tạo phiên phỏng vấn. Vui lòng quay lại sau.', 'error');
        return;
      }

      const params = new URLSearchParams(window.location.search);
      const preselect = params.get('career_role_id');
      if (preselect && available.some((role) => String(role.id) === preselect)) {
        roleSelect.value = preselect;
      }

      setStatus('Chọn vị trí nghề nghiệp và bấm "Bắt đầu phỏng vấn".', '');
    } catch (_err) {
      rolesAvailable = false;
      refreshStartState();
      setStatus('Không thể kết nối máy chủ để tải danh sách vị trí nghề nghiệp. Vui lòng kiểm tra kết nối rồi tải lại trang.', 'error');
    }
  }

  function bindEvents() {
    const form = $('interviewForm');
    if (form) {
      form.addEventListener('submit', (event) => {
        event.preventDefault();
        if (submitting) {
          setStatus('Đang xử lý yêu cầu trước đó. Vui lòng chờ trong giây lát.', 'error');
          return;
        }
        const roleSelect = $('careerRole');
        if (!rolesAvailable || !roleSelect || !roleSelect.value) {
          setStatus('Vui lòng chọn vị trí nghề nghiệp trước khi bắt đầu.', 'error');
          return;
        }
        if (!getToken()) { redirectToLogin(); return; }

        pendingRoleId = Number(roleSelect.value);
        setStatus('', '');
        showModal(true);
      });
    }

    const rejectBtn = $('consentReject');
    if (rejectBtn) {
      rejectBtn.addEventListener('click', () => {
        pendingRoleId = null;
        showModal(false);
        setStatus('Bạn đã từ chối. Phiên phỏng vấn không được tạo và không có dữ liệu nào được gửi đến AI.', '');
      });
    }

    const acceptBtn = $('consentAccept');
    if (acceptBtn) {
      acceptBtn.addEventListener('click', async () => {
        if (submitting) return;
        if (!pendingRoleId) {
          showModal(false);
          setStatus('Không có yêu cầu phỏng vấn nào đang chờ xác nhận. Vui lòng bấm "Bắt đầu phỏng vấn" để tiếp tục.', 'error');
          return;
        }
        if (!getToken()) {
          showModal(false);
          redirectToLogin();
          return;
        }

        const roleId = pendingRoleId;
        const body = {
          career_role_id: roleId,
          ai_consent: { accepted: true, purpose_version: PURPOSE_VERSION }
        };
        // Chỉ xóa payload sau khi đã tạo body, tránh dùng lại consent cho lần gửi sau.
        pendingRoleId = null;
        submitting = true;
        refreshStartState();
        acceptBtn.disabled = true;
        showModal(false);
        setLoading(true);
        setStatus('Đang tạo phiên phỏng vấn và sinh câu hỏi bằng AI...', '');

        try {
          const result = await requestJson('/api/v1/interviews', {
            method: 'POST',
            headers: authHeaders(true),
            body: JSON.stringify(body)
          });

          if (result.res.status === 401) { redirectToLogin(); return; }
          if (!result.res.ok) {
            setStatus(describeHttpError(result.res.status, result.data), 'error');
            // Nếu backend yêu cầu consent lại, mở modal với đúng vị trí vừa chọn.
            if (readErrorCode(result.data) === 'AI_CONSENT_REQUIRED') {
              pendingRoleId = roleId;
              showModal(true);
            }
            return;
          }

          const session = result.data && result.data.data;
          setStatus((result.data && result.data.message) || 'Tạo phiên phỏng vấn thành công.', 'ok');
          renderSession(session, true);
          loadHistory(true);
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

    const submitBtn = $('submitAnswerBtn');
    if (submitBtn) submitBtn.addEventListener('click', submitCurrentAnswer);

    const nextBtn = $('nextQuestionBtn');
    if (nextBtn) nextBtn.addEventListener('click', handleNext);

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
    loadCareerRoles();
    loadHistory();

    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get('session_id');
    if (sessionId) loadSession(Number(sessionId), true);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
