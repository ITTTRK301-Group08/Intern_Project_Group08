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

  function renderRoles() {
    const container = $('roles');
    const selectedCategory = $('categoryFilter').value;
    const filtered = roles.filter((role) => !selectedCategory || String(role.category_id) === selectedCategory);
    container.replaceChildren();
    $('roleCount').textContent = filtered.length + ' vị trí';
    if (!filtered.length) return addEmptyState(container, 'Chưa có vị trí phù hợp với bộ lọc.');

    filtered.forEach((role) => {
      const card = document.createElement('article');
      card.className = 'explore-card';
      const heading = document.createElement('h3');
      heading.textContent = role.name;
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
        pill.textContent = item.skill.name + ' · mức ' + item.required_level + '/5';
        skillsList.appendChild(pill);
      });
      card.append(heading, category, description);
      if (skillsList.childElementCount) card.appendChild(skillsList);
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
        getData('/api/v1/catalog/roles'),
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
  $('skillFilter').addEventListener('change', renderResources);
  $('resourceSearch').addEventListener('input', () => {
    renderSkills();
    renderResources();
  });
  initialize();
})();
