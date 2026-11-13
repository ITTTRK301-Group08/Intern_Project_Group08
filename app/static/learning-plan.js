(function () {
  const TOKEN_KEY = 'acm_access_token';
  const $ = (id) => document.getElementById(id);
  const savedToken = localStorage.getItem(TOKEN_KEY);
  if (savedToken) $('token').value = savedToken;

  function setMessage(message, isError) {
    $('message').textContent = message || '';
    $('message').className = 'status' + (isError ? ' error' : '');
  }

  async function api(path, options) {
    const token = $('token').value.trim();
    if (!token) throw new Error('Vui lòng nhập JWT access token.');
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

  function statusLabel(status) {
    return { active: 'Đang học', completed: 'Hoàn thành', archived: 'Đã lưu trữ' }[status] || status;
  }

  function makeButton(text, handler, secondary) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = text;
    if (secondary) button.className = 'secondary';
    button.onclick = handler;
    return button;
  }

  function renderPlan(plan) {
    const card = document.createElement('section');
    card.className = 'card';
    const header = document.createElement('div');
    header.className = 'plan-header';
    const title = document.createElement('h2');
    title.textContent = plan.title + ' (#' + plan.id + ')';
    const status = document.createElement('span');
    status.className = 'badge';
    status.textContent = statusLabel(plan.status);
    header.append(title, status);
    card.append(header);

    const actions = document.createElement('div');
    actions.className = 'plan-actions';
    [
      ['Đang học', 'active'],
      ['Hoàn thành', 'completed'],
      ['Lưu trữ', 'archived']
    ].forEach(([label, value]) => {
      if (value !== plan.status) {
        actions.append(makeButton(label, async () => {
          try {
            await api('/api/v1/learning-plans/' + plan.id + '/status', {
              method: 'PATCH',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ status: value })
            });
            await loadPlans();
          } catch (error) {
            setMessage(error.message, true);
          }
        }, true));
      }
    });
    card.append(actions);

    const weeks = new Map();
    plan.items.forEach((item) => {
      if (!weeks.has(item.week_number)) weeks.set(item.week_number, []);
      weeks.get(item.week_number).push(item);
    });
    [...weeks.entries()].sort((a, b) => a[0] - b[0]).forEach(([week, items]) => {
      const section = document.createElement('section');
      section.className = 'week';
      const heading = document.createElement('h3');
      heading.textContent = 'Tuần ' + week;
      section.append(heading);
      items.forEach((item) => {
        const row = document.createElement('div');
        row.className = 'item';
        const label = document.createElement('label');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = item.is_completed;
        checkbox.onchange = async () => {
          checkbox.disabled = true;
          try {
            await api('/api/v1/learning-plans/' + plan.id + '/items/' + item.id, {
              method: 'PATCH',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ is_completed: checkbox.checked })
            });
            await loadPlans();
          } catch (error) {
            checkbox.checked = item.is_completed;
            checkbox.disabled = false;
            setMessage(error.message, true);
          }
        };
        const task = document.createElement('span');
        task.textContent = item.task_description;
        label.append(checkbox, task);
        row.append(label);
        if (item.completed_at) {
          const date = document.createElement('span');
          date.className = 'muted small';
          date.textContent = 'Hoàn thành: ' + new Date(item.completed_at).toLocaleString('vi-VN');
          row.append(date);
        }
        if (item.resource_url) {
          const resource = document.createElement('a');
          resource.href = item.resource_url;
          resource.target = '_blank';
          resource.rel = 'noopener noreferrer';
          resource.textContent = item.resource_title || 'Tài liệu học';
          row.append(resource);
        }
        section.append(row);
      });
      card.append(section);
    });
    return card;
  }

  async function loadPlans() {
    $('token').value = $('token').value.trim();
    if ($('token').value) localStorage.setItem(TOKEN_KEY, $('token').value);
    $('plans').replaceChildren();
    setMessage('Đang tải lộ trình...', false);
    try {
      const plans = await api('/api/v1/learning-plans');
      if (!plans.length) {
        const empty = document.createElement('div');
        empty.className = 'empty muted';
        empty.textContent = 'Tài khoản chưa có lộ trình học tập.';
        $('plans').append(empty);
      } else {
        const details = await Promise.all(
          plans.map((plan) => api('/api/v1/learning-plans/' + plan.id))
        );
        details.forEach((plan) => $('plans').append(renderPlan(plan)));
      }
      setMessage('', false);
    } catch (error) {
      setMessage(error.message, true);
    }
  }

  $('loadPlans').onclick = loadPlans;
  if (savedToken) loadPlans();
})();
