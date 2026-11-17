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
                     !window.location.host;

  var radarChartInstance = null;
  var readinessChartInstance = null;
  var skillHistoryChartInstance = null;
  var readinessReportId = null;
  var readinessHistoryLoaded = false;
  var readinessRefreshTimer = null;

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
      total: 7,
      page: 1,
      page_size: 3,
      total_pages: 3,
      items: [
        { id: 1, career_role_name: 'Backend Developer', status: 'completed', question_count: 3, created_at: new Date(Date.now() - 1 * 86400000).toISOString() },
        { id: 2, career_role_name: 'Backend Developer', status: 'completed', question_count: 3, created_at: new Date(Date.now() - 3 * 86400000).toISOString() },
        { id: 3, career_role_name: 'Data Analyst', status: 'completed', question_count: 3, created_at: new Date(Date.now() - 5 * 86400000).toISOString() },
        { id: 4, career_role_name: 'Frontend Developer', status: 'completed', question_count: 3, created_at: new Date(Date.now() - 7 * 86400000).toISOString() },
        { id: 5, career_role_name: 'Backend Developer', status: 'completed', question_count: 3, created_at: new Date(Date.now() - 10 * 86400000).toISOString() },
        { id: 6, career_role_name: 'DevOps Engineer', status: 'completed', question_count: 3, created_at: new Date(Date.now() - 12 * 86400000).toISOString() },
        { id: 7, career_role_name: 'Backend Developer', status: 'completed', question_count: 3, created_at: new Date(Date.now() - 15 * 86400000).toISOString() }
      ]
    },
    readinessHistory: {
      points: [
        {
          score: 64,
          analyzed_at: new Date(Date.now() - 12 * 86400000).toISOString(),
          skills: [
            { skill_id: 1, skill_name: 'Python', current_level: 2 },
            { skill_id: 2, skill_name: 'SQL', current_level: 3 }
          ]
        },
        {
          score: 72,
          analyzed_at: new Date(Date.now() - 4 * 86400000).toISOString(),
          skills: [
            { skill_id: 1, skill_name: 'Python', current_level: 3 },
            { skill_id: 2, skill_name: 'SQL', current_level: 4 }
          ]
        }
      ],
      stats: {
        report_count: 2,
        latest_score: 72,
        previous_score: 64,
        change_since_first: 8,
        latest_change: 8,
        highest_score: 72,
        lowest_score: 64,
        trend: 'improving'
      }
    }
  };

  function renderSummary(summary) {
    var score = summary && summary.readiness_score;
    $('kpiReadinessVal').textContent = score == null ? '--' : Number(score).toFixed(1);

    var badge = $('readinessStatusBadge');
    if (!summary) {
      badge.textContent = 'Không tải được';
      badge.className = 'readiness-pill';
    } else if (score == null) {
      badge.textContent = 'Chưa có báo cáo';
      badge.className = 'readiness-pill';
    } else if (score >= 80) {
      badge.textContent = 'Sẵn sàng cao';
      badge.className = 'readiness-pill readiness-high';
    } else if (score >= 50) {
      badge.textContent = 'Cần nâng cao';
      badge.className = 'readiness-pill readiness-mid';
    } else {
      badge.textContent = 'Mới bắt đầu';
      badge.className = 'readiness-pill readiness-low';
    }

    $('kpiRoleName').textContent = summary
      ? (summary.target_role || 'Chưa chọn')
      : 'Không tải được dữ liệu';
    $('kpiRoleLevel').textContent = summary && summary.total_skills_evaluated
      ? 'Cấp độ: ' + (summary.target_role_level || '—') + ' • ' + summary.total_skills_evaluated + ' kỹ năng đánh giá'
      : summary ? 'Chưa có báo cáo phân tích' : 'Không thể kết nối đến máy chủ';

    $('kpiMatchedRatio').textContent = (summary ? (summary.skills_matched_count || 0) : '--') + ' / ' +
      (summary ? (summary.total_skills_evaluated || 0) : '--');
    $('kpiGapSubtext').textContent = summary
      ? (summary.skills_gap_count || 0) + ' kỹ năng có khoảng cách'
      : 'Không tải được dữ liệu đánh giá';

    if (summary && summary.active_plan) {
      $('kpiPlanProgress').textContent = (summary.active_plan.progress_percent || 0).toFixed(1);
      $('kpiPlanDaysLeft').textContent = (summary.active_plan.completed_tasks || 0) + ' / ' +
                                        (summary.active_plan.total_tasks || 0) + ' nhiệm vụ • Còn ' +
                                        (summary.active_plan.days_left || 0) + ' ngày';
    } else if (summary) {
      $('kpiPlanProgress').textContent = '0';
      $('kpiPlanDaysLeft').textContent = 'Chưa có lộ trình đang thực hiện';
    } else {
      $('kpiPlanProgress').textContent = '--';
      $('kpiPlanDaysLeft').textContent = 'Không tải được dữ liệu lộ trình';
    }

    $('kpiInterviewsCount').textContent = summary ? (summary.total_interviews || 0) : '--';
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
    if (!breakdown.length) {
      container.textContent = 'Chưa có dữ liệu tiến độ lộ trình.';
      return;
    }
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

  function showReadinessHistoryState(message) {
    var state = $('readinessHistoryState');
    var content = $('readinessHistoryContent');
    if (content) content.hidden = true;
    if (state) {
      state.textContent = message;
      state.hidden = false;
    }
  }

  function renderReadinessHistory(historyData) {
    var state = $('readinessHistoryState');
    var content = $('readinessHistoryContent');
    var points = historyData && historyData.points;
    if (!points || !points.length) {
      showReadinessHistoryState('Chưa có báo cáo phân tích hoàn tất để thể hiện lịch sử điểm.');
      return;
    }

    function monitorReadinessHistory() {
      if (isDirectMode || readinessRefreshTimer) return;
      readinessRefreshTimer = window.setInterval(function () {
        var token = window.LaBanApp ? window.LaBanApp.getToken() : '';
        if (!token || token === 'demo_student_token') return;
        fetch('/api/v1/dashboard/readiness-history', {
          headers: { Authorization: 'Bearer ' + token }
        })
          .then(function (response) {
            if (response.status === 401) {
              if (window.LaBanApp) window.LaBanApp.redirectToLogin();
              throw new Error('Phiên đăng nhập đã hết hạn');
            }
            if (!response.ok) throw new Error('Không thể kiểm tra cập nhật điểm readiness');
            return response.json();
          })
          .then(function (response) {
            if (!response || !response.data || !readinessHistoryLoaded) {
              throw new Error('Phản hồi lịch sử điểm không hợp lệ');
            }
            var points = response.data.points || [];
            var newestId = points.length ? points[points.length - 1].analysis_id : null;
            var status = $('readinessRefreshStatus');
            status.hidden = true;
            if (newestId !== readinessReportId) {
              readinessReportId = newestId;
              loadDashboardData();
            }
          })
          .catch(function () {
            var status = $('readinessRefreshStatus');
            status.textContent = 'Chưa thể kiểm tra báo cáo mới. Biểu đồ đang giữ dữ liệu đã tải.';
            status.hidden = false;
          });
      }, 30000);
    }

    state.hidden = true;
    content.hidden = false;
    var stats = historyData.stats || {};
    var trendLabels = {
      improving: 'Đang cải thiện',
      declining: 'Đang giảm',
      stable: 'Ổn định'
    };
    var statItems = [
      ['Điểm gần nhất', stats.latest_score],
      ['Lần trước', stats.previous_score],
      ['Thay đổi từ lần đầu', stats.change_since_first, true],
      ['So với lần trước', stats.latest_change, true],
      ['Cao nhất', stats.highest_score],
      ['Thấp nhất', stats.lowest_score],
      ['Xu hướng', trendLabels[stats.trend] || 'Chưa đủ dữ liệu']
    ];
    var statsContainer = $('readinessHistoryStats');
    statsContainer.replaceChildren();
    statItems.forEach(function (item) {
      var card = document.createElement('div');
      card.className = 'readiness-stat';
      var label = document.createElement('span');
      label.className = 'readiness-stat-label';
      label.textContent = item[0];
      var value = document.createElement('strong');
      value.className = 'readiness-stat-value';
      if (item[1] == null) {
        value.textContent = '—';
      } else {
        var formatted = item[1];
        if (item[2] && typeof formatted === 'number' && formatted > 0) formatted = '+' + formatted;
        value.textContent = String(formatted) + (typeof formatted === 'number' ? ' pts' : '');
      }
      card.append(label, value);
      statsContainer.appendChild(card);
    });

    var labels = points.map(function (point) {
      return new Date(point.analyzed_at).toLocaleDateString('vi-VN');
    });
    var values = points.map(function (point) { return point.score; });
    var canvas = $('readinessHistoryChart');
    var chartWrap = canvas.parentElement;
    if (readinessChartInstance) {
      readinessChartInstance.destroy();
      readinessChartInstance = null;
    }
    chartWrap.querySelectorAll('svg').forEach(function (node) { node.remove(); });

    if (typeof window.Chart !== 'undefined') {
      canvas.hidden = false;
      readinessChartInstance = new window.Chart(canvas, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [{
            label: 'Career Readiness Score',
            data: values,
            borderColor: '#087c72',
            backgroundColor: 'rgba(8, 124, 114, 0.12)',
            pointBackgroundColor: '#087c72',
            pointRadius: 4,
            pointHoverRadius: 6,
            borderWidth: 2,
            tension: 0.25,
            fill: true
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: { min: 0, max: 100, ticks: { stepSize: 20 }, title: { display: true, text: 'Điểm / 100' } },
            x: { title: { display: true, text: 'Thời điểm phân tích' } }
          },
          plugins: {
            tooltip: {
              callbacks: {
                label: function (context) { return ' ' + context.parsed.y + '/100'; },
                afterLabel: function (context) {
                  return points[context.dataIndex].career_role_name || '';
                }
              }
            },
            legend: { display: false }
          }
        }
      });
    } else {
      canvas.hidden = true;
      renderReadinessSvg(chartWrap, labels, values);
    }
    renderSkillHistory(points, labels);
  }

  function renderSkillHistory(points, labels) {
    var canvas = $('readinessSkillHistoryChart');
    var state = $('skillHistoryState');
    var chartWrap = canvas.parentElement;
    if (skillHistoryChartInstance) {
      skillHistoryChartInstance.destroy();
      skillHistoryChartInstance = null;
    }
    chartWrap.querySelectorAll('svg').forEach(function (node) { node.remove(); });

    var bySkill = {};
    points.forEach(function (point) {
      (point.skills || []).forEach(function (skill) {
        bySkill[skill.skill_id] = skill.skill_name;
      });
    });
    var skillIds = Object.keys(bySkill);
    if (!skillIds.length) {
      canvas.hidden = true;
      state.textContent = 'Chưa có báo cáo lưu điểm thành phần theo kỹ năng.';
      state.hidden = false;
      return;
    }

    state.hidden = true;
    canvas.hidden = false;
    var colors = ['#087c72', '#d28a16', '#5369a8', '#b75050', '#66834f', '#815a91'];
    var datasets = skillIds.map(function (skillId, index) {
      return {
        label: bySkill[skillId],
        data: points.map(function (point) {
          var skill = (point.skills || []).find(function (item) {
            return String(item.skill_id) === skillId;
          });
          return skill ? skill.current_level : null;
        }),
        borderColor: colors[index % colors.length],
        backgroundColor: colors[index % colors.length],
        spanGaps: false,
        tension: 0.2,
        pointRadius: 3
      };
    });

    if (typeof window.Chart !== 'undefined') {
      skillHistoryChartInstance = new window.Chart(canvas, {
        type: 'line',
        data: { labels: labels, datasets: datasets },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: { min: 0, max: 5, ticks: { stepSize: 1 }, title: { display: true, text: 'Mức kỹ năng / 5' } },
            x: { title: { display: true, text: 'Thời điểm phân tích' } }
          },
          plugins: {
            tooltip: {
              callbacks: {
                afterLabel: function (context) {
                  var skill = (points[context.dataIndex].skills || []).find(function (item) {
                    return item.skill_name === context.dataset.label;
                  });
                  return skill ? 'Chuẩn vị trí: ' + skill.required_level + '/5' : '';
                }
              }
            }
          }
        }
      });
      return;
    }

    canvas.hidden = true;
    renderSkillHistorySvg(chartWrap, labels, skillIds, bySkill, datasets, colors);
  }

  function renderSkillHistorySvg(container, labels, skillIds, skillNames, datasets, colors) {
    var ns = 'http://www.w3.org/2000/svg';
    var width = Math.max(480, labels.length * 76);
    var height = 250;
    var left = 38;
    var right = width - 18;
    var top = 14;
    var bottom = height - 38;
    var svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', '0 0 ' + width + ' ' + height);
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', 'Lịch sử điểm theo kỹ năng');
    svg.style.width = '100%';

    for (var level = 0; level <= 5; level++) {
      var y = bottom - (level / 5) * (bottom - top);
      var grid = document.createElementNS(ns, 'line');
      grid.setAttribute('x1', left);
      grid.setAttribute('x2', right);
      grid.setAttribute('y1', y);
      grid.setAttribute('y2', y);
      grid.setAttribute('stroke', '#d7e4df');
      svg.appendChild(grid);
      var tick = document.createElementNS(ns, 'text');
      tick.setAttribute('x', left - 8);
      tick.setAttribute('y', y + 4);
      tick.setAttribute('text-anchor', 'end');
      tick.setAttribute('font-size', '11');
      tick.textContent = String(level);
      svg.appendChild(tick);
    }

    datasets.forEach(function (dataset, datasetIndex) {
      var segment = [];
      function appendSegment() {
        if (segment.length > 1) {
          var path = document.createElementNS(ns, 'path');
          path.setAttribute('d', segment.join(' '));
          path.setAttribute('fill', 'none');
          path.setAttribute('stroke', colors[datasetIndex % colors.length]);
          path.setAttribute('stroke-width', '2');
          svg.appendChild(path);
        }
        segment = [];
      }
      dataset.data.forEach(function (value, pointIndex) {
        if (value == null) {
          appendSegment();
          return;
        }
        var x = labels.length === 1 ? (left + right) / 2 : left + pointIndex * (right - left) / (labels.length - 1);
        var y = bottom - (value / 5) * (bottom - top);
        segment.push((segment.length ? 'L' : 'M') + x + ' ' + y);
        var dot = document.createElementNS(ns, 'circle');
        dot.setAttribute('cx', x);
        dot.setAttribute('cy', y);
        dot.setAttribute('r', '3');
        dot.setAttribute('fill', colors[datasetIndex % colors.length]);
        svg.appendChild(dot);
      });
      appendSegment();
    });

    labels.forEach(function (label, index) {
      var x = labels.length === 1 ? (left + right) / 2 : left + index * (right - left) / (labels.length - 1);
      var dateLabel = document.createElementNS(ns, 'text');
      dateLabel.setAttribute('x', x);
      dateLabel.setAttribute('y', bottom + 22);
      dateLabel.setAttribute('text-anchor', 'middle');
      dateLabel.setAttribute('font-size', '11');
      dateLabel.textContent = label;
      svg.appendChild(dateLabel);
    });
    var legend = document.createElementNS(ns, 'text');
    legend.setAttribute('x', left);
    legend.setAttribute('y', height - 4);
    legend.setAttribute('font-size', '11');
    legend.textContent = skillIds.map(function (id) { return skillNames[id]; }).join(' · ');
    svg.appendChild(legend);
    container.appendChild(svg);
  }

  function renderReadinessSvg(container, labels, values) {
    var ns = 'http://www.w3.org/2000/svg';
    var width = Math.max(480, labels.length * 76);
    var height = 270;
    var left = 44;
    var right = width - 18;
    var top = 14;
    var bottom = height - 38;
    var svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', '0 0 ' + width + ' ' + height);
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', 'Lịch sử điểm readiness theo thời gian');
    svg.style.width = '100%';

    [0, 20, 40, 60, 80, 100].forEach(function (score) {
      var y = bottom - (score / 100) * (bottom - top);
      var line = document.createElementNS(ns, 'line');
      line.setAttribute('x1', left);
      line.setAttribute('x2', right);
      line.setAttribute('y1', y);
      line.setAttribute('y2', y);
      line.setAttribute('stroke', '#d7e4df');
      svg.appendChild(line);
      var tick = document.createElementNS(ns, 'text');
      tick.setAttribute('x', left - 8);
      tick.setAttribute('y', y + 4);
      tick.setAttribute('text-anchor', 'end');
      tick.setAttribute('font-size', '11');
      tick.textContent = String(score);
      svg.appendChild(tick);
    });

    var pathData = values.map(function (score, index) {
      var x = labels.length === 1 ? (left + right) / 2 : left + index * (right - left) / (labels.length - 1);
      var y = bottom - (score / 100) * (bottom - top);
      return (index ? 'L' : 'M') + x + ' ' + y;
    }).join(' ');
    var path = document.createElementNS(ns, 'path');
    path.setAttribute('d', pathData);
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke', '#087c72');
    path.setAttribute('stroke-width', '3');
    svg.appendChild(path);

    values.forEach(function (score, index) {
      var x = labels.length === 1 ? (left + right) / 2 : left + index * (right - left) / (labels.length - 1);
      var y = bottom - (score / 100) * (bottom - top);
      var point = document.createElementNS(ns, 'circle');
      point.setAttribute('cx', x);
      point.setAttribute('cy', y);
      point.setAttribute('r', '4');
      point.setAttribute('fill', '#087c72');
      svg.appendChild(point);
      var dateLabel = document.createElementNS(ns, 'text');
      dateLabel.setAttribute('x', x);
      dateLabel.setAttribute('y', bottom + 22);
      dateLabel.setAttribute('text-anchor', 'middle');
      dateLabel.setAttribute('font-size', '11');
      dateLabel.textContent = labels[index];
      svg.appendChild(dateLabel);
    });
    container.appendChild(svg);
  }

  var currentInterviewPage = 1;
  var INTERVIEW_PAGE_SIZE = 3;

  function renderInterviewHistory(interviewData) {
    var container = $('interviewSessionsContainer');
    var paginationBar = $('interviewPagination');
    var pageInfo = $('interviewPageInfo');
    var prevBtn = $('prevInterviewPageBtn');
    var nextBtn = $('nextInterviewPageBtn');

    if (!container) return;
    container.innerHTML = '';

    var total = interviewData.total || (interviewData.items ? interviewData.items.length : 0);
    var page = interviewData.page || currentInterviewPage;
    var pageSize = interviewData.page_size || INTERVIEW_PAGE_SIZE;
    var totalPages = interviewData.total_pages || Math.max(1, Math.ceil(total / pageSize));

    currentInterviewPage = page;

    var items = interviewData.items || [];
    // Nếu trong direct mode và items chưa được slice theo trang
    if (isDirectMode && items.length > pageSize) {
      var start = (page - 1) * pageSize;
      items = items.slice(start, start + pageSize);
    }

    if (items.length === 0) {
      container.innerHTML = '<p style="color: var(--muted); font-size: 14px; text-align: center; padding: 16px 0;">Chưa có phiên phỏng vấn thử nào.</p>';
      if (paginationBar) paginationBar.style.display = 'none';
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

    // Cập nhật thanh phân trang
    if (paginationBar) {
      if (total > pageSize || totalPages > 1) {
        paginationBar.style.display = 'flex';
        if (pageInfo) {
          pageInfo.textContent = 'Trang ' + page + ' / ' + totalPages + ' (Tổng ' + total + ' phiên)';
        }
        if (prevBtn) {
          prevBtn.disabled = (page <= 1);
          prevBtn.onclick = function () {
            if (page > 1) fetchInterviewPage(page - 1);
          };
        }
        if (nextBtn) {
          nextBtn.disabled = (page >= totalPages);
          nextBtn.onclick = function () {
            if (page < totalPages) fetchInterviewPage(page + 1);
          };
        }
      } else {
        paginationBar.style.display = 'none';
      }
    }
  }

  function fetchInterviewPage(page) {
    if (isDirectMode) {
      currentInterviewPage = page;
      var total = DEMO_DASHBOARD.interviews.total || 7;
      var totalPages = Math.ceil(total / INTERVIEW_PAGE_SIZE);
      renderInterviewHistory({
        total: total,
        page: page,
        page_size: INTERVIEW_PAGE_SIZE,
        total_pages: totalPages,
        items: DEMO_DASHBOARD.interviews.items
      });
      return;
    }

    var token = window.LaBanApp ? window.LaBanApp.getToken() : '';
    fetch('/api/v1/dashboard/interview-history?page=' + page + '&page_size=' + INTERVIEW_PAGE_SIZE, {
      headers: { Authorization: 'Bearer ' + token }
    })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (res && res.data) {
          renderInterviewHistory(res.data);
        }
      })
      .catch(function () {
        /* Bỏ qua lỗi kết nối và giữ trang hiện tại */
      });
  }

  function loadDashboardData() {
    var token = window.LaBanApp ? window.LaBanApp.getToken() : '';

    if (isDirectMode) {
      renderSummary(DEMO_DASHBOARD.summary);
      renderSkillsTable(DEMO_DASHBOARD.radar.skills);
      renderRadarChart(DEMO_DASHBOARD.radar);
      renderWeeklyProgress(DEMO_DASHBOARD.progress);
      renderInterviewHistory(DEMO_DASHBOARD.interviews);
      renderReadinessHistory(DEMO_DASHBOARD.readinessHistory);
      return;
    }
    if (!token || token === 'demo_student_token') {
      if (window.LaBanApp) window.LaBanApp.redirectToLogin();
      return;
    }

    var headers = { Authorization: 'Bearer ' + token };
    function fetchData(url) {
      return fetch(url, { headers: headers }).then(function (response) {
        if (response.status === 401) {
          if (window.LaBanApp) window.LaBanApp.redirectToLogin();
          throw new Error('Phiên đăng nhập đã hết hạn');
        }
        if (!response.ok) throw new Error('Không thể tải dữ liệu');
        return response.json();
      }).then(function (response) {
        if (!response || !response.data) throw new Error('Phản hồi API không hợp lệ');
        return response.data;
      });
    }

    Promise.allSettled([
      fetchData('/api/v1/dashboard/summary'),
      fetchData('/api/v1/dashboard/skill-radar'),
      fetchData('/api/v1/dashboard/learning-progress'),
      fetchData('/api/v1/dashboard/interview-history?page=1&page_size=5'),
      fetchData('/api/v1/dashboard/readiness-history')
    ]).then(function (results) {
      var summary = results[0].status === 'fulfilled' ? results[0].value : null;
      var radar = results[1].status === 'fulfilled' ? results[1].value : null;
      var progress = results[2].status === 'fulfilled' ? results[2].value : null;
      var interviews = results[3].status === 'fulfilled' ? results[3].value : null;
      var history = results[4].status === 'fulfilled' ? results[4].value : null;

      renderSummary(summary);
      renderSkillsTable(radar ? radar.skills : []);
      renderRadarChart(radar || { skills: [] });
      renderWeeklyProgress(progress || {});
      renderInterviewHistory(interviews || { items: [] });
      if (history) {
        var points = history.points || [];
        readinessReportId = points.length ? points[points.length - 1].analysis_id : null;
        readinessHistoryLoaded = true;
        renderReadinessHistory(history);
        monitorReadinessHistory();
      }
      else showReadinessHistoryState('Không thể tải lịch sử điểm. Vui lòng thử lại sau.');
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadDashboardData();
  });
})();
