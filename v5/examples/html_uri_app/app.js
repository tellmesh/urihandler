import { createUriRuntime } from './uri-runtime.js';

const state = {
  led: 'off',
  logs: [],
  portalText: '',
};

function appendLog(event, detail = {}) {
  state.logs.unshift({
    at: new Date().toLocaleTimeString(),
    event,
    detail,
  });
  state.logs = state.logs.slice(0, 12);
}

function pickPortalText(url) {
  if (url.includes('reports')) return 'supplier portal monthly csv export ready';
  if (url.includes('zus')) return 'zus form preview ok';
  if (url.includes('transfer')) return 'bank batch transfer draft ok, waiting before 2fa';
  return 'page ok';
}

function readPath(object, path) {
  return String(path).split('.').reduce((value, key) => value?.[key], object);
}

const refs = {
  'devices.ledSet': ({ translation, payload }) => {
    state.led = translation.args[0] || 'on';
    appendLog('device.led.set', { state: state.led, payload });
    return { ok: true, target: translation.target, state: state.led, payload };
  },
  'devices.telemetryLatest': ({ translation }) => ({
    ok: true,
    target: translation.target,
    telemetry: {
      led: state.led,
      temperature: 22.4,
      rssi: -48,
    },
  }),
  'logs.write': ({ payload }) => {
    appendLog(payload.event || 'frontend.event', payload.detail || {});
    return { ok: true, written: true };
  },
  'assertions.contains': ({ payload }) => {
    const actual = String(payload.actual || '');
    const expected = String(payload.expected || '');
    return {
      ok: actual.toLowerCase().includes(expected.toLowerCase()),
      actual,
      expected,
    };
  },
};

const adapters = {
  'local-function': async ({ entry, translation, payload }) => {
    const fn = refs[entry.ref];
    if (!fn) throw new Error(`Missing ref: ${entry.ref}`);
    return fn({ entry, translation, payload });
  },
  fetch: async ({ entry, translation, payload, descriptor }) => {
    const method = entry.config.method || 'POST';
    appendLog('http.fetch', { method: entry.config.method, url: entry.config.url, payload });
    const response = await fetch(entry.config.url, {
      method,
      headers: method === 'GET' ? undefined : { 'Content-Type': 'application/json' },
      body: method === 'GET' ? undefined : JSON.stringify({ uri: descriptor.raw, target: translation.target, args: translation.args, ...payload }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
    return result;
  },
  'backend-dispatch': async ({ entry, descriptor, payload }) => {
    const response = await fetch(entry.config.url || '/api/dispatch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ uri: descriptor.raw, payload }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
    appendLog('backend.dispatch', { uri: descriptor.raw, ok: result.ok });
    return result;
  },
  'mqtt-publish': async ({ entry, translation, payload }) => {
    const topic = [entry.config.topicPrefix, translation.target, ...translation.args].filter(Boolean).join('/');
    appendLog('mqtt.publish', { topic, payload });
    return { ok: true, simulated: true, type: 'mqtt', topic, payload };
  },
  'shell-template': async ({ entry, translation }) => {
    const command = entry.config.template.replace(/\{(\d+)\}/g, (_, index) => translation.args[Number(index)] || '');
    appendLog('shell.template', { command });
    return { ok: true, simulated: true, type: 'shell', command };
  },
  'browser-open': async ({ payload }) => {
    state.portalText = pickPortalText(payload.url || '');
    appendLog('browser.open', { url: payload.url });
    return { ok: true, url: payload.url, text: state.portalText };
  },
  'dom-read': async () => {
    appendLog('dom.read', { bytes: state.portalText.length });
    return { ok: true, text: state.portalText };
  },
  'uri-flow': async ({ entry, dispatch }) => {
    const results = {};
    const steps = [];
    for (const step of entry.config.steps || []) {
      const payload = { ...(step.payload || {}) };
      if (payload.actual_from) payload.actual = readPath(results, payload.actual_from);
      const result = await dispatch(step.uri, payload);
      results[step.id] = result;
      steps.push({ id: step.id, uri: step.uri, result });
      if (result.ok === false) break;
    }
    appendLog('workflow.run', { workflow: entry.uri, steps: steps.length });
    return { ok: steps.every((step) => step.result.ok !== false), type: 'workflow', steps };
  },
};

const outputEl = document.querySelector('#output');
const logEl = document.querySelector('#logs');
const stateEl = document.querySelector('#state');
const routeCountEl = document.querySelector('#route-count');

const bindingDocument = await fetch('./bindings.json').then((response) => response.json());
const runtime = createUriRuntime({ bindings: bindingDocument, adapters, refs, state });
window.uriApp = runtime;

routeCountEl.textContent = Object.keys(runtime.routes).length;
render();

document.addEventListener('click', async (event) => {
  const target = event.target.closest('[data-uri], a[href^="#"]');
  if (!target) return;
  const href = target.getAttribute('href') || '';
  const uri = target.dataset.uri || decodeURIComponent(href.slice(1));
  if (!uri.includes('://')) return;
  event.preventDefault();
  const payload = target.dataset.payload ? JSON.parse(target.dataset.payload) : { source: 'html-uri-app' };
  await run(uri, payload);
});

async function run(uri, payload) {
  try {
    const result = await runtime.dispatch(uri, payload);
    if (!uri.startsWith('log://')) {
      await runtime.dispatch('log://frontend/session/write/event', {
        event: 'frontend.dispatch',
        detail: { uri, ok: result.ok !== false },
      });
    }
    outputEl.textContent = JSON.stringify({ uri, result }, null, 2);
  } catch (error) {
    outputEl.textContent = JSON.stringify({ uri, error: error.message }, null, 2);
  }
  render();
}

function render() {
  stateEl.textContent = JSON.stringify({ led: state.led, portalText: state.portalText }, null, 2);
  logEl.innerHTML = state.logs
    .map((item) => `<li><strong>${item.at}</strong><span>${item.event}</span><code>${escapeHtml(JSON.stringify(item.detail))}</code></li>`)
    .join('');
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  })[char]);
}
