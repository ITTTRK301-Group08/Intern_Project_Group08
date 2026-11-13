/**
 * Xử lý giao diện Dashboard tổng hợp và Biểu đồ Radar kỹ năng (M7).
 * Tích hợp Chart.js với SVG fallback độc lập, tương thích cả môi trường Live FastAPI và Direct.
 */
(function () {
  'use strict';

  if (window.__LaBanDashboardLoaded__) return;
  window.__LaBanDashboardLoaded__ = true;

  var isDirectMode = window.location.protocol === 'file:' ||
                     window.location.pathname.indexOf('/app/static/') !== -1 ||
                     window.location.pathname.endsWith('.html') ||
                     !window.location.host;

  var radarChartInstance = null;

  function $(id) {
    return document.getElementById(id);
  }

  var DEMO_DASHBOARD = {
    summary: {
      readiness_score: 72.5,
      target_role: 'Backend Developer',
      target_role_level: 'Junior',
      total_analyses: 2,
      total_interviews: 2,
      total_skills_evaluated: 5,
      skills_matched_count: 3,
      skills_gap_count: 2,
      active_plan: {
        id: 1,
        title: 'Lộ trình 30 ngày Backend Developer',
        progress_percent: 37.5,
        days_left: 22,
        total_tasks: 8,
        completed_tasks: 3
      }
    },
    radar: {
      role_name: 'Backend Developer',
      overall_readiness: 72.5,
      skills: [
        { skill_name: 'Python', current_level: 3, required_level: 4, gap_score: 1, weight: 1.5, is_gap: true },
        { skill_name: 'SQL', current_level: 2, required_level: 3, gap_score: 1, weight: 1.2, is_gap: true },
        { skill_name: 'Git', current_level: 3, required_level: 3, gap_score: 0, weight: 1.0, is_gap: false },
        { skill_name: 'REST APIs', current_level: 4, required_level: 4, gap_score: 0, weight: 1.5, is_gap: false },
        { skill_name: 'Linux', current_level: 2, required_level: 2, gap_score: 0, weight: 1.0, is_gap: false }
      ]
    },
    progress: {
      has_active_plan: true,
      weekly_breakdown: [
        { week_number: 1, total_tasks: 2, completed_tasks: 2, progress_percent: 100.0 },
        { week_number: 2, total_tasks: 2, completed_tasks: 1, progress_percent: 50.0 },
        { week_number: 3, total_tasks: 2, completed_tasks: 0, progress_percent: 0.0 },
        { week_number: 4, total_tasks: 2, completed_tasks: 0, progress_percent: 0.0 }
      ]
    },
    interviews: {
      items: [
        { id: 1, career_role_name: 'Backend Developer', status: 'completed', question_count: 3, created_at: new Date(Date.now() - 2 * 86400000).toISOString() },
        { id: 2, career_role_name: 'Backend Developer', status: 'completed', question_count: 3, created_at: new Date(Date.now() - 5 * 86400000).toISOString() }
      ]
    }
  };

  function renderSummary(summary) {
    var score = summary.readiness_score || 0;
    $('kpiReadinessVal').textContent = score.toFixed(1);

    var badge = $('readinessStatusBadge');
    if (score >= 80) {
      badge.textContent = 'Sẵn sàng cao';
      badge.className = 'readiness-pill readiness-high';
    } else if (score >= 50) {
      badge.textContent = 'Cần nâng cao';
      badge.className = 'readiness-pill readiness-mid';
    } else {
      badge.textContent = 'Mới bắt đầu';
      badge.className = 'readiness-pill readiness-low';
    }

    $('kpiRoleName').textContent = summary.target_role || 'Chưa chọn';
    $('kpiRoleLevel').textContent = 'Cấp độ: ' + (summary.target_role_level || 'Junior') +
                                    ' • ' + (summary.total_skills_evaluated || 0) + ' kỹ năng đánh giá';

    $('kpiMatchedRatio').textContent = (summary.skills_matched_count || 0) + ' / ' + (summary.total_skills_evaluated || 0);
    $('kpiGapSubtext').textContent = (summary.skills_gap_count || 0) + ' kỹ năng có khoảng cách';

    if (summary.active_plan) {
      $('kpiPlanProgress').textContent = (summary.active_plan.progress_percent || 0).toFixed(1);
      $('kpiPlanDaysLeft').textContent = (summary.active_plan.completed_tasks || 0) + ' / ' +
                                        (summary.active_plan.total_tasks || 0) + ' nhiệm vụ • Còn ' +
                                        (summary.active_plan.days_left || 0) + ' ngày';
    } else {
      $('kpiPlanProgress').textContent = '0';
      $('kpiPlanDaysLeft').textContent = 'Chưa có lộ trình đang thực hiện';
    }

    $('kpiInterviewsCount').textContent = summary.total_interviews || 0;
  }

  function renderSkillsTable(skills) {
    var tbody = $('skillsTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!skills || skills.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--muted); padding: 24px;">Chưa có dữ liệu đánh giá kỹ năng.</td></tr>';
      return;
    }

    skills.forEach(function (sk) {
      var tr = document.createElement('tr');

      // Tên kỹ năng
      var tdName = document.createElement('td');
      tdName.style.fontWeight = '600';
      tdName.textContent = sk.skill_name;

      // Mức hiện tại
      var tdCur = document.createElement('td');
      tdCur.innerHTML = renderLevelDots(sk.current_level, 'active') + ' <span style="font-weight:600; margin-left:6px;">' + sk.current_level + '/5</span>';

      // Chuẩn vị trí
      var tdReq = document.createElement('td');
      tdReq.innerHTML = renderLevelDots(sk.required_level, 'required') + ' <span style="font-weight:600; margin-left:6px;">' + sk.required_level + '/5</span>';

      // Độ hụt
      var tdGap = document.createElement('td');
      var gap = sk.gap_score || 0;
      tdGap.innerHTML = gap > 0
        ? '<span class="gap-badge gap">-' + gap + ' bậc</span>'
        : '<span class="gap-badge ok">Đạt chuẩn</span>';

      // Trọng số
      var tdWeight = document.createElement('td');
      tdWeight.textContent = (sk.weight || 1.0).toFixed(1);

      // Trạng thái
      var tdStatus = document.createElement('td');
      tdStatus.innerHTML = sk.is_gap
        ? '<span style="color: var(--danger); font-weight: 600;">Cần rèn luyện</span>'
        : '<span style="color: var(--ok); font-weight: 600;">Đã đáp ứng</span>';

      // Thao tác
      var tdAction = document.createElement('td');
      var link = document.createElement('a');
      link.href = isDirectMode ? './roadmap.html' : '/roadmap';
      link.className = 'btn-link small';
      link.textContent = 'Học lộ trình →';
      tdAction.appendChild(link);

      tr.append(tdName, tdCur, tdReq, tdGap, tdWeight, tdStatus, tdAction);
      tbody.appendChild(tr);
    });
  }

  function renderLevelDots(level, styleClass) {
    var html = '<div class="level-dots-wrap">';
    for (var i = 1; i <= 5; i++) {
      var cls = (i <= level) ? ' ' + styleClass : '';
      html += '<span class="level-dot' + cls + '"></span>';
    }
    html += '</div>';
    return html;
  }

  function renderRadarChart(radarData) {
    var canvas = $('radarChartCanvas');
    var svgFallback = $('radarSvgFallback');
    if (!canvas) return;

    var skills = radarData.skills || [];
    if (skills.length === 0) {
      canvas.style.display = 'none';
      if (svgFallback) {
        svgFallback.hidden = false;
        svgFallback.innerHTML = '<p style="text-align: center; color: var(--muted); padding: 40px 0;">Chưa có dữ liệu phân tích kỹ năng.</p>';
      }
      return;
    }

    var labels = skills.map(function (s) { return s.skill_name; });
    var currentData = skills.map(function (s) { return s.current_level; });
    var requiredData = skills.map(function (s) { return s.required_level; });

    // Kiểm tra xem Chart.js có sẵn sàng không
    if (typeof window.Chart !== 'undefined') {
      canvas.style.display = 'block';
      if (svgFallback) svgFallback.hidden = true;

      if (radarChartInstance) {
        radarChartInstance.destroy();
      }

      radarChartInstance = new window.Chart(canvas, {
        type: 'radar',
        data: {
          labels: labels,
          datasets: [
            {
              label: 'Năng lực hiện tại',
              data: currentData,
              backgroundColor: 'rgba(8, 124, 114, 0.25)',
              borderColor: '#087c72',
              pointBackgroundColor: '#087c72',
              pointBorderColor: '#fff',
              pointHoverBackgroundColor: '#fff',
              pointHoverBorderColor: '#087c72',
              borderWidth: 2
            },
            {
              label: 'Chuẩn yêu cầu vị trí',
              data: requiredData,
              backgroundColor: 'rgba(234, 179, 8, 0.15)',
              borderColor: '#eab308',
              pointBackgroundColor: '#eab308',
              pointBorderColor: '#fff',
              pointHoverBackgroundColor: '#fff',
              pointHoverBorderColor: '#eab308',
              borderWidth: 2,
              borderDash: [4, 4]
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            r: {
              min: 0,
              max: 5,
              ticks: { stepSize: 1, display: true, backdropColor: 'transparent' },
              grid: { color: 'rgba(21, 50, 71, 0.08)' },
              angleLines: { color: 'rgba(21, 50, 71, 0.08)' },
              pointLabels: {
                font: { size: 12, weight: '600', family: 'sans-serif' },
                color: '#153247'
              }
            }
          },
          plugins: {
            legend: { display: false }
          }
        }
      });
    } else {
      // Fallback vẽ bằng SVG nếu môi trường ngoại tuyến không tải được Chart.js
      canvas.style.display = 'none';
      if (svgFallback) {
        svgFallback.hidden = false;
        renderSvgRadar(svgFallback, labels, currentData, requiredData);
      }
    }
  }

  function renderSvgRadar(container, labels, currentLevels, requiredLevels) {
    var size = 320;
    var center = size / 2;
    var radius = size * 0.38;
    var n = labels.length;
    var angleStep = (Math.PI * 2) / n;

    function getCoords(index, val) {
      var angle = index * angleStep - Math.PI / 2;
      var r = (val / 5) * radius;
      return {
        x: center + r * Math.cos(angle),
        y: center + r * Math.sin(angle)
      };
    }

    var svg = '<svg viewBox="0 0 ' + size + ' ' + size + '" style="width: 100%; height: auto;">';

    // Grid circles
    for (var ring = 1; ring <= 5; ring++) {
      var pts = [];
      for (var i = 0; i < n; i++) {
        var pt = getCoords(i, ring);
        pts.push(pt.x.toFixed(1) + ',' + pt.y.toFixed(1));
      }
      svg += '<polygon points="' + pts.join(' ') + '" fill="none" stroke="#d7e4df" stroke-width="1" />';
    }

    // Axis lines & labels
    for (var a = 0; a < n; a++) {
      var outer = getCoords(a, 5);
      svg += '<line x1="' + center + '" y1="' + center + '" x2="' + outer.x + '" y2="' + outer.y + '" stroke="#d7e4df" stroke-width="1" />';
      var lblPt = getCoords(a, 5.6);
      svg += '<text x="' + lblPt.x + '" y="' + lblPt.y + '" text-anchor="middle" font-size="11" font-weight="600" fill="#153247">' + labels[a] + '</text>';
    }

    // Required Polygon (Gold)
    var reqPts = [];
    for (var r = 0; r < n; r++) {
      var rp = getCoords(r, requiredLevels[r]);
      reqPts.push(rp.x.toFixed(1) + ',' + rp.y.toFixed(1));
    }
    svg += '<polygon points="' + reqPts.join(' ') + '" fill="rgba(234, 179, 8, 0.2)" stroke="#eab308" stroke-width="2" stroke-dasharray="3,3" />';

    // Current Polygon (Teal)
    var curPts = [];
    for (var c = 0; c < n; c++) {
      var cp = getCoords(c, currentLevels[c]);
      curPts.push(cp.x.toFixed(1) + ',' + cp.y.toFixed(1));
    }
    svg += '<polygon points="' + curPts.join(' ') + '" fill="rgba(8, 124, 114, 0.3)" stroke="#087c72" stroke-width="2" />';

    svg += '</svg>';
    container.innerHTML = svg;
  }

  function renderWeeklyProgress(progressData) {
    var container = $('weeklyProgressBarsContainer');
    if (!container) return;
    container.innerHTML = '';

    var breakdown = progressData.weekly_breakdown || [];
    var titles = {
      1: 'Tuần 1: Nền tảng cốt lõi',
      2: 'Tuần 2: Nâng cao năng lực',
      3: 'Tuần 3: Mini-Project thực tế',
      4: 'Tuần 4: Portfolio & Phỏng vấn'
    };

    breakdown.forEach(function (w) {
      var itemDiv = document.createElement('div');
      itemDiv.className = 'dash-week-item';

      var labelRow = document.createElement('div');
      labelRow.className = 'dash-week-label-row';

      var titleSpan = document.createElement('span');
      titleSpan.textContent = titles[w.week_number] || ('Tuần ' + w.week_number);

      var ratioSpan = document.createElement('span');
      ratioSpan.style.color = 'var(--primary-deep)';
      ratioSpan.textContent = w.completed_tasks + '/' + w.total_tasks + ' (' + Math.round(w.progress_percent) + '%)';

      labelRow.append(titleSpan, ratioSpan);

      var track = document.createElement('div');
      track.className = 'dash-week-progress-track';

      var fill = document.createElement('div');
      fill.className = 'dash-week-progress-fill';
      fill.style.width = Math.min(100, Math.max(0, w.progress_percent)) + '%';

      track.appendChild(fill);
      itemDiv.append(labelRow, track);
      container.appendChild(itemDiv);
    });
  }

  function renderInterviewHistory(interviewData) {
    var container = $('interviewSessionsContainer');
    if (!container) return;
    container.innerHTML = '';

    var items = interviewData.items || [];
    if (items.length === 0) {
      container.innerHTML = '<p style="color: var(--muted); font-size: 14px; text-align: center; padding: 16px 0;">Chưa có phiên phỏng vấn thử nào.</p>';
      return;
    }

    items.forEach(function (session) {
      var card = document.createElement('div');
      card.className = 'interview-item-card';

      var left = document.createElement('div');
      left.className = 'interview-item-left';

      var roleTitle = document.createElement('span');
      roleTitle.className = 'interview-item-role';
      roleTitle.textContent = session.career_role_name || 'Phỏng vấn kỹ thuật';

      var dateSpan = document.createElement('span');
      dateSpan.className = 'interview-item-date';
      dateSpan.textContent = (session.created_at ? new Date(session.created_at).toLocaleDateString('vi-VN') : 'Gần đây') +
                             ' • ' + (session.question_count || 3) + ' câu hỏi';

      left.append(roleTitle, dateSpan);

      var badge = document.createElement('span');
      badge.className = 'plan-status-pill plan-status-completed';
      badge.style.fontSize = '11px';
      badge.textContent = 'Hoàn thành';

      card.append(left, badge);
      container.appendChild(card);
    });
  }

  function loadDashboardData() {
    var token = window.LaBanApp ? window.LaBanApp.getToken() : '';

    if (isDirectMode || !token || token === 'demo_student_token') {
      renderSummary(DEMO_DASHBOARD.summary);
      renderSkillsTable(DEMO_DASHBOARD.radar.skills);
      renderRadarChart(DEMO_DASHBOARD.radar);
      renderWeeklyProgress(DEMO_DASHBOARD.progress);
      renderInterviewHistory(DEMO_DASHBOARD.interviews);
      return;
    }

    var headers = { Authorization: 'Bearer ' + token };

    Promise.allSettled([
      fetch('/api/v1/dashboard/summary', { headers: headers }).then(function (r) { return r.json(); }),
      fetch('/api/v1/dashboard/skill-radar', { headers: headers }).then(function (r) { return r.json(); }),
      fetch('/api/v1/dashboard/learning-progress', { headers: headers }).then(function (r) { return r.json(); }),
      fetch('/api/v1/dashboard/interview-history?page=1&page_size=5', { headers: headers }).then(function (r) { return r.json(); })
    ]).then(function (results) {
      var summaryRes = results[0].status === 'fulfilled' && results[0].value ? results[0].value.data : DEMO_DASHBOARD.summary;
      var radarRes = results[1].status === 'fulfilled' && results[1].value ? results[1].value.data : DEMO_DASHBOARD.radar;
      var progressRes = results[2].status === 'fulfilled' && results[2].value ? results[2].value.data : DEMO_DASHBOARD.progress;
      var interviewRes = results[3].status === 'fulfilled' && results[3].value ? results[3].value.data : DEMO_DASHBOARD.interviews;

      renderSummary(summaryRes || DEMO_DASHBOARD.summary);
      var skillsList = (radarRes && radarRes.skills && radarRes.skills.length > 0) ? radarRes.skills : DEMO_DASHBOARD.radar.skills;
      renderSkillsTable(skillsList);
      renderRadarChart(radarRes || DEMO_DASHBOARD.radar);
      renderWeeklyProgress(progressRes || DEMO_DASHBOARD.progress);
      renderInterviewHistory(interviewRes || DEMO_DASHBOARD.interviews);
    }).catch(function () {
      renderSummary(DEMO_DASHBOARD.summary);
      renderSkillsTable(DEMO_DASHBOARD.radar.skills);
      renderRadarChart(DEMO_DASHBOARD.radar);
      renderWeeklyProgress(DEMO_DASHBOARD.progress);
      renderInterviewHistory(DEMO_DASHBOARD.interviews);
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadDashboardData();
  });
})();
