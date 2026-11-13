(function () {
  'use strict';

  if (window.__LaBanExploreLoaded__) return;
  window.__LaBanExploreLoaded__ = true;

  var $ = function (id) { return document.getElementById(id); };
  var statusEl = $('status');
  var loadingEl = $('loading');
  var roles = [];
  var skills = [];
  var resources = [];
  var selectedRoleId = null;
  var currentView = 'all';

  var DEFAULT_CATEGORIES = [
    { id: 1, name: 'Software Development', slug: 'software-development', description: 'Thiết kế, xây dựng và tối ưu ứng dụng phần mềm.' },
    { id: 2, name: 'Data and AI', slug: 'data-and-ai', description: 'Phân tích dữ liệu lớn và xây dựng hệ thống trí tuệ nhân tạo.' },
    { id: 3, name: 'Cybersecurity', slug: 'cybersecurity', description: 'Bảo mật hệ thống, mạng máy tính và an toàn thông tin.' },
    { id: 4, name: 'Product Design', slug: 'product-design', description: 'Nghiên cứu trải nghiệm người dùng và thiết kế giao diện số.' }
  ];

  var DEFAULT_SKILLS = [
    { id: 1, name: 'Python', description: 'Ngôn ngữ lập trình phổ biến cho backend, tự động hóa và dữ liệu.' },
    { id: 2, name: 'SQL', description: 'Truy vấn, thiết kế và tối ưu cơ sở dữ liệu quan hệ.' },
    { id: 3, name: 'Git', description: 'Quản lý phiên bản mã nguồn và cộng tác nhóm qua GitHub/GitLab.' },
    { id: 4, name: 'REST APIs', description: 'Thiết kế, xây dựng và tích hợp chuẩn dịch vụ web HTTP.' },
    { id: 5, name: 'JavaScript', description: 'Xây dựng ứng dụng web tương tác mượt mà và logic phía client.' },
    { id: 6, name: 'HTML and CSS', description: 'Định hình cấu trúc giao diện chuẩn SEO và tạo kiểu phong cách web.' },
    { id: 7, name: 'Data Visualization', description: 'Trực quan hóa dữ liệu và biểu đồ hóa thông tin kinh doanh.' },
    { id: 8, name: 'Statistics', description: 'Phương pháp thống kê, xác suất và phân tích độ tin cậy.' },
    { id: 9, name: 'Machine Learning', description: 'Huấn luyện, đánh giá và triển khai mô hình học máy.' },
    { id: 10, name: 'Linux', description: 'Sử dụng dòng lệnh shell và quản trị hệ điều hành máy chủ Linux.' },
    { id: 11, name: 'Networking', description: 'Kiến trúc mạng máy tính, giao thức TCP/IP, DNS và định tuyến.' },
    { id: 12, name: 'Threat Modeling', description: 'Nhận diện, phân tích rủi ro và mô hình hóa mối đe dọa an ninh.' },
    { id: 13, name: 'UX Research', description: 'Nghiên cứu nhu cầu, hành vi và phỏng vấn người dùng thực tế.' },
    { id: 14, name: 'Wireframing', description: 'Xây dựng khung bố cục sơ bộ trước khi thiết kế UI chi tiết.' }
  ];

  var DEFAULT_ROLES = [
    {
      id: 1,
      category_id: 1,
      name: 'Backend Developer',
      slug: 'backend-developer',
      level: 'Junior',
      description: 'Thiết kế kiến trúc hệ thống, xây dựng RESTful APIs và tối ưu cơ sở dữ liệu phía máy chủ.',
      category: { id: 1, name: 'Software Development' },
      required_skills: [
        { skill: { id: 1, name: 'Python', description: 'Lập trình backend với FastAPI/Django' }, required_level: 4, is_required: true, weight: 1.5 },
        { skill: { id: 4, name: 'REST APIs', description: 'Thiết kế API chuẩn RESTful' }, required_level: 4, is_required: true, weight: 1.5 },
        { skill: { id: 2, name: 'SQL', description: 'Tối ưu truy vấn MySQL/PostgreSQL' }, required_level: 3, is_required: true, weight: 1.2 },
        { skill: { id: 3, name: 'Git', description: 'Quy trình Git Flow và Pull Request' }, required_level: 3, is_required: true, weight: 1.0 },
        { skill: { id: 10, name: 'Linux', description: 'Thao tác terminal và triển khai server' }, required_level: 2, is_required: false, weight: 0.8 }
      ]
    },
    {
      id: 2,
      category_id: 1,
      name: 'Frontend Developer',
      slug: 'frontend-developer',
      level: 'Fresher',
      description: 'Xây dựng giao diện web tương tác, tối ưu trải nghiệm người dùng và tích hợp API backend.',
      category: { id: 1, name: 'Software Development' },
      required_skills: [
        { skill: { id: 5, name: 'JavaScript', description: 'Lập trình ES6+ và xử lý bất đồng bộ' }, required_level: 4, is_required: true, weight: 1.5 },
        { skill: { id: 6, name: 'HTML and CSS', description: 'Bố cục Flexbox, Grid và Responsive' }, required_level: 4, is_required: true, weight: 1.4 },
        { skill: { id: 3, name: 'Git', description: 'Quản lý phiên bản mã nguồn' }, required_level: 2, is_required: true, weight: 1.0 },
        { skill: { id: 4, name: 'REST APIs', description: 'Tích hợp dữ liệu từ Backend API' }, required_level: 2, is_required: false, weight: 0.9 }
      ]
    },
    {
      id: 3,
      category_id: 2,
      name: 'Data Analyst',
      slug: 'data-analyst',
      level: 'Intern',
      description: 'Chuyển đổi dữ liệu thô thành bảng điều khiển trực quan và báo cáo chuyên sâu hỗ trợ ra quyết định.',
      category: { id: 2, name: 'Data and AI' },
      required_skills: [
        { skill: { id: 2, name: 'SQL', description: 'Truy vấn kết xuất dữ liệu báo cáo' }, required_level: 4, is_required: true, weight: 1.5 },
        { skill: { id: 7, name: 'Data Visualization', description: 'Trực quan hóa với Power BI / Tableau' }, required_level: 4, is_required: true, weight: 1.4 },
        { skill: { id: 1, name: 'Python', description: 'Xử lý dữ liệu với Pandas và NumPy' }, required_level: 3, is_required: true, weight: 1.2 },
        { skill: { id: 8, name: 'Statistics', description: 'Thống kê mô tả và kiểm định giả thuyết' }, required_level: 3, is_required: true, weight: 1.1 }
      ]
    },
    {
      id: 4,
      category_id: 2,
      name: 'Machine Learning Engineer',
      slug: 'machine-learning-engineer',
      level: 'Junior',
      description: 'Nghiên cứu thuật toán, huấn luyện mô hình dự đoán và triển khai giải pháp AI vào sản phẩm thực tế.',
      category: { id: 2, name: 'Data and AI' },
      required_skills: [
        { skill: { id: 9, name: 'Machine Learning', description: 'Thuật toán học máy Scikit-Learn/PyTorch' }, required_level: 5, is_required: true, weight: 1.6 },
        { skill: { id: 1, name: 'Python', description: 'Lập trình chuyên sâu cho khoa học dữ liệu' }, required_level: 4, is_required: true, weight: 1.4 },
        { skill: { id: 8, name: 'Statistics', description: 'Đại số tuyến tính và giải tích tối ưu' }, required_level: 4, is_required: true, weight: 1.3 },
        { skill: { id: 2, name: 'SQL', description: 'Khai thác dữ liệu huấn luyện mô hình' }, required_level: 2, is_required: false, weight: 0.8 }
      ]
    },
    {
      id: 5,
      category_id: 3,
      name: 'Cybersecurity Analyst',
      slug: 'cybersecurity-analyst',
      level: 'Fresher',
      description: 'Giám sát an ninh mạng, phát hiện lỗ hổng bảo mật và bảo vệ hạ tầng công nghệ thông tin.',
      category: { id: 3, name: 'Cybersecurity' },
      required_skills: [
        { skill: { id: 10, name: 'Linux', description: 'Phân tích hệ thống và nhật ký truy cập' }, required_level: 4, is_required: true, weight: 1.4 },
        { skill: { id: 11, name: 'Networking', description: 'Bảo mật giao thức mạng và tường lửa' }, required_level: 4, is_required: true, weight: 1.4 },
        { skill: { id: 12, name: 'Threat Modeling', description: 'Đánh giá nguy cơ theo tiêu chuẩn OWASP' }, required_level: 3, is_required: true, weight: 1.2 }
      ]
    },
    {
      id: 6,
      category_id: 4,
      name: 'UX/UI Designer',
      slug: 'ux-ui-designer',
      level: 'Intern',
      description: 'Nghiên cứu hành vi người dùng, vẽ wireframe và thiết kế giao diện sản phẩm số thân thiện.',
      category: { id: 4, name: 'Product Design' },
      required_skills: [
        { skill: { id: 13, name: 'UX Research', description: 'Phỏng vấn và lập chân dung người dùng' }, required_level: 4, is_required: true, weight: 1.5 },
        { skill: { id: 14, name: 'Wireframing', description: 'Thiết kế mẫu nhanh trên Figma' }, required_level: 4, is_required: true, weight: 1.5 },
        { skill: { id: 6, name: 'HTML and CSS', description: 'Hiểu cấu trúc web để thiết kế khả thi' }, required_level: 2, is_required: false, weight: 0.8 }
      ]
    }
  ];

  var DEFAULT_RESOURCES = [
    { id: 1, skill_id: 1, title: 'Python Official Tutorial', provider: 'Python Software Foundation', url: 'https://docs.python.org/3/tutorial/', resource_type: 'documentation', description: 'Tài liệu hướng dẫn chính thức và bài bản từ Python Foundation.', is_free: true, skill: { id: 1, name: 'Python' } },
    { id: 2, skill_id: 2, title: 'Interactive SQL Lessons', provider: 'SQLBolt', url: 'https://sqlbolt.com/', resource_type: 'practice', description: 'Bài tập thực hành SQL tương tác trực tiếp trên trình duyệt từ cơ bản đến nâng cao.', is_free: true, skill: { id: 2, name: 'SQL' } },
    { id: 3, skill_id: 3, title: 'Git Documentation & Pro Git', provider: 'Git SCM', url: 'https://git-scm.com/doc', resource_type: 'documentation', description: 'Toàn bộ cẩm nang sử dụng Git chính thức kèm sách Pro Git miễn phí.', is_free: true, skill: { id: 3, name: 'Git' } },
    { id: 4, skill_id: 5, title: 'MDN JavaScript Guide', provider: 'MDN Web Docs', url: 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide', resource_type: 'documentation', description: 'Cẩm nang toàn diện về JavaScript hiện đại từ Mozilla Developer Network.', is_free: true, skill: { id: 5, name: 'JavaScript' } },
    { id: 5, skill_id: 6, title: 'Learn Web Development (HTML/CSS)', provider: 'MDN Web Docs', url: 'https://developer.mozilla.org/en-US/docs/Learn', resource_type: 'course', description: 'Lộ trình học web bài bản từ cấu trúc HTML, CSS layout đến responsive design.', is_free: true, skill: { id: 6, name: 'HTML and CSS' } },
    { id: 6, skill_id: 7, title: 'Data Visualization Course', provider: 'Kaggle Learn', url: 'https://www.kaggle.com/learn/data-visualization', resource_type: 'course', description: 'Khóa học trực quan hóa dữ liệu ứng dụng với bài tập thực hành cụ thể.', is_free: true, skill: { id: 7, name: 'Data Visualization' } },
    { id: 7, skill_id: 9, title: 'Machine Learning Crash Course', provider: 'Google Developers', url: 'https://developers.google.com/machine-learning/crash-course', resource_type: 'course', description: 'Khóa học nhập môn Machine Learning thực tế với ví dụ và bài tập từ Google.', is_free: true, skill: { id: 9, name: 'Machine Learning' } },
    { id: 8, skill_id: 10, title: 'Linux Journey', provider: 'Linux Journey', url: 'https://linuxjourney.com/', resource_type: 'course', description: 'Học Linux từng bước miễn phí: dòng lệnh, phân quyền, tiến trình và mạng.', is_free: true, skill: { id: 10, name: 'Linux' } },
    { id: 9, skill_id: 12, title: 'OWASP Top 10 Security Risks', provider: 'OWASP Foundation', url: 'https://owasp.org/www-project-top-ten/', resource_type: 'documentation', description: 'Báo cáo chuẩn quốc tế về 10 lỗ hổng an ninh ứng dụng web phổ biến nhất.', is_free: true, skill: { id: 12, name: 'Threat Modeling' } },
    { id: 10, skill_id: 14, title: 'Guide to Wireframing', provider: 'Figma Resource Library', url: 'https://www.figma.com/resource-library/what-is-wireframing/', resource_type: 'article', description: 'Hướng dẫn xây dựng khung wireframe và thiết kế cấu trúc sản phẩm số hiệu quả.', is_free: true, skill: { id: 14, name: 'Wireframing' } }
  ];

  var RESOURCE_TYPE_LABELS = {
    documentation: 'Tài liệu',
    course: 'Khóa học',
    video: 'Video',
    article: 'Bài viết',
    practice: 'Thực hành'
  };

  function setStatus(message, isError) {
    statusEl.textContent = message || '';
    statusEl.className = 'status' + (isError ? ' error' : '');
  }

  function setLoading(on) {
    if (loadingEl) loadingEl.classList.toggle('hidden', !on);
  }

  async function getData(path) {
    var response = await fetch(path);
    if (!response.ok) throw new Error('Không thể tải dữ liệu khám phá lúc này.');
    var body = await response.json();
    return body.data || [];
  }

  function addEmptyState(container, message) {
    var empty = document.createElement('p');
    empty.className = 'empty-state';
    empty.textContent = message;
    container.appendChild(empty);
  }

  function createLevelBadge(level) {
    var text = level || 'Junior';
    var badge = document.createElement('span');
    var normalized = text.toLocaleLowerCase();
    var cls = 'level-badge';
    if (normalized === 'intern') cls += ' level-intern';
    else if (normalized === 'fresher') cls += ' level-fresher';
    else if (normalized === 'junior') cls += ' level-junior';
    badge.className = cls;
    badge.textContent = text;
    return badge;
  }

  function safeExternalUrl(url) {
    if (!url || typeof url !== 'string') return '#';
    var trimmed = url.trim();
    if (/^https?:\/\//i.test(trimmed) || trimmed.charAt(0) === '/') return trimmed;
    return '#';
  }

  function formatPriorityBadge(weightVal, totalWeight) {
    var pct = totalWeight > 0 ? Math.round((weightVal / totalWeight) * 100) : 0;
    var badge = document.createElement('span');
    if (pct >= 28) {
      badge.className = 'badge priority-high';
      badge.textContent = 'Trọng tâm · ' + pct + '%';
    } else if (pct >= 18) {
      badge.className = 'badge priority-mid';
      badge.textContent = 'Quan trọng · ' + pct + '%';
    } else {
      badge.className = 'badge priority-low';
      badge.textContent = 'Bổ trợ · ' + pct + '%';
    }
    return badge;
  }

  function syncResetButton() {
    var btn = $('resetFilters');
    if (!btn) return;
    var hasFilters = Boolean(
      ($('categoryFilter') && $('categoryFilter').value) ||
      ($('levelFilter') && $('levelFilter').value) ||
      ($('skillFilter') && $('skillFilter').value) ||
      ($('resourceSearch') && $('resourceSearch').value.trim()) ||
      currentView !== 'all'
    );
    btn.classList.toggle('hidden', !hasFilters);
  }

  function applyViewMode(view) {
    currentView = view || 'all';
    Array.prototype.slice.call(document.querySelectorAll('.view-tab')).forEach(function (tab) {
      var active = tab.getAttribute('data-view') === currentView;
      tab.classList.toggle('is-active', active);
      tab.setAttribute('aria-selected', String(active));
    });
    if ($('rolesSection')) $('rolesSection').classList.toggle('hidden', currentView !== 'all' && currentView !== 'roles');
    if ($('skillsSection')) $('skillsSection').classList.toggle('hidden', currentView !== 'all' && currentView !== 'skills');
    if ($('resourcesSection')) $('resourcesSection').classList.toggle('hidden', currentView !== 'all' && currentView !== 'resources');
    if ($('roleDetailSection') && currentView !== 'all' && currentView !== 'roles') {
      $('roleDetailSection').classList.add('hidden');
    }
    syncResetButton();
  }

  async function openRoleDetail(role) {
    selectedRoleId = role.id;
    renderRoles();

    var panel = $('roleDetailSection');
    var tbody = $('roleDetailSkillsBody');
    var statusText = $('roleDetailStatus');

    panel.classList.remove('hidden');
    $('roleDetailTitle').textContent = role.name;
    var levelBadge = createLevelBadge(role.level);
    var levelEl = $('roleDetailLevel');
    levelEl.className = levelBadge.className;
    levelEl.textContent = levelBadge.textContent;
    $('roleDetailCategory').textContent = role.category ? role.category.name : 'Chưa phân nhóm';
    $('roleDetailDesc').textContent = role.description || 'Chưa có mô tả chi tiết cho vị trí này.';
    $('roleAnalyzeLink').href = '/analysis?career_role_id=' + encodeURIComponent(role.id);
    statusText.textContent = 'Đang tải bộ kỹ năng yêu cầu...';
    tbody.replaceChildren();

    var requiredSkills = role.required_skills || [];
    try {
      requiredSkills = await getData('/api/v1/careers/' + role.id + '/skills');
    } catch (_err) {
      /* Dùng dữ liệu sẵn có trên thẻ nếu gọi chi tiết thất bại. */
    }

    statusText.textContent = 'Gồm ' + requiredSkills.length + ' kỹ năng tiêu chuẩn cho cấp độ ' + (role.level || 'Junior') + '.';

    if (!requiredSkills.length) {
      var trEmpty = document.createElement('tr');
      var tdEmpty = document.createElement('td');
      tdEmpty.colSpan = 4;
      tdEmpty.className = 'muted';
      tdEmpty.textContent = 'Vị trí này hiện chưa cập nhật danh sách kỹ năng.';
      trEmpty.appendChild(tdEmpty);
      tbody.appendChild(trEmpty);
      if ($('roleDetailResources')) $('roleDetailResources').classList.add('hidden');
      panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      return;
    }

    var totalWeight = requiredSkills.reduce(function (sum, item) {
      return sum + Number(item.weight || 1);
    }, 0);

    var roleSkillIds = new Set();

    requiredSkills.forEach(function (item) {
      if (item.skill && item.skill.id) roleSkillIds.add(String(item.skill.id));

      var tr = document.createElement('tr');

      var tdSkill = document.createElement('td');
      var strong = document.createElement('strong');
      strong.textContent = item.skill ? item.skill.name : 'Kỹ năng';
      tdSkill.appendChild(strong);
      if (item.skill && item.skill.description) {
        var desc = document.createElement('div');
        desc.className = 'resource-meta';
        desc.textContent = item.skill.description;
        tdSkill.appendChild(desc);
      }

      var tdReq = document.createElement('td');
      var reqBadge = document.createElement('span');
      var isReq = item.is_required !== false;
      reqBadge.className = 'req-badge ' + (isReq ? 'required' : 'optional');
      reqBadge.textContent = isReq ? 'Bắt buộc' : 'Khuyến khích';
      tdReq.appendChild(reqBadge);

      var tdLevel = document.createElement('td');
      var levelWrap = document.createElement('div');
      levelWrap.className = 'benchmark-wrap';
      var track = document.createElement('div');
      track.className = 'benchmark-track';
      var fill = document.createElement('div');
      fill.className = 'benchmark-fill';
      var levelVal = Number(item.required_level || 0);
      fill.style.width = Math.max(0, Math.min(100, (levelVal / 5) * 100)) + '%';
      track.appendChild(fill);
      var levelLabel = document.createElement('span');
      levelLabel.textContent = levelVal + ' / 5';
      levelWrap.append(track, levelLabel);
      tdLevel.appendChild(levelWrap);

      var tdPriority = document.createElement('td');
      var weightVal = Number(item.weight || 1);
      tdPriority.appendChild(formatPriorityBadge(weightVal, totalWeight));

      tr.append(tdSkill, tdReq, tdLevel, tdPriority);
      tbody.appendChild(tr);
    });

    var recBox = $('roleDetailResources');
    var recList = $('roleDetailResourcesList');
    if (recBox && recList) {
      recList.replaceChildren();
      var matchedResources = resources.filter(function (res) {
        return res.skill_id && roleSkillIds.has(String(res.skill_id));
      }).slice(0, 6);
      if (matchedResources.length) {
        matchedResources.forEach(function (res) {
          var chip = document.createElement('a');
          chip.className = 'detail-res-chip';
          chip.href = safeExternalUrl(res.url);
          chip.target = '_blank';
          chip.rel = 'noopener noreferrer';
          chip.textContent = res.title + (res.skill ? ' (' + res.skill.name + ')' : '') + ' ↗';
          recList.appendChild(chip);
        });
        recBox.classList.remove('hidden');
      } else {
        recBox.classList.add('hidden');
      }
    }

    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function renderRoles() {
    var container = $('roles');
    var selectedCategory = $('categoryFilter').value;
    var selectedLevel = $('levelFilter') ? $('levelFilter').value : '';
    var selectedSkill = $('skillFilter') ? $('skillFilter').value : '';
    var search = ($('resourceSearch') ? $('resourceSearch').value : '').trim().toLocaleLowerCase();

    var filtered = roles.filter(function (role) {
      var matchesCat = !selectedCategory || String(role.category_id) === selectedCategory;
      var matchesLevel = !selectedLevel || (role.level || '').toLocaleLowerCase() === selectedLevel.toLocaleLowerCase();
      var roleSkills = role.required_skills || [];
      var matchesSkill = !selectedSkill || roleSkills.some(function (rs) {
        return rs.skill && String(rs.skill.id) === selectedSkill;
      });
      var skillNames = roleSkills.map(function (rs) { return rs.skill ? rs.skill.name : ''; }).join(' ');
      var searchable = [role.name, role.description || '', role.level || '', role.category ? role.category.name : '', skillNames]
        .join(' ')
        .toLocaleLowerCase();
      var matchesSearch = !search || searchable.includes(search);
      return matchesCat && matchesLevel && matchesSkill && matchesSearch;
    });

    container.replaceChildren();
    $('roleCount').textContent = filtered.length + ' vị trí';
    syncResetButton();

    if (!filtered.length) {
      return addEmptyState(container, 'Chưa có vị trí nào khớp với bộ lọc hiện tại.');
    }

    filtered.forEach(function (role) {
      var card = document.createElement('article');
      card.className = 'explore-card' + (selectedRoleId === role.id ? ' is-selected' : '');

      var cardHeader = document.createElement('div');
      cardHeader.className = 'role-card-header';
      var heading = document.createElement('h3');
      heading.textContent = role.name;
      cardHeader.append(heading, createLevelBadge(role.level));

      var category = document.createElement('p');
      category.className = 'resource-meta';
      category.textContent = role.category ? role.category.name : 'Chưa phân nhóm';

      var description = document.createElement('p');
      description.textContent = role.description || 'Chưa có mô tả chi tiết.';

      var skillsList = document.createElement('ul');
      skillsList.className = 'pill-list';
      var allSkills = role.required_skills || [];
      var maxPreview = 4;
      allSkills.slice(0, maxPreview).forEach(function (item) {
        var pill = document.createElement('li');
        pill.className = 'pill';
        var skillTitle = item.skill ? item.skill.name : 'Kỹ năng';
        pill.textContent = skillTitle + ' · ' + item.required_level + '/5';
        skillsList.appendChild(pill);
      });
      if (allSkills.length > maxPreview) {
        var morePill = document.createElement('li');
        morePill.className = 'pill pill-more';
        morePill.textContent = '+' + (allSkills.length - maxPreview) + ' kỹ năng';
        skillsList.appendChild(morePill);
      }

      var actionRow = document.createElement('div');
      actionRow.className = 'card-actions-row';

      var detailBtn = document.createElement('button');
      detailBtn.type = 'button';
      detailBtn.className = 'secondary small';
      detailBtn.textContent = 'Xem yêu cầu kỹ năng';
      detailBtn.addEventListener('click', function () { openRoleDetail(role); });

      var analyzeLink = document.createElement('a');
      analyzeLink.className = 'card-link-inline';
      analyzeLink.href = '/analysis?career_role_id=' + encodeURIComponent(role.id);
      analyzeLink.textContent = 'Phân tích →';

      actionRow.append(detailBtn, analyzeLink);

      card.append(cardHeader, category, description);
      if (skillsList.childElementCount) card.appendChild(skillsList);
      card.appendChild(actionRow);
      container.appendChild(card);
    });
  }

  function renderSkills() {
    var container = $('skills');
    var search = $('resourceSearch').value.trim().toLocaleLowerCase();
    var selectedSkill = $('skillFilter') ? $('skillFilter').value : '';

    var resourceCounts = {};
    resources.forEach(function (r) {
      if (r.skill_id) {
        var key = String(r.skill_id);
        resourceCounts[key] = (resourceCounts[key] || 0) + 1;
      }
    });

    var filtered = skills.filter(function (skill) {
      var matchesSelected = !selectedSkill || String(skill.id) === selectedSkill;
      var matchesSearch = !search || (skill.name + ' ' + (skill.description || '')).toLocaleLowerCase().includes(search);
      return matchesSelected && matchesSearch;
    });

    container.replaceChildren();
    $('skillCount').textContent = filtered.length + ' kỹ năng';
    syncResetButton();

    if (!filtered.length) return addEmptyState(container, 'Không tìm thấy kỹ năng phù hợp.');

    filtered.forEach(function (skill) {
      var card = document.createElement('article');
      card.className = 'explore-card is-clickable';
      card.tabIndex = 0;
      card.setAttribute('role', 'button');
      card.setAttribute('aria-label', 'Lọc theo kỹ năng ' + skill.name);

      var heading = document.createElement('h3');
      heading.textContent = skill.name;

      var description = document.createElement('p');
      description.textContent = skill.description || 'Kỹ năng chuyên môn trong lộ trình nghề nghiệp.';

      var footer = document.createElement('div');
      footer.className = 'skill-card-footer';
      var cnt = resourceCounts[String(skill.id)] || 0;
      footer.textContent = cnt > 0 ? (cnt + ' tài nguyên học tập →') : 'Lọc vị trí liên quan →';

      var selectThisSkill = function () {
        $('skillFilter').value = String(skill.id);
        if (currentView === 'skills') {
          applyViewMode('all');
        }
        renderRoles();
        renderSkills();
        renderResources();
        if (cnt > 0 && $('resourcesSection')) {
          $('resourcesSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else if ($('rolesSection')) {
          $('rolesSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      };

      card.addEventListener('click', selectThisSkill);
      card.addEventListener('keydown', function (event) {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          selectThisSkill();
        }
      });

      card.append(heading, description, footer);
      container.appendChild(card);
    });
  }

  function renderResources() {
    var container = $('resources');
    var search = $('resourceSearch').value.trim().toLocaleLowerCase();
    var selectedSkill = $('skillFilter').value;

    var filtered = resources.filter(function (resource) {
      var matchesSkill = !selectedSkill || String(resource.skill_id) === selectedSkill;
      var skillName = resource.skill ? resource.skill.name : '';
      var searchable = (resource.title + ' ' + resource.provider + ' ' + skillName + ' ' + (resource.description || '')).toLocaleLowerCase();
      return matchesSkill && (!search || searchable.includes(search));
    });

    container.replaceChildren();
    $('resourceCount').textContent = filtered.length + ' tài nguyên';
    syncResetButton();

    if (!filtered.length) return addEmptyState(container, 'Không tìm thấy tài nguyên phù hợp.');

    filtered.forEach(function (resource) {
      var card = document.createElement('article');
      card.className = 'explore-card';

      var tagsRow = document.createElement('div');
      tagsRow.className = 'resource-tags';

      var typeBadge = document.createElement('span');
      typeBadge.className = 'badge badge-info';
      typeBadge.textContent = RESOURCE_TYPE_LABELS[resource.resource_type] || 'Tài nguyên';
      tagsRow.appendChild(typeBadge);

      if (resource.skill && resource.skill.name) {
        var skillBadge = document.createElement('span');
        skillBadge.className = 'badge badge-muted';
        skillBadge.textContent = resource.skill.name;
        tagsRow.appendChild(skillBadge);
      }

      var priceBadge = document.createElement('span');
      priceBadge.className = 'badge ' + (resource.is_free ? 'badge-ok' : 'badge-warn');
      priceBadge.textContent = resource.is_free ? 'Miễn phí' : 'Có phí';
      tagsRow.appendChild(priceBadge);

      var heading = document.createElement('h3');
      heading.textContent = resource.title;

      var meta = document.createElement('p');
      meta.className = 'resource-meta';
      meta.textContent = 'Nguồn: ' + (resource.provider || 'Đang cập nhật');

      var description = document.createElement('p');
      description.textContent = resource.description || '';

      var link = document.createElement('a');
      link.className = 'resource-open-link';
      link.href = safeExternalUrl(resource.url);
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = 'Mở tài nguyên học tập ↗';

      card.append(tagsRow, heading, meta, description, link);
      container.appendChild(card);
    });
  }

  function populateFilters(categoriesData, rolesData, skillsData) {
    var catFilter = $('categoryFilter');
    if (catFilter) {
      catFilter.replaceChildren();
      var optAllCat = document.createElement('option');
      optAllCat.value = '';
      optAllCat.textContent = 'Tất cả nhóm nghề';
      catFilter.appendChild(optAllCat);
      (categoriesData || []).forEach(function (category) {
        var option = document.createElement('option');
        option.value = String(category.id);
        option.textContent = category.name;
        catFilter.appendChild(option);
      });
    }

    var levelFilter = $('levelFilter');
    if (levelFilter) {
      var knownLevels = new Set(Array.from(levelFilter.options).map(function (o) { return o.value.toLocaleLowerCase(); }));
      (rolesData || []).forEach(function (role) {
        if (role.level && !knownLevels.has(role.level.toLocaleLowerCase())) {
          knownLevels.add(role.level.toLocaleLowerCase());
          var opt = document.createElement('option');
          opt.value = role.level;
          opt.textContent = role.level;
          levelFilter.appendChild(opt);
        }
      });
    }

    var skillFilter = $('skillFilter');
    if (skillFilter) {
      skillFilter.replaceChildren();
      var optAllSkill = document.createElement('option');
      optAllSkill.value = '';
      optAllSkill.textContent = 'Tất cả kỹ năng';
      skillFilter.appendChild(optAllSkill);
      (skillsData || []).forEach(function (skill) {
        var option = document.createElement('option');
        option.value = String(skill.id);
        option.textContent = skill.name;
        skillFilter.appendChild(option);
      });
    }
  }

  async function initialize() {
    // 1. Nạp sẵn bộ danh mục chuẩn để giao diện luôn hiển thị đầy đủ, đẹp mắt ngay cả khi mở file trực tiếp
    roles = DEFAULT_ROLES.slice();
    skills = DEFAULT_SKILLS.slice();
    resources = DEFAULT_RESOURCES.slice();
    populateFilters(DEFAULT_CATEGORIES, roles, skills);
    renderRoles();
    renderSkills();
    renderResources();
    setLoading(false);

    // 2. Đồng bộ ngầm với máy chủ backend nếu dịch vụ đang chạy
    try {
      var results = await Promise.all([
        getData('/api/v1/catalog/categories'),
        getData('/api/v1/careers'),
        getData('/api/v1/catalog/skills'),
        getData('/api/v1/catalog/resources')
      ]);
      if (Array.isArray(results[1]) && results[1].length) roles = results[1];
      if (Array.isArray(results[2]) && results[2].length) skills = results[2];
      if (Array.isArray(results[3]) && results[3].length) resources = results[3];
      populateFilters(results[0], roles, skills);
      renderRoles();
      renderSkills();
      renderResources();
    } catch (_offlineOrDirectFileOpen) {
      // Khi mở trực tiếp không qua server, dữ liệu chuẩn vẫn hiển thị trọn vẹn
    }
  }

  $('categoryFilter').addEventListener('change', renderRoles);
  if ($('levelFilter')) $('levelFilter').addEventListener('change', renderRoles);
  if ($('closeRoleDetail')) {
    $('closeRoleDetail').addEventListener('click', function () {
      selectedRoleId = null;
      $('roleDetailSection').classList.add('hidden');
      renderRoles();
    });
  }
  $('skillFilter').addEventListener('change', function () {
    renderRoles();
    renderSkills();
    renderResources();
  });
  $('resourceSearch').addEventListener('input', function () {
    renderRoles();
    renderSkills();
    renderResources();
  });

  Array.prototype.slice.call(document.querySelectorAll('.view-tab')).forEach(function (tab) {
    tab.addEventListener('click', function () {
      applyViewMode(tab.getAttribute('data-view'));
    });
  });

  if ($('resetFilters')) {
    $('resetFilters').addEventListener('click', function () {
      $('categoryFilter').value = '';
      if ($('levelFilter')) $('levelFilter').value = '';
      $('skillFilter').value = '';
      $('resourceSearch').value = '';
      applyViewMode('all');
      renderRoles();
      renderSkills();
      renderResources();
    });
  }

  initialize();
})();
