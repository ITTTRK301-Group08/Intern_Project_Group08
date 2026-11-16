/**
 * Xử lý giao diện Lộ trình học tập cá nhân hóa 30 ngày (UC-08 / M5).
 * Hỗ trợ song song cả môi trường FastAPI live API và xem trực tiếp (direct file/demo).
 */
(function () {
  'use strict';

  if (window.__LaBanRoadmapLoaded__) return;
  window.__LaBanRoadmapLoaded__ = true;

  var isDirectMode = window.location.protocol === 'file:' ||
                     window.location.pathname.indexOf('/app/static/') !== -1 ||
                     window.location.pathname.endsWith('.html') ||
                     !window.location.host;

  var currentPlan = null;
  var activeWeekFilter = 'all';

  function $(id) {
    return document.getElementById(id);
  }

  function showFeedback(message, isError) {
    var box = $('roadmapFeedback');
    if (!box) return;
    box.textContent = message;
    box.className = 'status-card ' + (isError ? 'danger' : 'ok');
    box.hidden = false;
    setTimeout(function () {
      box.hidden = true;
    }, 4500);
  }

  var DEMO_PLAN = {
    id: 1,
    user_id: 1,
    analysis_id: 101,
    target_role: 'Backend Developer (Junior)',
    title: 'Lộ trình 30 ngày chinh phục vị trí Backend Developer',
    start_date: new Date().toISOString().split('T')[0],
    end_date: new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0],
    status: 'active',
    items: [
      {
        id: 101,
        plan_id: 1,
        skill_id: 1,
        skill_name: 'Python',
        week_number: 1,
        task_description: 'Nắm vững lý thuyết nền tảng, Data structures và OOP nâng cao trong Python.',
        estimated_hours: 6.0,
        is_completed: false,
        resource: {
          id: 1,
          title: 'Python Tutorial',
          provider: 'Python Software Foundation',
          url: 'https://docs.python.org/3/tutorial/',
          resource_type: 'documentation',
          is_free: true
        }
      },
      {
        id: 102,
        plan_id: 1,
        skill_id: 2,
        skill_name: 'SQL',
        week_number: 1,
        task_description: 'Củng cố cú pháp truy vấn quan hệ, JOIN, GROUP BY và Aggregation trong SQL.',
        estimated_hours: 6.0,
        is_completed: false,
        resource: {
          id: 2,
          title: 'Interactive SQL Lessons',
          provider: 'SQLBolt',
          url: 'https://sqlbolt.com/',
          resource_type: 'practice',
          is_free: true
        }
      },
      {
        id: 103,
        plan_id: 1,
        skill_id: 1,
        skill_name: 'Python',
        week_number: 2,
        task_description: 'Thực hành lập trình bất đồng bộ (asyncio), Type hints và xử lý lỗi chuẩn trong Python.',
        estimated_hours: 8.0,
        is_completed: false,
        resource: {
          id: 6,
          title: 'Python Course',
          provider: 'Kaggle Learn',
          url: 'https://www.kaggle.com/learn/python',
          resource_type: 'course',
          is_free: true
        }
      },
      {
        id: 104,
        plan_id: 1,
        skill_id: 3,
        skill_name: 'REST APIs',
        week_number: 2,
        task_description: 'Thiết kế RESTful API chuẩn: HTTP status codes, validation và JWT authentication.',
        estimated_hours: 8.0,
        is_completed: false,
        resource: {
          id: 4,
          title: 'MDN Web APIs & Guides',
          provider: 'MDN Web Docs',
          url: 'https://developer.mozilla.org/en-US/docs/Web/API',
          resource_type: 'documentation',
          is_free: true
        }
      },
      {
        id: 105,
        plan_id: 1,
        skill_id: 1,
        skill_name: 'Python & REST APIs',
        week_number: 3,
        task_description: 'Xây dựng Mini-Project: Dịch vụ CRUD hoàn chỉnh kết nối SQLite/MySQL và kiểm thử API.',
        estimated_hours: 10.0,
        is_completed: false,
        resource: {
          id: 3,
          title: 'Git Documentation & Collaboration',
          provider: 'Git SCM',
          url: 'https://git-scm.com/doc',
          resource_type: 'documentation',
          is_free: true
        }
      },
      {
        id: 106,
        plan_id: 1,
        skill_id: 2,
        skill_name: 'SQL',
        week_number: 3,
        task_description: 'Tối ưu hóa câu lệnh SQL, Indexing và thiết kế mô hình thực thể chuẩn hóa.',
        estimated_hours: 8.0,
        is_completed: false,
        resource: {
          id: 2,
          title: 'Interactive SQL Lessons',
          provider: 'SQLBolt',
          url: 'https://sqlbolt.com/',
          resource_type: 'practice',
          is_free: true
        }
      },
      {
        id: 107,
        plan_id: 1,
        skill_id: 1,
        skill_name: 'Python',
        week_number: 4,
        task_description: 'Đóng gói mã nguồn, viết Unit tests với Pytest và tài liệu hóa README.',
        estimated_hours: 6.0,
        is_completed: false,
        resource: {
          id: 1,
          title: 'Python Tutorial',
          provider: 'Python Docs',
          url: 'https://docs.python.org/3/tutorial/',
          resource_type: 'documentation',
          is_free: true
        }
      },
      {
        id: 108,
        plan_id: 1,
        skill_id: 3,
        skill_name: 'Phỏng vấn chuyên môn',
        week_number: 4,
        task_description: 'Luyện tập bộ câu hỏi phỏng vấn kỹ thuật Backend và tự đánh giá độ sẵn sàng.',
        estimated_hours: 6.0,
        is_completed: false,
        resource: {
          id: 7,
          title: 'Intro to Tech Interviews',
          provider: 'La Bàn Nghề Nghiệp',
          url: '/analysis',
          resource_type: 'practice',
          is_free: true
        }
      }
    ]
  };

  var WEEK_TITLES = {
    1: { title: 'Tuần 1: Củng cố nền tảng lý thuyết & Kiến thức trọng tâm', desc: 'Nghiên cứu tài liệu chính thống và hệ thống hóa kiến thức cốt lõi.' },
    2: { title: 'Tuần 2: Nâng cao năng lực chuyên môn & Thực hành chuẩn hóa', desc: 'Luyện tập các bài tập chuyên sâu và kiến trúc lập trình nâng cao.' },
    3: { title: 'Tuần 3: Ứng dụng thực tế & Triển khai Mini-Project', desc: 'Xây dựng sản phẩm hoàn chỉnh gắn với nghiệp vụ thực tế của vị trí.' },
    4: { title: 'Tuần 4: Đánh giá tổng hợp, Portfolio & Ôn luyện phỏng vấn', desc: 'Tối ưu mã nguồn, đóng gói hồ sơ dự án và luyện phỏng vấn kỹ thuật.' }
  };

  function updatePlanMetrics(plan) {
    var items = plan.items || [];
    var total = items.length;
    var completed = items.filter(function (it) { return it.is_completed; }).length;
    var pct = total > 0 ? Math.round((completed / total) * 100) : 0;

    var totalHours = 0;
    items.forEach(function (it) { totalHours += (it.estimated_hours || 0); });

    var daysLeft = 30;
    if (plan.end_date) {
      var end = new Date(plan.end_date);
      var now = new Date();
      var diffDays = Math.ceil((end - now) / (1000 * 60 * 60 * 24));
      daysLeft = Math.max(0, diffDays);
    }

    $('kpiDaysLeft').textContent = daysLeft + ' ngày';
    $('kpiTasksRatio').textContent = completed + ' / ' + total;
    $('kpiTotalHours').textContent = totalHours.toFixed(0) + ' giờ';
    $('overallProgressText').textContent = pct + '%';
    $('overallProgressBar').style.width = pct + '%';

    var statusBadge = $('planStatusBadge');
    if (plan.status === 'completed') {
      statusBadge.textContent = 'Đã hoàn thành';
      statusBadge.className = 'plan-status-pill plan-status-completed';
    } else if (plan.status === 'archived') {
      statusBadge.textContent = 'Đã lưu trữ';
      statusBadge.className = 'plan-status-pill plan-status-archived';
    } else {
      statusBadge.textContent = 'Đang thực hiện';
      statusBadge.className = 'plan-status-pill plan-status-active';
    }

    if (plan.target_role) {
      $('targetRoleBadge').textContent = '🎯 Vị trí: ' + plan.target_role;
    }
    if (plan.title) {
      $('planTitle').textContent = plan.title;
    }
  }

  function renderWeeks(plan) {
    var container = $('weeksContainer');
    if (!container) return;
    container.innerHTML = '';

    var items = plan.items || [];
    var weekGroups = { 1: [], 2: [], 3: [], 4: [] };
    items.forEach(function (it) {
      var w = (it.week_number >= 1 && it.week_number <= 4) ? it.week_number : 1;
      weekGroups[w].push(it);
    });

    for (var w = 1; w <= 4; w++) {
      var wItems = weekGroups[w];
      var weekInfo = WEEK_TITLES[w] || { title: 'Tuần ' + w, desc: '' };
      var wCompleted = wItems.filter(function (i) { return i.is_completed; }).length;

      var weekCard = document.createElement('section');
      weekCard.className = 'week-card';
      weekCard.id = 'week-card-' + w;
      if (activeWeekFilter !== 'all' && activeWeekFilter !== String(w)) {
        weekCard.style.display = 'none';
      }

      var header = document.createElement('div');
      header.className = 'week-card-header';

      var titleGroup = document.createElement('div');
      titleGroup.className = 'week-title-group';

      var badge = document.createElement('span');
      badge.className = 'week-num-badge';
      badge.textContent = 'T' + w;

      var titleTextWrap = document.createElement('div');
      var h2 = document.createElement('h2');
      h2.className = 'week-heading';
      h2.textContent = weekInfo.title;

      var sub = document.createElement('p');
      sub.className = 'week-subtext';
      sub.textContent = weekInfo.desc;

      titleTextWrap.append(h2, sub);
      titleGroup.append(badge, titleTextWrap);

      var statusPill = document.createElement('span');
      statusPill.className = 'week-status-badge';
      statusPill.id = 'week-badge-' + w;
      statusPill.textContent = wCompleted + ' / ' + wItems.length + ' hoàn thành';

      header.append(titleGroup, statusPill);

      var ul = document.createElement('ul');
      ul.className = 'week-task-list';

      wItems.forEach(function (task) {
        var li = document.createElement('li');
        li.className = 'task-item' + (task.is_completed ? ' completed' : '');
        li.id = 'task-row-' + task.id;

        var checkWrap = document.createElement('div');
        checkWrap.className = 'task-checkbox-wrap';

        var checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'task-checkbox';
        checkbox.checked = !!task.is_completed;
        checkbox.setAttribute('aria-label', task.task_description);
        checkbox.addEventListener('change', function () {
          handleTaskToggle(task, checkbox.checked);
        });

        checkWrap.appendChild(checkbox);

        var body = document.createElement('div');
        body.className = 'task-body';

        var meta = document.createElement('div');
        meta.className = 'task-meta-top';

        var skillTag = document.createElement('span');
        skillTag.className = 'skill-tag';
        skillTag.textContent = task.skill_name || 'Kỹ năng';

        var hoursTag = document.createElement('span');
        hoursTag.className = 'hours-tag';
        hoursTag.textContent = '⏱ ' + (task.estimated_hours || 4) + ' giờ học';

        meta.append(skillTag, hoursTag);

        var descP = document.createElement('p');
        descP.className = 'task-desc';
        descP.textContent = task.task_description;

        body.append(meta, descP);

        if (task.resource && task.resource.url) {
          var resPill = document.createElement('a');
          resPill.className = 'resource-pill';
          resPill.href = task.resource.url;
          resPill.target = '_blank';
          resPill.rel = 'noopener noreferrer';
          resPill.innerHTML = '<span class="resource-type-icon">📖</span> ' +
                              task.resource.title + ' (' + task.resource.provider + ') →';
          body.appendChild(resPill);
        }

        li.append(checkWrap, body);
        ul.appendChild(li);
      });

      weekCard.append(header, ul);
      container.appendChild(weekCard);
    }
  }

  function handleTaskToggle(task, isCompleted) {
    task.is_completed = isCompleted;

    var row = $('task-row-' + task.id);
    if (row) {
      if (isCompleted) {
        row.classList.add('completed');
      } else {
        row.classList.remove('completed');
      }
    }

    updatePlanMetrics(currentPlan);

    // Cập nhật badge của tuần tương ứng
    var w = task.week_number || 1;
    var wItems = currentPlan.items.filter(function (it) { return it.week_number === w; });
    var wCompleted = wItems.filter(function (it) { return it.is_completed; }).length;
    var wBadge = $('week-badge-' + w);
    if (wBadge) {
      wBadge.textContent = wCompleted + ' / ' + wItems.length + ' hoàn thành';
    }

    if (isDirectMode) {
      try {
        localStorage.setItem('acm_roadmap_demo_state', JSON.stringify(currentPlan));
      } catch (_) {}
      showFeedback('Đã cập nhật trạng thái nhiệm vụ', false);
      return;
    }

    // Call live API
    var token = window.LaBanApp ? window.LaBanApp.getToken() : '';
    fetch('/api/v1/learning-plans/' + currentPlan.id + '/items/' + task.id, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer ' + token
      },
      body: JSON.stringify({ is_completed: isCompleted })
    })
      .then(function (res) {
        if (!res.ok) throw new Error('Cập nhật thất bại');
        return res.json();
      })
      .then(function () {
        showFeedback('Đã cập nhật tiến độ nhiệm vụ', false);
      })
      .catch(function () {
        // Hoàn tác nếu lỗi
        task.is_completed = !isCompleted;
        updatePlanMetrics(currentPlan);
        showFeedback('Chưa thể lưu trạng thái nhiệm vụ. Vui lòng thử lại.', true);
      });
  }

  function handleArchivePlan() {
    if (!currentPlan) return;
    if (!confirm('Bạn có chắc chắn muốn chuyển lộ trình này vào mục lưu trữ không?')) return;

    if (isDirectMode) {
      currentPlan.status = 'archived';
      updatePlanMetrics(currentPlan);
      showFeedback('Đã lưu trữ lộ trình học tập.', false);
      return;
    }

    var token = window.LaBanApp ? window.LaBanApp.getToken() : '';
    fetch('/api/v1/learning-plans/' + currentPlan.id + '/status', {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer ' + token
      },
      body: JSON.stringify({ status: 'archived' })
    })
      .then(function (res) {
        if (!res.ok) throw new Error('Lỗi lưu trữ');
        return res.json();
      })
      .then(function (body) {
        currentPlan = body.data;
        updatePlanMetrics(currentPlan);
        showFeedback('Đã lưu trữ lộ trình học tập thành công.', false);
      })
      .catch(function () {
        showFeedback('Không thể lưu trữ lộ trình. Vui lòng thử lại.', true);
      });
  }

  function setupFilterTabs() {
    var tabs = document.querySelectorAll('.week-tab-btn');
    Array.prototype.forEach.call(tabs, function (btn) {
      btn.addEventListener('click', function () {
        Array.prototype.forEach.call(tabs, function (t) { t.classList.remove('active'); });
        btn.classList.add('active');

        activeWeekFilter = btn.getAttribute('data-week');
        for (var w = 1; w <= 4; w++) {
          var card = $('week-card-' + w);
          if (!card) continue;
          if (activeWeekFilter === 'all' || activeWeekFilter === String(w)) {
            card.style.display = 'block';
          } else {
            card.style.display = 'none';
          }
        }
      });
    });
  }

  function loadPlan() {
    var token = window.LaBanApp ? window.LaBanApp.getToken() : '';

    if (isDirectMode || !token || token === 'demo_student_token') {
      try {
        var cached = localStorage.getItem('acm_roadmap_demo_state');
        if (cached) {
          currentPlan = JSON.parse(cached);
        } else {
          currentPlan = DEMO_PLAN;
        }
      } catch (_) {
        currentPlan = DEMO_PLAN;
      }
      updatePlanMetrics(currentPlan);
      renderWeeks(currentPlan);
      return;
    }

    fetch('/api/v1/learning-plans?include_archived=false', {
      headers: { Authorization: 'Bearer ' + token }
    })
      .then(function (res) {
        if (res.status === 401) {
          window.LaBanApp.redirectToLogin();
          return null;
        }
        if (!res.ok) throw new Error('Không thể tải lộ trình');
        return res.json();
      })
      .then(function (body) {
        if (!body || !body.data || body.data.length === 0) {
          // Chưa có plan, hiển thị empty state
          $('planContent').hidden = true;
          $('emptyPlanState').hidden = false;
          return;
        }

        var activePlan = body.data.find(function (p) { return p.status === 'active'; }) || body.data[0];
        return fetch('/api/v1/learning-plans/' + activePlan.id, {
          headers: { Authorization: 'Bearer ' + token }
        }).then(function (r) { return r.json(); });
      })
      .then(function (detailBody) {
        if (!detailBody || !detailBody.data) return;
        currentPlan = detailBody.data;
        $('planContent').hidden = false;
        $('emptyPlanState').hidden = true;
        updatePlanMetrics(currentPlan);
        renderWeeks(currentPlan);
      })
      .catch(function () {
        // Fallback demo plan khi có lỗi kết nối
        currentPlan = DEMO_PLAN;
        updatePlanMetrics(currentPlan);
        renderWeeks(currentPlan);
      });
  }

  document.addEventListener('DOMContentLoaded', function () {
    setupFilterTabs();
    var archiveBtn = $('archivePlanBtn');
    if (archiveBtn) {
      archiveBtn.addEventListener('click', handleArchivePlan);
    }
    loadPlan();
  });
})();
