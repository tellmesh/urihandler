const state = {
  routes: [],
  selected: null,
  logs: [],
};

const els = {
  actions: document.querySelector('#actions'),
  execute: document.querySelector('#execute-toggle'),
  shell: document.querySelector('#shell-toggle'),
  form: document.querySelector('#input-form'),
  logs: document.querySelector('#logs'),
  output: document.querySelector('#output'),
  routeCount: document.querySelector('#route-count'),
  run: document.querySelector('#run-button'),
  mcpTools: document.querySelector('#mcp-tools-btn'),
  a2aCard: document.querySelector('#a2a-card-btn'),
  toolList: document.querySelector('#tool-list'),
  discover: document.querySelector('#discover'),
};

const routeResponse = await fetch('./api/routes').then((response) => response.json());
state.routes = routeResponse.routes;
state.selected = state.routes[0] || null;
els.routeCount.textContent = state.routes.length;

renderActions();
renderForm();
await refreshLogs();

els.actions.addEventListener('click', (event) => {
  const button = event.target.closest('[data-uri]');
  if (!button) return;
  state.selected = state.routes.find((route) => route.uri === button.dataset.uri);
  renderActions();
  renderForm();
});

els.run.addEventListener('click', async () => {
  if (!state.selected) return;
  const result = await fetch('./api/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      uri: state.selected.uri,
      payload: payloadFromForm(),
      execute: els.execute.checked,
      allowShell: els.shell.checked,
    }),
  }).then((response) => response.json());
  els.output.textContent = JSON.stringify(result, null, 2);
  await refreshLogs();
});

function schemaFor(route) {
  return route?.config?.inputSchema || { type: 'object', properties: {} };
}

function payloadDefaults(route) {
  return route?.meta?.payload || {};
}

function renderActions() {
  els.actions.innerHTML = state.routes.map((route) => `
    <button type="button" class="action ${classFor(route)} ${route.uri === state.selected?.uri ? 'active' : ''}" data-uri="${escapeHtml(route.uri)}">
      <span>${escapeHtml(iconFor(route))}</span>
      <strong>${escapeHtml(route.meta?.label || route.uri)}</strong>
      <code>${escapeHtml(route.uri)}</code>
    </button>
  `).join('');
}

function renderForm() {
  const route = state.selected;
  const schema = schemaFor(route);
  const properties = schema.properties || {};
  const required = new Set(schema.required || []);
  const defaults = payloadDefaults(route);
  els.form.innerHTML = Object.entries(properties).map(([name, field]) => {
    const value = defaults[name] ?? field.default ?? '';
    const inputType = field.type === 'integer' || field.type === 'number' ? 'number' : 'text';
    return `
      <label class="field">
        <span>${escapeHtml(name)}${required.has(name) ? ' *' : ''}</span>
        <input name="${escapeHtml(name)}" type="${inputType}" value="${escapeHtml(value)}" data-type="${escapeHtml(field.type || 'string')}">
      </label>
    `;
  }).join('') || '<p class="empty">No input</p>';
}

function payloadFromForm() {
  const payload = {};
  for (const input of els.form.querySelectorAll('input[name]')) {
    const value = input.value;
    if (value === '') continue;
    if (input.dataset.type === 'integer') payload[input.name] = Number.parseInt(value, 10);
    else if (input.dataset.type === 'number') payload[input.name] = Number.parseFloat(value);
    else payload[input.name] = value;
  }
  return payload;
}

async function refreshLogs() {
  const data = await fetch('./api/logs').then((response) => response.json());
  state.logs = data.logs || [];
  els.logs.innerHTML = state.logs.map((item) => `
    <li>
      <strong>${escapeHtml(item.at || '')}</strong>
      <span>${escapeHtml(item.event || '')}</span>
      <code>${escapeHtml(JSON.stringify(item.detail || {}))}</code>
    </li>
  `).join('');
}

els.mcpTools.addEventListener('click', async () => {
  const manifest = await fetch('./api/mcp/tools').then((response) => response.json());
  els.discover.textContent = JSON.stringify(manifest, null, 2);
  renderToolList(manifest.tools || []);
});

els.a2aCard.addEventListener('click', async () => {
  const card = await fetch('./api/a2a/card').then((response) => response.json());
  els.discover.textContent = JSON.stringify(card, null, 2);
  renderToolList((card.skills || []).map((skill) => ({ name: skill.id })));
});

function renderToolList(tools) {
  els.toolList.innerHTML = tools.map((tool) =>
    `<button type="button" class="tool" data-tool="${escapeHtml(tool.name)}">${escapeHtml(tool.name)}</button>`,
  ).join('');
}

els.toolList.addEventListener('click', async (event) => {
  const button = event.target.closest('[data-tool]');
  if (!button) return;
  const result = await fetch('./api/mcp/call', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: button.dataset.tool, arguments: {}, execute: els.execute.checked, allowShell: els.shell.checked }),
  }).then((response) => response.json());
  els.output.textContent = JSON.stringify(result, null, 2);
  await refreshLogs();
});

function classFor(route) {
  return String(route.uri).split('://')[0];
}

function iconFor(route) {
  const key = classFor(route);
  return {
    media: 'M',
    package: 'P',
    say: 'A',
    shell: 'S',
  }[key] || key.slice(0, 1).toUpperCase();
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  })[char]);
}
