(function () {
  const $ = (id) => document.getElementById(id);
  const statusEl = $('status');
  let roles = [];
  let skills = [];
  let resources = [];

  function setStatus(message, isError) {
    statusEl.textContent = message || '';
    statusEl.className = 'status' + (isError ? ' error' : '');
  }

  async function getData(path) {
    const response = await fetch(path);
    if (!response.ok) throw new Error('Không tải được dữ liệu (' + response.status + ').');
    const body = await response.json();
    return body.data;
  }

  function addEmptyState(container, message) {
    const empty = document.createElement('p');
    empty.className = 'empty-state';
    empty.textContent = message;
    container.appendChild(empty);
  }

  function createLevelBadge(level) {
    const text = level || 'Junior';
    const badge = document.createElement('span');
    const normalized = text.toLocaleLowerCase();
    let cls = 'level-badge';
    if (normalized === 'intern') cls += ' level-intern';
    else if (normalized === 'fresher') cls += ' level-fresher';
    else if (normalized === 'junior') cls += ' level-junior';
    badge.className = cls;
    badge.textContent = text;
    return badge;
  }

  async function openRoleDetail(role) {
    const panel = $('roleDetailSection');
    const tbody = $('roleDetailSkillsBody');
    const statusText = $('roleDetailStatus');

    panel.classList.remove('hidden');
    $('roleDetailTitle').textContent = role.name;
    const levelBadge = createLevelBadge(role.level);
    const levelEl = $('roleDetailLevel');
    levelEl.className = levelBadge.className;
    levelEl.textContent = levelBadge.textContent;
    $('roleDetailCategory').textContent = role.category ? role.category.name : 'Chưa phân nhóm';
    $('roleDetailDesc').textContent = role.description || 'Chưa có mô tả chi tiết cho vị trí này.';
    $('roleAnalyzeLink').href = '/analysis?career_role_id=' + encodeURIComponent(role.id);
    statusText.textContent = 'Đang tải chi tiết bộ kỹ năng yêu cầu...';
    tbody.replaceChildren();

    let requiredSkills = role.required_skills || [];
    try {
      requiredSkills = await getData('/api/v1/careers/' + role.id + '/skills');
      statusText.textContent = 'Hiển thị ' + requiredSkills.length + ' kỹ năng yêu cầu (thang điểm 0–5 kèm trọng số).';
    } catch (_err) {
      statusText.textContent = 'Hiển thị ' + requiredSkills.length + ' kỹ năng yêu cầu.';
    }

    if (!requiredSkills.length) {
      const tr = document.createElement('tr');
      const td = document.createElement('td');
      td.colSpan = 5;
      td.className = 'muted';
      td.textContent = 'Vị trí này chưa cấu hình kỹ năng yêu cầu.';
      tr.appendChild(td);
      tbody.appendChild(tr);
      panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      return;
    }

    const totalWeight = requiredSkills.reduce((sum, item) => sum + Number(item.weight || 1), 0);

    requiredSkills.forEach((item, index) => {
      const tr = document.createElement('tr');

      const tdIndex = document.createElement('td');
      tdIndex.textContent = String(index + 1);

      const tdSkill = document.createElement('td');
      const strong = document.createElement('strong');
      strong.textContent = item.skill ? item.skill.name : 'Kỹ năng';
      tdSkill.appendChild(strong);
      if (item.skill && item.skill.description) {
        const desc = document.createElement('div');
        desc.className = 'resource-meta';
        desc.textContent = item.skill.description;
        tdSkill.appendChild(desc);
      }

      const tdReq = document.createElement('td');
      const reqBadge = document.createElement('span');
      const isReq = item.is_required !== false;
      reqBadge.className = 'req-badge ' + (isReq ? 'required' : 'optional');
      reqBadge.textContent = isReq ? 'Bắt buộc' : 'Khuyến khích';
      tdReq.appendChild(reqBadge);

      const tdLevel = document.createElement('td');
      const levelWrap = document.createElement('div');
      levelWrap.className = 'benchmark-wrap';
      const track = document.createElement('div');
      track.className = 'benchmark-track';
      const fill = document.createElement('div');
      fill.className = 'benchmark-fill';
      const levelVal = Number(item.required_level || 0);
      fill.style.width = Math.max(0, Math.min(100, (levelVal / 5) * 100)) + '%';
      track.appendChild(fill);
      const levelLabel = document.createElement('span');
      levelLabel.textContent = levelVal + ' / 5';
      levelWrap.append(track, levelLabel);
      tdLevel.appendChild(levelWrap);

      const tdWeight = document.createElement('td');
      const weightVal = Number(item.weight || 1);
      const pct = totalWeight > 0 ? Math.round((weightVal / totalWeight) * 100) : 0;
      tdWeight.textContent = weightVal.toFixed(2) + ' (' + pct + '%)';

      tr.append(tdIndex, tdSkill, tdReq, tdLevel, tdWeight);
      tbody.appendChild(tr);
    });

    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function renderRoles() {
    const container = $('roles');
    const selectedCategory = $('categoryFilter').value;
    const selectedLevel = $('levelFilter') ? $('levelFilter').value : '';
    const filtered = roles.filter((role) => {
      const matchesCat = !selectedCategory || String(role.category_id) === selectedCategory;
      const matchesLevel = !selectedLevel || (role.level || '').toLocaleLowerCase() === selectedLevel.toLocaleLowerCase();
      return matchesCat && matchesLevel;
    });
    container.replaceChildren();
    $('roleCount').textContent = filtered.length + ' vị trí';
    if (!filtered.length) return addEmptyState(container, 'Chưa có vị trí phù hợp với bộ lọc.');

    filtered.forEach((role) => {
      const card = document.createElement('article');
      card.className = 'explore-card';

      const cardHeader = document.createElement('div');
      cardHeader.className = 'role-card-header';
      const heading = document.createElement('h3');
      heading.textContent = role.name;
      cardHeader.append(heading, createLevelBadge(role.level));

      const category = document.createElement('p');
      category.className = 'resource-meta';
      category.textContent = role.category ? role.category.name : 'Chưa phân nhóm';

      const description = document.createElement('p');
      description.textContent = role.description || 'Chưa có mô tả.';

      const skillsList = document.createElement('ul');
      skillsList.className = 'pill-list';
      (role.required_skills || []).forEach((item) => {
        const pill = document.createElement('li');
        pill.className = 'pill';
        const weightNum = item.weight !== undefined ? Number(item.weight) : 1;
        const weight = Number.isFinite(weightNum) ? String(Number(weightNum.toFixed(2))) : '1';
        pill.textContent = item.skill.name + ' · mức ' + item.required_level + '/5 · w=' + weight;
        skillsList.appendChild(pill);
      });

      const detailBtn = document.createElement('button');
      detailBtn.type = 'button';
      detailBtn.className = 'secondary small role-detail-btn';
      detailBtn.textContent = 'Xem chi tiết kỹ năng & trọng số';
      detailBtn.addEventListener('click', () => openRoleDetail(role));

      card.append(cardHeader, category, description);
      if (skillsList.childElementCount) card.appendChild(skillsList);
      card.appendChild(detailBtn);
      container.appendChild(card);
    });
  }

  function renderSkills() {
    const container = $('skills');
    const search = $('resourceSearch').value.trim().toLocaleLowerCase();
    const filtered = skills.filter((skill) => !search || (skill.name + ' ' + (skill.description || '')).toLocaleLowerCase().includes(search));
    container.replaceChildren();
    $('skillCount').textContent = filtered.length + ' kỹ năng';
    if (!filtered.length) return addEmptyState(container, 'Không tìm thấy kỹ năng.');

    filtered.forEach((skill) => {
      const card = document.createElement('article');
      card.className = 'explore-card';
      const heading = document.createElement('h3');
      heading.textContent = skill.name;
      const description = document.createElement('p');
      description.textContent = skill.description || 'Chưa có mô tả.';
      card.append(heading, description);
      container.appendChild(card);
    });
  }

  function renderResources() {
    const container = $('resources');
    const search = $('resourceSearch').value.trim().toLocaleLowerCase();
    const selectedSkill = $('skillFilter').value;
    const filtered = resources.filter((resource) => {
      const matchesSkill = !selectedSkill || String(resource.skill_id) === selectedSkill;
      const searchable = (resource.title + ' ' + resource.provider + ' ' + (resource.description || '')).toLocaleLowerCase();
      return matchesSkill && (!search || searchable.includes(search));
    });
    container.replaceChildren();
    $('resourceCount').textContent = filtered.length + ' tài nguyên';
    if (!filtered.length) return addEmptyState(container, 'Không tìm thấy tài nguyên phù hợp.');

    filtered.forEach((resource) => {
      const card = document.createElement('article');
      card.className = 'explore-card';
      const heading = document.createElement('h3');
      heading.textContent = resource.title;
      const meta = document.createElement('p');
      meta.className = 'resource-meta';
      meta.textContent = [resource.provider, resource.skill ? resource.skill.name : '', resource.is_free ? 'Miễn phí' : 'Có phí'].filter(Boolean).join(' · ');
      const description = document.createElement('p');
      description.textContent = resource.description || '';
      const link = document.createElement('a');
      link.href = resource.url;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = 'Mở tài nguyên ↗';
      card.append(heading, meta, description, link);
      container.appendChild(card);
    });
  }

  async function initialize() {
    try {
      const [categories, roleData, skillData, resourceData] = await Promise.all([
        getData('/api/v1/catalog/categories'),
        getData('/api/v1/careers'),
        getData('/api/v1/catalog/skills'),
        getData('/api/v1/catalog/resources')
      ]);
      roles = roleData;
      skills = skillData;
      resources = resourceData;

      categories.forEach((category) => {
        const option = document.createElement('option');
        option.value = category.id;
        option.textContent = category.name;
        $('categoryFilter').appendChild(option);
      });

      const levelFilter = $('levelFilter');
      if (levelFilter) {
        const knownLevels = new Set(Array.from(levelFilter.options).map((o) => o.value.toLocaleLowerCase()));
        roles.forEach((role) => {
          if (role.level && !knownLevels.has(role.level.toLocaleLowerCase())) {
            knownLevels.add(role.level.toLocaleLowerCase());
            const opt = document.createElement('option');
            opt.value = role.level;
            opt.textContent = role.level;
            levelFilter.appendChild(opt);
          }
        });
      }

      skills.forEach((skill) => {
        const option = document.createElement('option');
        option.value = skill.id;
        option.textContent = skill.name;
        $('skillFilter').appendChild(option);
      });

      renderRoles();
      renderSkills();
      renderResources();
      setStatus('Đã tải dữ liệu nghề nghiệp, kỹ năng và tài nguyên học tập.');
    } catch (error) {
      setStatus(error.message || 'Không thể tải dữ liệu khám phá.', true);
    }
  }

  $('categoryFilter').addEventListener('change', renderRoles);
  if ($('levelFilter')) $('levelFilter').addEventListener('change', renderRoles);
  if ($('closeRoleDetail')) {
    $('closeRoleDetail').addEventListener('click', () => {
      $('roleDetailSection').classList.add('hidden');
    });
  }
  $('skillFilter').addEventListener('change', renderResources);
  $('resourceSearch').addEventListener('input', () => {
    renderSkills();
    renderResources();
  });
  initialize();
})();
