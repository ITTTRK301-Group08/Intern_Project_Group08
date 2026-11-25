/**
 * UI-07 — Phỏng vấn thử (M6).
 * - Tạo phiên, tải câu hỏi theo thứ tự, gửi câu trả lời và nhận điểm/feedback.
 * - Hoàn thành phiên và hiển thị điểm trung bình.
 * - Mọi dữ liệu từ API được render bằng textContent/createElement, không dùng innerHTML.
 */
(function () {
  'use strict';

  if (window.__LaBanInterviewLoaded__) return;
  window.__LaBanInterviewLoaded__ = true;

  var app = window.LaBanApp;
  var isDirectMode = false;

  var PURPOSE_VERSION = 'v1';
  var MAX_ANSWER_LENGTH = 5000;

  var state = {
    roles: [],
    currentSession: null,
    submitting: {}
  };

  var STATUS_META = {
    ready: { label: 'Sẵn sàng', cls: 'badge-info' },
    in_progress: { label: 'Đang thực hiện', cls: 'badge-warn' },
    completed: { label: 'Hoàn thành', cls: 'badge-ok' },
    abandoned: { label: 'Đã bỏ dở', cls: 'badge-muted' },
    failed: { label: 'Thất bại', cls: 'badge-muted' }
  };

  var DEMO_ROLES = [
    { id: 1, name: 'Data Analyst', level: 'Intern' },
    { id: 2, name: 'Frontend Developer', level: 'Fresher' },
    { id: 3, name: 'Backend Developer', level: 'Fresher' },
    { id: 4, name: 'AI / Machine Learning Engineer', level: 'Intern' },
    { id: 5, name: 'DevOps Engineer', level: 'Fresher' },
    { id: 6, name: 'Product Owner', level: 'Intern' }
  ];

  var DEMO_QUESTIONS = [
    {
      question_text: 'Bạn hãy giới thiệu một dự án gần đây và giải thích vai trò của bạn trong dự án đó.',
      competency: 'Giao tiếp và kể chuyện nghề nghiệp',
      evaluation_criteria: ['Nêu rõ bối cảnh dự án', 'Mô tả đúng vai trò cá nhân', 'Nêu kết quả đo lường được']
    },
    {
      question_text: 'Bạn xử lý thế nào khi phát hiện một lỗi nghiêm trọng ngay trước thời điểm bàn giao?',
      competency: 'Xử lý tình huống và quản lý rủi ro',
      evaluation_criteria: ['Nhận diện mức độ ưu tiên', 'Có phương án giảm thiểu rủi ro', 'Giao tiếp minh bạch với nhóm']
    },
    {
      question_text: 'Bạn học một công nghệ mới trong thời gian ngắn bằng cách nào?',
      competency: 'Tự học và thích nghi',
      evaluation_criteria: ['Có quy trình học rõ ràng', 'Biết chọn nguồn tài liệu phù hợp', 'Có cách kiểm chứng kiến thức']
    }
  ];

  var DEMO_HISTORY = [
    {
      id: 9101,
      career_role_name: 'Backend Developer',
      career_role_level: 'Fresher',
      status: 'completed',
      question_count: 3,
      answered_count: 3,
      total_score: 82.5,
      created_at: new Date(Date.now() - 86400000).toISOString(),
      completed_at: new Date(Date.now() - 86400000).toISOString()
    },
    {
      id: 9102,
      career_role_name: 'Data Analyst',
      career_role_level: 'Intern',
      status: 'in_progress',
      question_count: 3,
      answered_count: 1,
      total_score: null,
      created_at: new Date(Date.now() - 3 * 86400000).toISOString(),
      completed_at: null
    },
    {
      id: 9103,
      career_role_name: 'Frontend Developer',
      career_role_level: 'Fresher',
      status: 'abandoned',
      question_count: 3,
      answered_count: 2,
      total_score: null,
      created_at: new Date(Date.now() - 8 * 86400000).toISOString(),
      completed_at: null
    }
  ];

  var statusEl = null;
  var loadingEl = null;
  var roleSelect = null;
  var roleHint = null;
  var consentCheckbox = null;
  var createForm = null;
  var createBtn = null;
  var sessionCard = null;
  var sessionRoleName = null;
  var sessionMeta = null;
  var sessionStatusBadge = null;
  var sessionProgressText = null;
  var progressTrack = null;
  var progressFill = null;
  var questionsContainer = null;
  var completeBtn = null;
  var completeHint = null;
  var completionBox = null;
  var completionScore = null;
  var completionMeta = null;
  var historyContainer = null;

  function $(id) {
    return document.getElementById(id);
  }

  function setStatus(message, type) {
    if (!statusEl) return;
    statusEl.textContent = message || '';
    statusEl.className = message ? 'status ' + (type || 'info') : 'status';
  }

  function showLoading(visible) {
    if (!loadingEl) return;
    if (visible) {
      loadingEl.classList.remove('hidden');
    } else {
      loadingEl.classList.add('hidden');
    }
  }

  function statusMeta(status) {
    return STATUS_META[status] || { label: status || 'Không xác định', cls: 'badge-muted' };
  }

  function isActiveStatus(status) {
    return status === 'ready' || status === 'in_progress';
  }

  function formatScore(value) {
    var number = Number(value);
    if (!Number.isFinite(number)) return '—';
    return Number.isInteger(number) ? String(number) : number.toFixed(2).replace(/0+$/, '').replace(/\.$/, '');
  }

  function formatDate(value) {
    if (app && typeof app.formatDate === 'function') return app.formatDate(value);
    if (!value) return '-';
    var date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleDateString('vi-VN');
  }

  function countAnswered(questions) {
    return (questions || []).filter(function (question) {
      return question && question.answer;
    }).length;
  }

  function apiRequest(path, options) {
    options = options || {};
    var token = app && typeof app.getToken === 'function' ? app.getToken() : '';
    if (!token) {
      if (app && typeof app.redirectToLogin === 'function') app.redirectToLogin();
      return Promise.reject(new Error('Bạn cần đăng nhập để tiếp tục.'));
    }

    var headers = { Authorization: 'Bearer ' + token };
    if (options.body) headers['Content-Type'] = 'application/json';

    return fetch(path, {
      method: options.method || 'GET',
      headers: headers,
      body: options.body
    }).catch(function () {
      throw new Error('Không thể kết nối máy chủ. Vui lòng kiểm tra mạng và thử lại.');
    }).then(function (response) {
      return response.text().then(function (text) {
        var body = null;
        if (text) {
          try { body = JSON.parse(text); } catch (_) { body = null; }
        }
        if (!response.ok) {
          var message = app && typeof app.extractApiError === 'function'
            ? app.extractApiError(body, 'Yêu cầu chưa thể thực hiện. Vui lòng thử lại.')
            : 'Yêu cầu chưa thể thực hiện. Vui lòng thử lại.';
          var error = new Error(message);
          error.status = response.status;
          error.body = body;
          throw error;
        }
        if (!body || body.success !== true) {
          throw new Error('Phản hồi từ máy chủ không hợp lệ. Vui lòng thử lại.');
        }
        return body.data;
      });
    });
  }

  // ---------------------------------------------------------------------
  // Tạo phiên và tải danh sách vị trí
  // ---------------------------------------------------------------------

  function renderRoleOptions() {
    if (!roleSelect) return;
    var selected = roleSelect.value;
    roleSelect.replaceChildren();

    var placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = '-- Chọn vị trí nghề nghiệp --';
    roleSelect.appendChild(placeholder);

    state.roles.forEach(function (role) {
      var option = document.createElement('option');
      option.value = String(role.id);
      option.textContent = role.name + (role.level ? ' (' + role.level + ')' : '');
      roleSelect.appendChild(option);
    });

    if (selected) roleSelect.value = selected;
    if (roleHint) {
      roleHint.textContent = state.roles.length
        ? 'Có ' + state.roles.length + ' vị trí nghề nghiệp để lựa chọn.'
        : 'Chưa có vị trí nghề nghiệp khả dụng.';
    }
  }

  function loadRoles() {
    return apiRequest('/api/v1/catalog/roles').then(function (roles) {
      state.roles = Array.isArray(roles) ? roles : [];
      renderRoleOptions();
    }).catch(function (error) {
      if (isDirectMode) {
        state.roles = DEMO_ROLES.slice();
        renderRoleOptions();
        setStatus('Đang hiển thị dữ liệu minh họa vì chưa kết nối được máy chủ.', 'info');
        return;
      }
      if (roleHint) roleHint.textContent = 'Không thể tải danh sách vị trí nghề nghiệp.';
      setStatus(error.message, 'error');
    });
  }

  function buildDemoSession(roleId) {
    var role = DEMO_ROLES.filter(function (item) {
      return Number(item.id) === Number(roleId);
    })[0] || DEMO_ROLES[0];

    return {
      id: 9001,
      status: 'ready',
      career_role: { id: role.id, name: role.name, level: role.level },
      total_score: null,
      completed_at: null,
      created_at: new Date().toISOString(),
      questions: DEMO_QUESTIONS.map(function (question, index) {
        return {
          id: index + 1,
          question_order: index + 1,
          question_text: question.question_text,
          competency: question.competency,
          evaluation_criteria: question.evaluation_criteria.slice(),
          answer: null
        };
      })
    };
  }

  function handleCreateSession(event) {
    event.preventDefault();
    if (!createBtn || createBtn.disabled) return;

    var roleId = roleSelect ? roleSelect.value : '';
    if (!roleId) {
      setStatus('Vui lòng chọn vị trí nghề nghiệp trước khi bắt đầu.', 'warning');
      if (roleSelect) roleSelect.focus();
      return;
    }
    if (!consentCheckbox || !consentCheckbox.checked) {
      setStatus('Bạn cần đồng ý cho phép sử dụng dữ liệu để AI chấm điểm.', 'warning');
      if (consentCheckbox) consentCheckbox.focus();
      return;
    }

    createBtn.disabled = true;
    createBtn.textContent = 'Đang tạo phiên...';
    showLoading(true);
    setStatus('');

    var request;
    if (isDirectMode) {
      request = new Promise(function (resolve) {
        window.setTimeout(function () { resolve(buildDemoSession(Number(roleId))); }, 400);
      });
    } else {
      request = apiRequest('/api/v1/interviews', {
        method: 'POST',
        body: JSON.stringify({
          career_role_id: Number(roleId),
          ai_consent: { accepted: true, purpose_version: PURPOSE_VERSION }
        })
      });
    }

    request.then(function (session) {
      state.currentSession = session;
      renderSession();
      setStatus('Tạo phiên phỏng vấn thành công. Hãy trả lời từng câu hỏi.', 'ok');
      loadHistory();
      if (sessionCard && typeof sessionCard.scrollIntoView === 'function') {
        sessionCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }).catch(function (error) {
      setStatus(error.message, 'error');
    }).then(function () {
      createBtn.disabled = false;
      createBtn.textContent = 'Bắt đầu phỏng vấn';
      showLoading(false);
    });
  }

  // ---------------------------------------------------------------------
  // Render phiên và câu hỏi
  // ---------------------------------------------------------------------

  function renderSession() {
    var session = state.currentSession;
    if (!sessionCard) return;
    if (!session) {
      sessionCard.classList.add('hidden');
      return;
    }

    sessionCard.classList.remove('hidden');

    var role = session.career_role;
    if (sessionRoleName) {
      sessionRoleName.textContent = role && role.name ? role.name : 'Phiên phỏng vấn';
    }
    if (sessionMeta) {
      var parts = [];
      if (role && role.level) parts.push('Cấp độ ' + role.level);
      parts.push('Tạo lúc ' + formatDate(session.created_at));
      sessionMeta.textContent = parts.join(' • ');
    }
    if (sessionStatusBadge) {
      var meta = statusMeta(session.status);
      sessionStatusBadge.textContent = meta.label;
      sessionStatusBadge.className = 'badge ' + meta.cls;
    }

    renderQuestions();
    updateProgress();
    renderCompletion();
  }

  function buildQuestionCard(question, index, session) {
    var card = document.createElement('article');
    card.className = 'question-card';
    card.setAttribute('data-question-id', String(question.id));

    var head = document.createElement('div');
    head.className = 'question-head';

    var order = document.createElement('span');
    order.className = 'question-order';
    order.textContent = 'Câu ' + (question.question_order || index + 1);

    var competency = document.createElement('span');
    competency.className = 'badge badge-info';
    competency.textContent = question.competency || 'Năng lực chung';

    head.append(order, competency);

    var questionText = document.createElement('p');
    questionText.className = 'question-text';
    questionText.textContent = question.question_text || '';

    var criteria = document.createElement('div');
    criteria.className = 'criteria';
    var criteriaLabel = document.createElement('p');
    criteriaLabel.className = 'field-hint';
    criteriaLabel.textContent = 'Tiêu chí đánh giá';
    var criteriaList = document.createElement('ul');
    (question.evaluation_criteria || []).forEach(function (criterion) {
      var item = document.createElement('li');
      item.textContent = criterion;
      criteriaList.appendChild(item);
    });
    criteria.append(criteriaLabel, criteriaList);

    var label = document.createElement('label');
    label.className = 'answer-label';
    label.textContent = 'Câu trả lời của bạn';

    var textarea = document.createElement('textarea');
    textarea.rows = 5;
    textarea.maxLength = MAX_ANSWER_LENGTH;
    textarea.placeholder = 'Trình bày câu trả lời của bạn một cách cụ thể...';
    textarea.value = question.answer ? (question.answer.answer_text || '') : '';

    var counter = document.createElement('span');
    counter.className = 'answer-counter';
    counter.textContent = textarea.value.length + '/' + MAX_ANSWER_LENGTH;

    label.appendChild(textarea);
    label.appendChild(counter);

    var actions = document.createElement('div');
    actions.className = 'answer-actions';

    var submitBtn = document.createElement('button');
    submitBtn.type = 'button';
    submitBtn.className = 'answer-submit';
    submitBtn.textContent = question.answer ? 'Đã trả lời' : 'Gửi câu trả lời';

    var aiLoading = document.createElement('span');
    aiLoading.className = 'ai-loading hidden';
    aiLoading.textContent = 'AI đang chấm điểm...';

    actions.append(submitBtn, aiLoading);

    var result = document.createElement('div');
    result.className = 'answer-result hidden';

    var scoreRow = document.createElement('div');
    scoreRow.className = 'score-row';
    var scorePill = document.createElement('span');
    scorePill.className = 'score-pill';
    scorePill.textContent = '—/100';
    var scoreCaption = document.createElement('span');
    scoreCaption.className = 'score-caption';
    scoreCaption.textContent = 'Điểm do AI chấm cho câu này';
    scoreRow.append(scorePill, scoreCaption);

    var feedback = document.createElement('p');
    feedback.className = 'feedback-text';
    result.append(scoreRow, feedback);

    if (question.answer) {
      textarea.readOnly = true;
      submitBtn.disabled = true;
      result.classList.remove('hidden');
      scorePill.textContent = formatScore(question.answer.score) + '/100';
      feedback.textContent = question.answer.feedback || '';
    } else if (!isActiveStatus(session.status)) {
      textarea.disabled = true;
      submitBtn.disabled = true;
      submitBtn.textContent = 'Phiên đã kết thúc';
    } else {
      textarea.addEventListener('input', function () {
        counter.textContent = textarea.value.length + '/' + MAX_ANSWER_LENGTH;
      });
      submitBtn.addEventListener('click', function () {
        submitAnswer(question, card);
      });
    }

    card.append(head, questionText, criteria, label, actions, result);
    return card;
  }

  function renderQuestions() {
    if (!questionsContainer) return;
    var session = state.currentSession;
    var questions = session && session.questions ? session.questions.slice() : [];
    questions.sort(function (a, b) {
      return (a.question_order || 0) - (b.question_order || 0);
    });

    questionsContainer.replaceChildren();
    questions.forEach(function (question, index) {
      questionsContainer.appendChild(buildQuestionCard(question, index, session));
    });
  }

  function updateProgress() {
    var session = state.currentSession;
    var questions = session && session.questions ? session.questions : [];
    var answered = countAnswered(questions);
    var total = questions.length;
    var percent = total ? Math.round((answered / total) * 100) : 0;

    if (sessionProgressText) {
      sessionProgressText.textContent = answered + '/' + (total || 3) + ' câu đã trả lời';
    }
    if (progressFill) progressFill.style.width = percent + '%';
    if (!progressTrack && sessionCard) {
      progressTrack = sessionCard.querySelector('.progress-track');
    }
    if (progressTrack) progressTrack.setAttribute('aria-valuenow', String(percent));

    if (completeBtn) {
      completeBtn.disabled = !(total > 0 && answered === total && isActiveStatus(session.status));
    }
    if (completeHint) {
      if (!session) {
        completeHint.textContent = '';
      } else if (session.status === 'completed') {
        completeHint.textContent = 'Phiên đã hoàn thành và được khóa.';
      } else if (session.status === 'abandoned') {
        completeHint.textContent = 'Phiên đã bị bỏ dở, không thể tiếp tục.';
      } else if (answered < total) {
        completeHint.textContent = 'Bạn cần trả lời đủ tất cả câu hỏi trước khi hoàn thành.';
      } else {
        completeHint.textContent = 'Bạn đã trả lời đủ câu hỏi. Có thể hoàn thành phiên.';
      }
    }
  }

  function renderCompletion() {
    if (!completionBox) return;
    var session = state.currentSession;
    if (!session || session.status !== 'completed') {
      completionBox.classList.add('hidden');
      return;
    }

    completionBox.classList.remove('hidden');
    if (completionScore) {
      completionScore.textContent = formatScore(session.total_score) + '/100';
    }
    if (completionMeta) {
      completionMeta.textContent = session.completed_at
        ? 'Hoàn thành lúc ' + formatDate(session.completed_at)
        : 'Phiên đã hoàn thành.';
    }
  }

  // ---------------------------------------------------------------------
  // Gửi câu trả lời
  // ---------------------------------------------------------------------

  function makeDemoAnswer(question, answerText) {
    var words = answerText.split(/\s+/).filter(Boolean).length;
    var raw = 55 + words * 2.5 + answerText.length / 40;
    var score = Math.max(45, Math.min(95, Math.round(raw * 10) / 10));
    return {
      id: Date.now(),
      question_id: question.id,
      answer_text: answerText,
      score: score,
      feedback: 'Câu trả lời đã nêu được ý chính và bám sát câu hỏi. Hãy bổ sung ví dụ cụ thể, số liệu đo lường và kết quả đạt được để tăng tính thuyết phục.',
      created_at: new Date().toISOString()
    };
  }

  function submitAnswer(question, card) {
    var key = String(question.id);
    if (state.submitting[key]) return;

    var textarea = card.querySelector('textarea');
    var submitBtn = card.querySelector('.answer-submit');
    var aiLoading = card.querySelector('.ai-loading');
    var result = card.querySelector('.answer-result');
    var answerText = textarea ? textarea.value.trim() : '';
    var session = state.currentSession;

    if (!answerText) {
      setStatus('Vui lòng nhập câu trả lời trước khi gửi.', 'warning');
      if (textarea) textarea.focus();
      return;
    }
    if (!session || !isActiveStatus(session.status)) {
      setStatus('Phiên phỏng vấn đã kết thúc, không thể gửi thêm câu trả lời.', 'warning');
      return;
    }

    state.submitting[key] = true;
    if (submitBtn) submitBtn.disabled = true;
    if (aiLoading) aiLoading.classList.remove('hidden');
    setStatus('AI đang chấm điểm câu trả lời của bạn...', 'info');

    var request;
    if (isDirectMode) {
      request = new Promise(function (resolve) {
        window.setTimeout(function () { resolve(makeDemoAnswer(question, answerText)); }, 700);
      });
    } else {
      request = apiRequest('/api/v1/interviews/' + session.id + '/answers', {
        method: 'POST',
        body: JSON.stringify({ question_id: question.id, answer_text: answerText })
      });
    }

    request.then(function (data) {
      var answer = data && data.answer ? data.answer : data;
      question.answer = answer;
      if (data && data.session_status) session.status = data.session_status;

      if (textarea) {
        textarea.value = answer.answer_text || answerText;
        textarea.readOnly = true;
      }
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Đã trả lời';
      }
      if (result) {
        result.classList.remove('hidden');
        result.classList.remove('is-error');
        var pill = result.querySelector('.score-pill');
        var feedback = result.querySelector('.feedback-text');
        var caption = result.querySelector('.score-caption');
        if (pill) pill.textContent = formatScore(answer.score) + '/100';
        if (feedback) feedback.textContent = answer.feedback || '';
        if (caption) caption.textContent = 'Điểm do AI chấm cho câu này';
      }

      renderSession();
      setStatus('Đã lưu câu trả lời cho câu ' + question.question_order + '.', 'ok');
      loadHistory();
    }).catch(function (error) {
      if (result) {
        result.classList.remove('hidden');
        result.classList.add('is-error');
        var pill = result.querySelector('.score-pill');
        var feedback = result.querySelector('.feedback-text');
        if (pill) pill.textContent = 'Chưa chấm được';
        if (feedback) feedback.textContent = error.message;
      }
      setStatus(error.message, 'error');
      if (submitBtn) submitBtn.disabled = false;
      if (error.status === 409 && session) {
        loadSessionDetail(session.id, true);
      }
    }).then(function () {
      state.submitting[key] = false;
      if (aiLoading) aiLoading.classList.add('hidden');
      if (submitBtn && !question.answer) submitBtn.disabled = false;
    });
  }

  // ---------------------------------------------------------------------
  // Hoàn thành phiên
  // ---------------------------------------------------------------------

  function makeDemoCompletion(session) {
    var questions = session.questions || [];
    var scores = questions.map(function (question) {
      return Number(question.answer ? question.answer.score : 0);
    });
    var total = scores.length
      ? Math.round((scores.reduce(function (sum, value) { return sum + value; }, 0) / scores.length) * 100) / 100
      : 0;
    return {
      id: session.id,
      status: 'completed',
      total_score: total,
      completed_at: new Date().toISOString(),
      question_count: scores.length,
      answered_count: scores.length
    };
  }

  function handleCompleteSession() {
    var session = state.currentSession;
    if (!session || !completeBtn || completeBtn.disabled) return;

    completeBtn.disabled = true;
    completeBtn.textContent = 'Đang hoàn thành...';
    showLoading(true);
    setStatus('');

    var request;
    if (isDirectMode) {
      request = new Promise(function (resolve) {
        window.setTimeout(function () { resolve(makeDemoCompletion(session)); }, 500);
      });
    } else {
      request = apiRequest('/api/v1/interviews/' + session.id + '/complete', { method: 'POST' });
    }

    request.then(function (data) {
      session.status = data.status || 'completed';
      session.total_score = data.total_score;
      session.completed_at = data.completed_at;
      if (data.question_count) {
        // Giữ nguyên danh sách câu hỏi đã có; số lượng chỉ dùng để hiển thị.
        session.question_count = data.question_count;
      }
      renderSession();
      setStatus('Hoàn thành phiên phỏng vấn. Điểm trung bình: ' + formatScore(session.total_score) + '/100.', 'ok');
      loadHistory();
    }).catch(function (error) {
      setStatus(error.message, 'error');
    }).then(function () {
      completeBtn.textContent = 'Hoàn thành phiên';
      showLoading(false);
      updateProgress();
    });
  }

  // ---------------------------------------------------------------------
  // Lịch sử phiên
  // ---------------------------------------------------------------------

  function buildDemoDetail(sessionId) {
    var summary = DEMO_HISTORY.filter(function (item) {
      return Number(item.id) === Number(sessionId);
    })[0] || DEMO_HISTORY[0];

    var answeredCount = summary.answered_count || 0;
    var demoScores = [82.5, 90, 76];
    var questions = DEMO_QUESTIONS.map(function (question, index) {
      var answer = index < answeredCount
        ? {
            id: index + 1,
            question_id: index + 1,
            answer_text: 'Câu trả lời minh họa cho câu hỏi số ' + (index + 1) + '.',
            score: demoScores[index],
            feedback: 'Câu trả lời có ý chính rõ ràng. Hãy bổ sung ví dụ thực tế và kết quả đo lường cụ thể.',
            created_at: summary.created_at
          }
        : null;
      return {
        id: index + 1,
        question_order: index + 1,
        question_text: question.question_text,
        competency: question.competency,
        evaluation_criteria: question.evaluation_criteria.slice(),
        answer: answer
      };
    });

    return {
      id: summary.id,
      status: summary.status,
      career_role: {
        id: summary.id,
        name: summary.career_role_name,
        level: summary.career_role_level || 'Intern'
      },
      total_score: summary.total_score,
      completed_at: summary.completed_at,
      created_at: summary.created_at,
      questions: questions
    };
  }

  function demoHistoryData() {
    var items = DEMO_HISTORY.slice();
    var session = state.currentSession;
    if (session && session.id !== 9001) {
      var role = session.career_role || {};
      items.unshift({
        id: session.id,
        career_role_name: role.name || 'Phiên phỏng vấn',
        career_role_level: role.level || '',
        status: session.status,
        question_count: (session.questions || []).length,
        answered_count: countAnswered(session.questions),
        total_score: session.total_score,
        created_at: session.created_at,
        completed_at: session.completed_at
      });
    }
    return {
      items: items,
      total: items.length,
      page: 1,
      page_size: 5,
      total_pages: 1
    };
  }

  function describeHistoryMeta(item) {
    var date = formatDate(item.created_at);
    var answered = typeof item.answered_count === 'number' ? item.answered_count : null;
    var total = item.question_count || 3;
    var progress = answered === null ? total + ' câu hỏi' : answered + '/' + total + ' câu đã trả lời';
    return date + ' • ' + progress;
  }

  function renderHistory(items) {
    if (!historyContainer) return;
    historyContainer.replaceChildren();

    if (!items || items.length === 0) {
      var empty = document.createElement('p');
      empty.className = 'history-empty';
      empty.textContent = 'Chưa có phiên phỏng vấn nào.';
      historyContainer.appendChild(empty);
      return;
    }

    items.forEach(function (item) {
      var button = document.createElement('button');
      button.type = 'button';
      button.className = 'history-item';

      var top = document.createElement('span');
      top.className = 'history-top';

      var role = document.createElement('span');
      role.className = 'history-role';
      role.textContent = item.career_role_name || 'Phỏng vấn kỹ thuật';

      var badge = document.createElement('span');
      var meta = statusMeta(item.status);
      badge.className = 'badge history-badge ' + meta.cls;
      badge.textContent = meta.label;

      top.append(role, badge);

      var metaLine = document.createElement('span');
      metaLine.className = 'history-meta';
      metaLine.textContent = describeHistoryMeta(item);

      var score = document.createElement('span');
      score.className = 'history-score';
      if (item.status === 'completed' && item.total_score !== null && item.total_score !== undefined) {
        score.textContent = 'Điểm: ' + formatScore(item.total_score) + '/100';
      } else if (item.status === 'completed') {
        score.textContent = 'Chưa có điểm tổng.';
      } else {
        score.textContent = 'Chưa có điểm tổng.';
      }

      button.append(top, metaLine, score);
      button.addEventListener('click', function () {
        loadSessionDetail(item.id);
      });

      historyContainer.appendChild(button);
    });
  }

  function loadHistory() {
    var request = isDirectMode
      ? Promise.resolve(demoHistoryData())
      : apiRequest('/api/v1/interviews?page=1&page_size=5');

    return request.then(function (data) {
      renderHistory(data && data.items ? data.items : []);
    }).catch(function () {
      if (isDirectMode) {
        renderHistory(demoHistoryData().items);
        return;
      }
      if (historyContainer) {
        historyContainer.replaceChildren();
        var message = document.createElement('p');
        message.className = 'history-empty';
        message.textContent = 'Không thể tải lịch sử phỏng vấn.';
        historyContainer.appendChild(message);
      }
    });
  }

  function loadSessionDetail(sessionId, silent) {
    if (!sessionId) return;
    if (!silent) {
      showLoading(true);
      setStatus('Đang tải phiên phỏng vấn...', 'info');
    }

    var request = isDirectMode
      ? Promise.resolve(buildDemoDetail(sessionId))
      : apiRequest('/api/v1/interviews/' + sessionId);

    request.then(function (session) {
      state.currentSession = session;
      renderSession();
      if (!silent) setStatus('Đã tải phiên phỏng vấn.', 'ok');
    }).catch(function (error) {
      if (!silent) setStatus(error.message, 'error');
    }).then(function () {
      if (!silent) showLoading(false);
    });
  }

  // ---------------------------------------------------------------------
  // Khởi tạo
  // ---------------------------------------------------------------------

  function init() {
    statusEl = $('status');
    loadingEl = $('loading');
    roleSelect = $('roleSelect');
    roleHint = $('roleHint');
    consentCheckbox = $('consentCheckbox');
    createForm = $('createSessionForm');
    createBtn = $('createSessionBtn');
    sessionCard = $('sessionCard');
    sessionRoleName = $('sessionRoleName');
    sessionMeta = $('sessionMeta');
    sessionStatusBadge = $('sessionStatusBadge');
    sessionProgressText = $('sessionProgressText');
    progressFill = $('sessionProgressFill');
    progressTrack = sessionCard ? sessionCard.querySelector('.progress-track') : null;
    questionsContainer = $('questionsContainer');
    completeBtn = $('completeBtn');
    completeHint = $('completeHint');
    completionBox = $('completionBox');
    completionScore = $('completionScore');
    completionMeta = $('completionMeta');
    historyContainer = $('historyContainer');

    if (createForm) createForm.addEventListener('submit', handleCreateSession);
    if (completeBtn) completeBtn.addEventListener('click', handleCompleteSession);

    loadRoles();
    loadHistory();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
