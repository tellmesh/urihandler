from __future__ import annotations

import html as _html
import json as _json


def docs_nodes_html(profiles: list) -> str:
    rows = []
    for profile in profiles:
        rows.append(
            "<tr>"
            f"<td id=\"{_html.escape(profile['id'])}\"><strong>{_html.escape(profile['label'])}</strong>"
            f"<br><code>{_html.escape(profile['id'])}</code></td>"
            f"<td>{_html.escape(profile['description'])}</td>"
            f"<td><code>{_html.escape(profile['transport'])}</code></td>"
            f"<td><code>{_html.escape(profile['runtime'])}</code></td>"
            f"<td>{_html.escape(', '.join(profile.get('routesHint') or []))}</td>"
            "</tr>"
        )
    return """<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <title>urirun node types</title>
  <style>
    body { font: 15px/1.45 system-ui, sans-serif; margin: 32px; max-width: 1180px; color: #e5e7eb; background: #0f172a; }
    a { color: #67e8f9; } code { color: #bae6fd; }
    table { border-collapse: collapse; width: 100%; margin-top: 18px; }
    th, td { border: 1px solid #334155; padding: 10px; vertical-align: top; }
    th { text-align: left; background: #111827; }
    .subtle { color: #94a3b8; }
  </style>
</head>
<body>
  <h1>Typy node w urirun</h1>
  <p class="subtle">To jest backendowe źródło prawdy używane przez dashboard, discovery i URI object registry.</p>
  <table>
    <thead><tr><th>Typ</th><th>Kiedy używać</th><th>Transport</th><th>Runtime</th><th>Typowe URI</th></tr></thead>
    <tbody>""" + "\n".join(rows) + """</tbody>
  </table>
  <h2>Zasada wyboru komponentu</h2>
  <p>Jeśli komponent żyje jako proces i ma port/status, zrób z niego <strong>service</strong>.
  Jeśli dostarcza ograniczoną zdolność URI, zrób <strong>connector</strong>.
  Jeśli jest żywym widokiem, zrób <strong>widget</strong>.
  Jeśli jest skończonym plikiem lub raportem, zrób <strong>artifact</strong>.</p>
  <p><a href="/">Powrót do dashboardu</a></p>
</body>
</html>"""


def service_widget_html(view: dict) -> str:
    target = str(view.get("target") or view.get("serviceId") or "service:phone-scanner")
    view_id = str(view.get("id") or "")
    refresh = int(view.get("refreshMs") or 1000)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_html.escape(str(view.get("title") or "urirun service view"))}</title>
  <style>
    :root {{ color-scheme: dark; --bg:#11100f; --panel:#181716; --panel2:#201f1d; --ink:#f4f1e9; --muted:#aaa49a; --line:#3c3934; --accent:#2dd4bf; --good:#34d399; --bad:#fb7185; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; padding:12px; background:var(--bg); color:var(--ink); font:14px/1.45 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
    .widget {{ display:grid; gap:10px; min-height:100vh; }}
    .card {{ display:grid; gap:8px; padding:12px; border:1px solid rgba(45,212,191,.3); border-radius:8px; background:rgba(45,212,191,.08); }}
    .head,.meta {{ display:flex; align-items:center; justify-content:space-between; gap:8px; flex-wrap:wrap; }}
    .pill {{ display:inline-flex; min-height:24px; align-items:center; padding:2px 8px; border-radius:999px; background:#25231f; color:var(--muted); }}
    .pill.accepted,.pill.running {{ color:var(--good); background:rgba(52,211,153,.14); }}
    .pill.failed,.pill.rejected,.pill.stopped {{ color:var(--bad); background:rgba(251,113,133,.16); }}
    .frames {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(96px,1fr)); gap:8px; }}
    .frame {{ display:grid; gap:4px; padding:6px; border:1px solid var(--line); border-radius:6px; background:var(--panel2); }}
    img {{ width:100%; aspect-ratio:4/3; object-fit:cover; border-radius:4px; background:#151412; }}
    a {{ color:var(--accent); }}
    pre {{ margin:0; padding:10px; overflow:auto; border:1px solid var(--line); border-radius:6px; background:#151412; color:var(--ink); }}
    .muted {{ color:var(--muted); }}
  </style>
</head>
<body>
  <main class="widget">
    <section class="card" id="view">loading...</section>
  </main>
  <script>
    const target = {_json.dumps(target)};
    const viewId = {_json.dumps(view_id)};
    const refreshMs = Math.max(500, Number({_json.dumps(refresh)}) || 1000);
    const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[ch]));
    const basename = (path) => String(path || '').split('/').filter(Boolean).pop() || String(path || '');
    const docLabel = (candidate) => {{
      const doc = candidate && candidate.detectedDocument ? candidate.detectedDocument : {{}};
      return [doc.type, doc.date, doc.contractor || doc.supplier || doc.category, doc.amount].filter(Boolean).join(' · ') || 'document candidate';
    }};
    function pickView(data) {{
      const views = data.views || [];
      return views.find((view) => view.id === viewId) || views.find((view) => view.target === target || view.serviceId === target) || null;
    }}
    function renderScanner(view) {{
      const streams = view.data && Array.isArray(view.data.streams) ? view.data.streams : [];
      return streams.map((stream) => {{
        const best = stream.best || {{}};
        const document = stream.document || {{}};
        const status = stream.status || view.status || 'running';
        const frames = stream.candidates || [];
        const link = document.path ? `<a href="${{esc(document.previewUrl || `/api/file?path=${{encodeURIComponent(document.path)}}`)}}" download>${{esc(basename(document.path))}}</a>` : '';
        return `<section class="card">
          <div class="head"><strong>${{esc(view.title || 'service view')}}</strong><span class="pill ${{esc(status)}}">${{esc(status)}}</span></div>
          <div class="meta"><span class="muted">${{esc(stream.seriesId || view.target || '')}}</span><span class="muted">${{esc(stream.updatedAt || view.updatedAt || '')}}</span></div>
          <strong>${{esc(docLabel(best))}}</strong>
          <div class="muted">${{esc(stream.count || 0)}} frame(s)</div>
          ${{link}}
          ${{frames.length ? `<div class="frames">${{frames.map((frame) => `<div class="frame">${{frame.previewUrl ? `<img src="${{esc(frame.previewUrl)}}" alt="${{esc(docLabel(frame))}}">` : ''}}<span class="muted">${{esc(docLabel(frame))}}</span></div>`).join('')}}</div>` : ''}}
          <details><summary>URI / JSON</summary><pre>${{esc(JSON.stringify(stream, null, 2))}}</pre></details>
        </section>`;
      }}).join('') || '<section class="card">no stream</section>';
    }}
    function render(view) {{
      if (!view) return '<section class="card"><div class="head"><strong>service view</strong><span class="pill stopped">stopped</span></div><div class="muted">no live data</div></section>';
      if (view.view === 'scanner-stream') return renderScanner(view);
      return `<section class="card"><div class="head"><strong>${{esc(view.title || view.id || 'service view')}}</strong><span class="pill ${{esc(view.status || 'running')}}">${{esc(view.status || view.kind || 'live')}}</span></div><pre>${{esc(JSON.stringify(view, null, 2))}}</pre></section>`;
    }}
    async function load() {{
      const res = await fetch('/api/services/live?limit=8', {{ cache: 'no-store' }});
      const data = await res.json();
      document.getElementById('view').outerHTML = `<div id="view">${{render(pickView(data))}}</div>`;
    }}
    load().catch((error) => {{ document.getElementById('view').textContent = error.message; }});
    setInterval(() => load().catch(() => {{}}), refreshMs);
  </script>
</body>
</html>"""


def service_widget_svg(view: dict, summary: dict, width: int = 720, height: int = 180) -> str:
    status = summary["status"]
    status_color = "#34d399" if status in {"accepted", "running"} else "#fb7185" if status in {"failed", "rejected", "stopped"} else "#aaa49a"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{_html.escape(summary['title'])}">
  <rect width="100%" height="100%" rx="8" fill="#11100f"/>
  <rect x="10" y="10" width="{width - 20}" height="{height - 20}" rx="8" fill="#13251f" stroke="#2dd4bf" stroke-opacity=".45"/>
  <text x="24" y="42" fill="#f4f1e9" font-family="system-ui, -apple-system, Segoe UI, sans-serif" font-size="18" font-weight="700">{_html.escape(summary['title'])}</text>
  <rect x="{width - 130}" y="24" width="100" height="28" rx="14" fill="{status_color}" fill-opacity=".16"/>
  <text x="{width - 80}" y="43" text-anchor="middle" fill="{status_color}" font-family="system-ui, -apple-system, Segoe UI, sans-serif" font-size="13">{_html.escape(status)}</text>
  <text x="24" y="78" fill="#f4f1e9" font-family="system-ui, -apple-system, Segoe UI, sans-serif" font-size="15">{_html.escape(summary['subtitle'])}</text>
  <text x="24" y="108" fill="#aaa49a" font-family="system-ui, -apple-system, Segoe UI, sans-serif" font-size="13">{_html.escape(summary['detail'])}</text>
  <text x="24" y="{height - 24}" fill="#aaa49a" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="11">{_html.escape(str(view.get('id') or view.get('target') or ''))}</text>
</svg>"""


INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>urirun host</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #11100f;
      --surface: #181716;
      --surface-2: #201f1d;
      --surface-3: #292724;
      --ink: #f4f1e9;
      --muted: #aaa49a;
      --line: #3c3934;
      --line-soft: #302d29;
      --accent: #2dd4bf;
      --accent-ink: #06221f;
      --warn: #fbbf24;
      --bad: #fb7185;
      --good: #34d399;
      --topbar: rgba(24, 23, 22, 0.94);
      --pill-bg: #25231f;
      --pill-ink: #ded8cc;
      --good-bg: rgba(52, 211, 153, .14);
      --bad-bg: rgba(251, 113, 133, .16);
      --warn-bg: rgba(251, 191, 36, .16);
      --user-bg: rgba(45, 212, 191, .10);
      --system-bg: #1c1b19;
      --code-bg: #151412;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font: 14px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--ink);
    }
    .topbar {
      position: sticky;
      top: 0;
      z-index: 5;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      min-height: 64px;
      padding: 12px 20px;
      border-bottom: 1px solid var(--line);
      background: var(--topbar);
      backdrop-filter: blur(10px);
    }
    h1, h2, h3, p { margin: 0; }
    h1 { font-size: 20px; font-weight: 750; letter-spacing: 0; }
    h2 { font-size: 16px; font-weight: 700; }
    .subtle { color: var(--muted); }
    .toolbar, .tabs, .actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    button, select, input, textarea {
      font: inherit;
      border: 1px solid var(--line);
      background: var(--surface);
      color: var(--ink);
      border-radius: 6px;
    }
    button {
      min-height: 36px;
      padding: 0 12px;
      cursor: pointer;
    }
    button.primary { background: var(--accent); border-color: var(--accent); color: var(--accent-ink); font-weight: 700; }
    button.danger { color: var(--bad); }
    button.active { border-color: var(--accent); box-shadow: inset 0 -2px 0 var(--accent); color: var(--accent); }
    button:disabled { opacity: .55; cursor: not-allowed; }
    ::placeholder { color: #7f786f; }
    a { color: var(--accent); }
    select, input { min-height: 36px; padding: 0 10px; }
    textarea {
      width: 100%;
      min-height: 108px;
      padding: 10px 12px;
      resize: vertical;
    }
    main {
      width: min(1440px, 100%);
      margin: 0 auto;
      padding: 18px 20px 84px;
    }
    .metrics {
      display: grid;
      grid-template-columns: repeat(5, minmax(120px, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }
    .metric {
      min-height: 76px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
    }
    .metric strong { display: block; font-size: 24px; line-height: 1.1; }
    .grid {
      display: grid;
      grid-template-columns: minmax(0, 1.25fr) minmax(320px, .75fr);
      gap: 14px;
      align-items: start;
    }
    body[data-view="chat"] .grid {
      grid-template-columns: minmax(0, 1fr);
      min-height: calc(100vh - 210px);
    }
    body[data-view="chat"] .grid > .stack:first-of-type {
      grid-column: 1 / -1;
      min-height: inherit;
    }
    body[data-view="chat"] .grid > aside.stack {
      display: none;
    }
    /* Nodes view goes full page width so the Nodes | URI Processes columns are roomy. */
    body[data-view="nodes"] .grid {
      grid-template-columns: minmax(0, 1fr);
    }
    body[data-view="nodes"] .grid > .stack:not(aside) {
      grid-column: 1 / -1;
    }
    body[data-view="nodes"] .grid > aside.stack {
      display: none;
    }
    /* Activity view is logs-only and full page width (its panels live in the aside). */
    body[data-view="activity"] .grid {
      grid-template-columns: minmax(0, 1fr);
    }
    body[data-view="activity"] .grid > .stack:not(aside) {
      display: none;
    }
    body[data-view="activity"] .grid > aside.stack {
      grid-column: 1 / -1;
      display: grid;
    }
    body[data-view="chat"] .chat-panel {
      min-height: inherit;
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
    }
    body[data-view="chat"] .chat-panel .panel-body,
    body[data-view="chat"] .chat-shell,
    body[data-view="chat"] .chat-main {
      min-height: 0;
      height: 100%;
    }
    body[data-view="chat"] .chat-result {
      max-height: none;
      min-height: 0;
    }
    .discovery-layout {
      grid-column: 1 / -1;
      display: grid;
      grid-template-columns: minmax(260px, .35fr) minmax(0, .65fr);
      gap: 14px;
      align-items: start;
    }
    .discovery-target {
      width: 100%;
      text-align: left;
      display: block;
      border: 1px solid var(--line);
      background: var(--surface-2);
      color: var(--text);
      border-radius: 8px;
      padding: 10px 12px;
      cursor: pointer;
    }
    .discovery-target.active {
      border-color: var(--accent);
      box-shadow: inset 3px 0 0 var(--accent);
      background: var(--surface);
    }
    .discovery-route-grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 8px;
    }
    .route-title {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }
    .panel {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      overflow: hidden;
    }
    .panel-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
    }
    .panel-body { padding: 12px 14px; }
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; min-width: 760px; }
    th, td { padding: 9px 8px; border-bottom: 1px solid var(--line-soft); text-align: left; vertical-align: top; }
    th { color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; }
    .status, .pill {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 0 8px;
      border-radius: 999px;
      background: var(--pill-bg);
      color: var(--pill-ink);
      white-space: nowrap;
    }
    .status.done, .pill.up { background: var(--good-bg); color: var(--good); }
    .status.blocked, .status.failed, .pill.down { background: var(--bad-bg); color: var(--bad); }
    .status.in_progress, .pill.running { background: var(--warn-bg); color: var(--warn); }
    .stack { display: grid; gap: 14px; }
    .list { display: grid; gap: 8px; }
    .chat-shell {
      display: grid;
      grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
      gap: 12px;
      min-height: 640px;
    }
    .contacts-panel {
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      gap: 8px;
      min-height: 0;
      padding-right: 12px;
      border-right: 1px solid var(--line-soft);
    }
    .contact-list {
      display: grid;
      align-content: start;
      gap: 8px;
      overflow: auto;
      min-height: 0;
    }
    .contact-card {
      display: grid;
      grid-template-columns: auto minmax(0, 1fr);
      gap: 8px;
      align-items: start;
      padding: 9px;
      border: 1px solid var(--line-soft);
      border-radius: 8px;
      background: var(--surface-2);
    }
	    .contact-card input { margin-top: 2px; min-height: 0; }
	    .contact-title { font-weight: 700; overflow-wrap: anywhere; }
	    .contact-meta { color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }
	    .contact-body { display: grid; gap: 5px; min-width: 0; }
	    .contact-actions {
	      display: flex;
	      flex-wrap: wrap;
	      gap: 6px;
	      padding-top: 2px;
	    }
	    .contact-actions button {
	      min-height: 30px;
	      padding: 0 9px;
	      font-size: 12px;
	    }
	    .chat-main {
      display: grid;
      grid-template-rows: auto minmax(0, 1fr) auto;
      gap: 10px;
      min-width: 0;
      min-height: 0;
    }
    .chat-toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }
    .chat-form { display: grid; gap: 10px; }
    .chat-composer {
      display: grid;
      gap: 10px;
      padding-top: 10px;
      border-top: 1px solid var(--line-soft);
    }
    .chat-options, .node-options {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }
    .check {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-height: 30px;
      color: var(--muted);
    }
    .check input { min-height: 0; }
    .chat-result {
      display: grid;
      gap: 8px;
      min-height: 360px;
      max-height: 620px;
      overflow: auto;
    }
    .stream-list {
      display: grid;
      gap: 8px;
    }
    .stream-card {
      display: grid;
      gap: 8px;
      padding: 10px;
      border: 1px solid rgba(45, 212, 191, .28);
      border-radius: 8px;
      background: rgba(45, 212, 191, .08);
    }
    .stream-head, .stream-meta {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
    .stream-frames {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(86px, 1fr));
      gap: 6px;
    }
    .stream-frame {
      display: grid;
      gap: 4px;
      min-width: 0;
      padding: 6px;
      border: 1px solid var(--line-soft);
      border-radius: 6px;
      background: var(--surface-2);
    }
    .stream-frame img {
      width: 100%;
      aspect-ratio: 4 / 3;
      object-fit: cover;
      border-radius: 4px;
      background: var(--code-bg);
    }
    .service-table-wrap {
      overflow: auto;
      border: 1px solid var(--line-soft);
      border-radius: 6px;
    }
    .service-table-wrap table {
      width: 100%;
      min-width: 0;
      border: 0;
      border-radius: 0;
    }
    .service-media {
      width: 100%;
      max-height: 520px;
      object-fit: contain;
      border: 1px solid var(--line-soft);
      border-radius: 6px;
      background: var(--code-bg);
    }
    .service-frame {
      width: 100%;
      height: min(68vh, 720px);
      border: 1px solid var(--line-soft);
      border-radius: 6px;
      background: var(--code-bg);
    }
    .service-form-preview {
      display: grid;
      gap: 8px;
      padding: 10px;
      border: 1px solid var(--line-soft);
      border-radius: 6px;
      background: var(--surface-2);
    }
    .service-graph {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 8px;
    }
    .artifact-layout, .widget-layout {
      grid-column: 1 / -1;
      display: grid;
      gap: 14px;
    }
    .nodes-layout {
      grid-column: 1 / -1;
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 14px;
      align-items: start;
    }
    .nodes-layout.hidden { display: none; }
    .node-row { cursor: pointer; }
    .node-row.node-row-active { border-color: var(--accent); background: var(--surface-3); }
    .node-kind-tabs { display: flex; flex-wrap: wrap; gap: 6px; margin: 6px 0; }
    .node-kind-tab { display: inline-flex; flex-direction: column; align-items: flex-start; gap: 1px; padding: 6px 10px; border: 1px solid var(--border, #334155); border-radius: 8px; background: var(--surface-2, #1e293b); cursor: pointer; font-size: .85rem; }
    .node-kind-tab .subtle { font-size: .68rem; }
    .node-kind-tab.active { border-color: var(--accent); background: var(--surface-3); }
    .node-kind-form { border: 1px solid var(--border, #334155); border-radius: 8px; padding: 10px; margin-top: 6px; }
    .phone-node-qr { text-align: center; margin: 8px 0; }
    .phone-node-qr img { width: 200px; height: 200px; background: #fff; padding: 6px; border-radius: 8px; }
    .pill.kind { background: rgba(56,189,248,.16); color: var(--accent, #38bdf8); text-transform: uppercase; font-size: .62rem; letter-spacing: .04em; }
    @media (max-width: 920px) { .nodes-layout { grid-template-columns: 1fr; } }
    .ticket-form-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
    }
    .ticket-form-grid .ticket-form-full { grid-column: 1 / -1; }
    .ticket-form-grid textarea { width: 100%; resize: vertical; }
    .qr-block { border-top: 1px solid var(--line-soft); padding-top: 6px; }
    .qr-block summary { cursor: pointer; }
    .qr-wrap { display: flex; align-items: center; gap: 10px; margin-top: 6px; flex-wrap: wrap; }
    .qr-img { width: 120px; height: 120px; image-rendering: pixelated; background: #fff; padding: 4px; border-radius: 6px; }
    .qr-img-lg { width: 260px; height: 260px; image-rendering: pixelated; background: #fff; padding: 8px; border-radius: 8px; }
    .qr-link { word-break: break-all; font-size: 12px; }
    .qr-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.6); display: grid; place-items: center; z-index: 1000; }
    .qr-overlay-card { background: var(--surface-2); border: 1px solid var(--line-soft); border-radius: 10px; padding: 16px; display: grid; gap: 10px; justify-items: center; max-width: 90vw; }
    .artifact-file-grid {
      display: grid;
      gap: 8px;
      overflow: auto;
    }
    .artifact-file-row {
      display: grid;
      grid-template-columns: 32px 280px minmax(220px, 1fr) minmax(180px, .65fr) minmax(150px, .45fr);
      gap: 10px;
      align-items: start;
      min-width: 1060px;
      padding: 8px;
      border: 1px solid var(--line-soft);
      border-radius: 8px;
      background: var(--surface-2);
    }
    .artifact-file-row.header {
      position: sticky;
      top: 0;
      z-index: 1;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      background: var(--surface-3);
    }
    .artifact-thumb {
      display: grid;
      place-items: center;
      width: 264px;
      height: 200px;
      overflow: hidden;
      border: 1px solid var(--line-soft);
      border-radius: 6px;
      background: var(--code-bg);
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
    }
    .artifact-thumb img {
      width: 100%;
      height: 100%;
      border: 0;
      object-fit: cover;
      background: var(--code-bg);
      pointer-events: none;
    }
    .artifact-thumb-pdf, .attachment-pdf-preview {
      align-content: center;
      gap: 8px;
      color: var(--text);
      background:
        linear-gradient(180deg, rgba(248, 250, 252, .08), rgba(15, 23, 42, .1)),
        var(--code-bg);
    }
    .artifact-thumb-pdf span, .attachment-pdf-preview span {
      font-size: 28px;
      font-weight: 800;
      letter-spacing: 0;
    }
    .artifact-thumb-pdf small, .attachment-pdf-preview small {
      color: var(--muted);
      text-transform: none;
    }
    .artifact-thumb-missing {
      color: var(--danger);
      border-style: dashed;
      text-transform: none;
    }
    .artifact-name {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }
    .artifact-actions {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
      margin-top: 4px;
    }
    .artifact-meta-line {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      color: var(--muted);
    }
    .widget-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 12px;
      align-items: start;
    }
    .widget-card {
      display: grid;
      gap: 8px;
      min-width: 0;
      align-content: start;
    }
    .widget-card > .stream-head,
    .widget-card > .subtle,
    .widget-card > .artifact-actions {
      padding: 0 2px;
    }
    .widget-preview {
      display: grid;
      gap: 8px;
      max-height: 720px;
      overflow: auto;
    }
    .message {
      display: grid;
      gap: 8px;
      padding: 10px;
      border: 1px solid var(--line-soft);
      border-radius: 8px;
      background: var(--system-bg);
    }
    .message.user { background: var(--user-bg); border-color: rgba(45, 212, 191, .32); }
    .message.system { background: var(--system-bg); }
    .message-head { display: flex; justify-content: space-between; gap: 10px; align-items: center; }
    .message-title { display: inline-flex; align-items: center; gap: 8px; min-width: 0; }
    .message-actions { display: inline-flex; align-items: center; gap: 8px; }
    .attachments {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 8px;
    }
    .attachment.attachment-widget {
      grid-column: 1 / -1;
    }
    .attachment {
      display: grid;
      gap: 6px;
      padding: 8px;
      border: 1px solid var(--line-soft);
      border-radius: 8px;
      background: var(--surface-2);
    }
    .attachment img {
      width: 100%;
      max-height: 420px;
      object-fit: contain;
      border: 1px solid var(--line-soft);
      border-radius: 6px;
      background: var(--code-bg);
    }
    .attachment iframe {
      width: 100%;
      height: 520px;
      border: 1px solid var(--line-soft);
      border-radius: 6px;
      background: var(--code-bg);
    }
    .attachment.attachment-pdf {
      grid-column: span 2;
    }
    .attachment-pdf-preview {
      display: grid;
      place-items: center;
      min-height: 260px;
      border: 1px solid var(--line-soft);
      border-radius: 6px;
    }
    .attachment.attachment-qr {
      max-width: 380px;
    }
    .attachment.attachment-qr img {
      max-height: 340px;
      image-rendering: pixelated;
    }
    @media (max-width: 760px) {
      .attachment.attachment-pdf { grid-column: auto; }
      .attachment iframe { height: 420px; }
    }
    pre {
      margin: 0;
      padding: 10px;
      border: 1px solid var(--line-soft);
      border-radius: 6px;
      background: var(--code-bg);
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }
    .item {
      display: grid;
      gap: 4px;
      padding: 10px;
      border: 1px solid var(--line-soft);
      border-radius: 8px;
      background: var(--surface-2);
    }
    .mono {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
      overflow-wrap: anywhere;
    }
    .bottom-nav {
      position: fixed;
      left: 0;
      right: 0;
      bottom: 0;
      z-index: 6;
      display: none;
      grid-template-columns: repeat(8, 1fr);
      border-top: 1px solid var(--line);
      background: var(--surface);
    }
    .bottom-nav button {
      border: 0;
      border-radius: 0;
      min-height: 56px;
      border-right: 1px solid var(--line);
    }
    .hidden { display: none !important; }
    body.chat-fullscreen { overflow: hidden; }
    body.chat-fullscreen .topbar,
    body.chat-fullscreen .metrics,
    body.chat-fullscreen aside,
    body.chat-fullscreen .bottom-nav { display: none; }
    body.chat-fullscreen main {
      width: 100%;
      height: 100vh;
      padding: 10px;
    }
    body.chat-fullscreen .grid { height: 100%; display: block; }
    body.chat-fullscreen .grid > .stack { height: 100%; display: block; }
    body.chat-fullscreen .chat-panel {
      height: 100%;
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
    }
    body.chat-fullscreen .chat-panel .panel-body,
    body.chat-fullscreen .chat-shell,
    body.chat-fullscreen .chat-main { height: 100%; min-height: 0; }
    body.chat-fullscreen .chat-shell { min-height: 0; }
    body.chat-fullscreen .chat-result {
      max-height: none;
      min-height: 0;
    }
    body.chat-fullscreen textarea { min-height: 86px; }
    @media (max-width: 920px) {
      .topbar { align-items: flex-start; flex-direction: column; }
      main { padding: 14px 12px 76px; }
      .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .grid { grid-template-columns: 1fr; }
      .discovery-layout { grid-template-columns: 1fr; }
      .chat-shell { grid-template-columns: 1fr; min-height: 0; }
      .contacts-panel { border-right: 0; border-bottom: 1px solid var(--line-soft); padding-right: 0; padding-bottom: 10px; }
      .contact-list { max-height: 260px; }
      .artifact-file-row {
        grid-template-columns: 32px 188px minmax(180px, 1fr) minmax(140px, .65fr) minmax(150px, .45fr);
        min-width: 850px;
      }
      .artifact-thumb { width: 180px; height: 136px; }
      .desktop-tabs { display: none; }
      .bottom-nav { display: grid; }
      table { min-width: 680px; }
    }
  </style>
</head>
<body>
  <header class="topbar">
    <div>
      <h1>urirun host</h1>
      <p class="subtle" id="contextLine">Loading...</p>
    </div>
    <div class="toolbar">
      <div class="tabs desktop-tabs">
        <button data-view="overview">Overview</button>
        <button data-view="chat">Chat</button>
        <button data-view="discovery">Discovery</button>
        <button data-view="artifacts">Artifacts</button>
        <button data-view="widgets">Widgets</button>
        <button data-view="twin">Digital Twin</button>
        <button data-view="tasks">Tasks</button>
        <button data-view="host">Host</button>
        <button data-view="nodes">Nodes</button>
        <button data-view="activity">Activity</button>
      </div>
      <button id="scannerBtn" type="button">Phone Scanner</button>
      <button id="phoneQrBtn" type="button" title="Pokaz QR tego widoku do otwarcia na telefonie" onclick="showViewQr()">Telefon (QR)</button>
      <span class="pill" id="activeTabPill">overview</span>
      <button class="primary" id="refreshBtn">Refresh</button>
    </div>
  </header>
  <main>
    <section class="metrics" id="metrics"></section>
    <section class="grid">
      <section class="discovery-layout view-block" data-section="discovery">
        <article class="panel">
          <div class="panel-head"><h2>URI Objects</h2><span class="subtle" id="discoveryCount"></span></div>
          <div class="panel-body"><div class="list" id="discoveryList"></div></div>
        </article>
        <article class="panel">
          <div class="panel-head">
            <div>
              <h2 id="discoveryRouteTitle">URI Registry</h2>
              <p class="subtle" id="discoveryRouteMeta"></p>
            </div>
            <span class="subtle" id="discoveryRouteCount"></span>
          </div>
          <div class="panel-body"><div class="list" id="discoveryRoutesList"></div></div>
        </article>
      </section>
      <section class="artifact-layout view-block" data-section="artifacts">
        <article class="panel">
          <div class="panel-head">
            <div>
              <h2>Artifacts</h2>
              <p class="subtle">File-style grid/table of generated documents, scans and previews.</p>
            </div>
            <div class="actions">
              <span class="subtle" id="artifactCount"></span>
              <span class="subtle" id="artifactSelectionSummary">0 selected</span>
              <button type="button" id="artifactSelectVisibleBtn">Select visible</button>
              <button type="button" id="artifactClearSelectionBtn">Clear</button>
              <button type="button" class="danger" id="artifactDeleteSelectedBtn">Delete selected</button>
              <button type="button" class="danger" id="artifactDeleteVisibleBtn">Delete visible</button>
              <button type="button" id="artifactDedupeRowsBtn">Dedupe rows</button>
              <button type="button" id="artifactCleanupOrphansBtn">Cleanup orphan JSON</button>
              <button type="button" id="documentReconcileBtn">Reconcile docs index</button>
              <button type="button" id="artifactCopyJsonBtn">Copy JSON</button>
              <button type="button" id="artifactRefreshBtn">Refresh files</button>
            </div>
          </div>
          <div class="panel-body"><div class="artifact-file-grid" id="artifactFileGrid"></div></div>
        </article>
      </section>
      <section class="widget-layout view-block" data-section="widgets">
        <article class="panel">
          <div class="panel-head">
            <div>
              <h2>Widgets</h2>
              <p class="subtle">Dashboard service previews and live views exposed by URI services.</p>
            </div>
            <div class="actions">
              <span class="subtle" id="widgetCount"></span>
              <button type="button" id="widgetRefreshBtn">Refresh widgets</button>
            </div>
          </div>
          <div class="panel-body"><div class="widget-grid" id="widgetGrid"></div></div>
        </article>
      </section>

      <section class="widget-layout view-block" data-section="twin" style="display: flex; flex-direction: column; height: 100%;">
        <div class="panel-head"><h2>Digital Twin Monitor</h2></div>
        <div class="panel-body" style="flex: 1; padding: 0;">
          <iframe src="/twin?source=live" title="Digital Twin Monitor" style="width:100%;height:100%;border:none;min-height:70vh;"></iframe>
        </div>
      </section>

      <section class="nodes-layout view-block" data-section="host">
        <article class="panel">
          <div class="panel-head">
            <div>
              <h2>Konfiguracja hosta</h2>
              <p class="subtle">Tożsamość, ścieżki i status lokalnego hosta urirun.</p>
            </div>
            <span class="pill" id="hostStatusPill"></span>
          </div>
          <div class="panel-body"><div class="list" id="hostConfigList"></div></div>
        </article>
        <article class="panel">
          <div class="panel-head"><h2>Możliwości hosta (URI)</h2><span class="subtle" id="hostRouteCount"></span></div>
          <div class="panel-body"><div class="list" id="hostRoutesList"></div></div>
        </article>
      </section>
      <section class="artifact-layout view-block" data-section="host">
        <article class="panel">
          <div class="panel-head">
            <div>
              <h2>Rozszerzenia URI (connectory)</h2>
              <p class="subtle">Dodaj connector ze \u017ar\u00f3d\u0142a i przetestuj, czy dzia\u0142a na ho\u015bcie lub wybranym w\u0119\u017ale.</p>
            </div>
            <span class="subtle" id="connectorInstallStatus"></span>
          </div>
          <div class="panel-body">
            <div class="ticket-form-grid">
              <label class="stack"><span class="subtle">\u0179r\u00f3d\u0142o</span>
                <select id="connectorSource" onchange="connectorSourceHint()">
                  <option value="pip">pip (PyPI)</option>
                  <option value="github">github repo</option>
                  <option value="local">lokalny folder</option>
                  <option value="npm">npm</option>
                  <option value="docker">docker image</option>
                  <option value="http">gotowe API (http)</option>
                </select></label>
              <label class="stack ticket-form-full"><span class="subtle" id="connectorSpecLabel">Pakiet / spec</span>
                <input id="connectorSpec" placeholder="urirun-connector-hash"></label>
            </div>
            <div class="artifact-actions" style="margin-top:8px">
              <button type="button" class="primary" onclick="installConnector()">\u2b07\ufe0f Zainstaluj connector</button>
              <span class="subtle">instaluje na ho\u015bcie (pip/github/lokalny); npm/docker/http \u2192 komenda do ich \u015brodowiska</span>
            </div>
            <pre id="connectorInstallResult" class="mono" style="margin-top:8px;white-space:pre-wrap"></pre>
            <hr style="border-color:var(--line-soft);margin:12px 0">
            <h3 style="margin:0 0 6px">Test connectora</h3>
            <div class="ticket-form-grid">
              <label class="stack ticket-form-full"><span class="subtle">URI testowy (najlepiej read-only query)</span>
                <input id="connectorTestUri" placeholder="uuid://host/id/query/v4"></label>
              <label class="stack ticket-form-full"><span class="subtle">Payload (JSON)</span>
                <input id="connectorTestPayload" placeholder="{}"></label>
              <label class="stack"><span class="subtle">\u015arodowisko</span>
                <select id="connectorTestEnv"><option value="host">host (lokalnie)</option></select></label>
            </div>
            <div class="artifact-actions" style="margin-top:8px">
              <button type="button" onclick="testConnector()">\u25b6\ufe0f Testuj</button>
              <span id="connectorTestStatus" class="subtle"></span>
            </div>
            <pre id="connectorTestResult" class="mono" style="margin-top:8px;white-space:pre-wrap"></pre>
          </div>
        </article>
      </section>
      <section class="artifact-layout view-block" data-section="tasks">
        <article class="panel">
          <div class="panel-head">
            <div>
              <h2>Tickety</h2>
              <p class="subtle">Tickety infrastruktury — dodawaj ręcznie lub z czatu, uruchamiaj i zamykaj.</p>
            </div>
            <div class="toolbar">
              <select id="sprintFilter">
                <option value="current">current</option>
                <option value="all">all</option>
              </select>
              <select id="queueFilter">
                <option value="">all queues</option>
                <option value="implementation">implementation</option>
                <option value="daily">daily</option>
                <option value="review">review</option>
                <option value="infra">infra</option>
                <option value="default">default</option>
              </select>
              <button type="button" id="taskRefreshBtn" onclick="reloadTasks()">Odśwież</button>
            </div>
          </div>
          <div class="panel-body">
            <details class="add-ticket-form" id="addTicketDetails" style="margin-bottom:12px">
              <summary>➕ Nowy ticket (ręcznie lub z bieżącego promptu czatu)</summary>
              <div class="ticket-form-grid" style="margin-top:10px">
                <label class="stack"><span class="subtle">Tytuł</span><input id="newTicketName" placeholder="np. Wdróż node lenovo do mesh"></label>
                <label class="stack"><span class="subtle">Priorytet</span>
                  <select id="newTicketPriority"><option value="normal">normal</option><option value="high">high</option><option value="low">low</option></select></label>
                <label class="stack"><span class="subtle">Kolejka</span>
                  <select id="newTicketQueue"><option value="default">default</option><option value="infra">infra</option><option value="implementation">implementation</option><option value="daily">daily</option><option value="review">review</option></select></label>
                <label class="stack"><span class="subtle">Etykiety (po przecinku)</span><input id="newTicketLabels" placeholder="infra, deploy"></label>
                <label class="stack ticket-form-full"><span class="subtle">Opis</span><textarea id="newTicketDesc" rows="3" placeholder="Szczegóły zadania infrastrukturalnego…"></textarea></label>
              </div>
              <div class="artifact-actions" style="margin-top:8px">
                <button type="button" class="primary" onclick="createTicket()">💾 Utwórz ticket</button>
                <button type="button" onclick="createTicketFromChat()" title="Użyj tekstu z pola czatu jako nowy ticket">💬 Z promptu czatu</button>
                <span id="newTicketStatus" class="subtle"></span>
              </div>
            </details>
            <div class="table-wrap">
              <table>
                <thead><tr><th>ID</th><th>Name</th><th>Status</th><th>Queue</th><th>Priority</th><th>Actions</th></tr></thead>
                <tbody id="tasksBody"></tbody>
              </table>
            </div>
          </div>
        </article>
      </section>
      <div class="stack">
        <article class="panel view-block chat-panel" data-section="chat">
          <div class="panel-head">
            <div>
              <h2>Chat Result</h2>
              <p class="subtle">Natural language to URI flow across host, nodes and services.</p>
            </div>
            <div class="actions">
              <span class="subtle" id="chatStatus">idle</span>
              <span class="pill" id="chatMode">dry-run</span>
              <button id="chatFullscreenBtn" type="button">Full screen</button>
            </div>
          </div>
          <div class="panel-body">
            <div class="chat-shell">
              <div class="contacts-panel">
                <div>
                  <h3>Contacts</h3>
                  <p class="subtle">Select one or more URI targets.</p>
                </div>
                <div class="contact-list" id="chatContactList"></div>
              </div>
              <div class="chat-main">
                <div class="chat-toolbar">
                  <div class="subtle" id="chatTargetSummary">urirun host</div>
                  <div class="actions">
                    <span class="subtle" id="chatSelectionSummary">0 selected</span>
                    <button type="button" id="chatTwinBtn" title="Otwórz Digital Twin Monitor">&#128190; Twin</button>
                    <button type="button" id="chatScrollBottomBtn">Latest</button>
                    <button type="button" id="chatCopyVisibleBtn">Copy chat</button>
                    <button type="button" id="chatSelectVisibleBtn">Select visible</button>
                    <button type="button" id="chatClearSelectionBtn">Clear</button>
                    <button type="button" class="danger" id="chatDeleteSelectedBtn">Delete selected</button>
                    <button type="button" class="danger" id="chatDeleteVisibleBtn">Delete all visible</button>
                  </div>
                </div>
                <div class="stream-list" id="chatStreamList"></div>
                <div class="chat-result" id="chatResult"></div>
                <form class="chat-form chat-composer" id="chatForm">
                  <textarea id="chatPrompt" placeholder="Napisz komendę NL do wybranych kontaktów URI..."></textarea>
                  <div class="chat-options">
                    <label class="check"><input type="checkbox" id="chatExecute" checked> Execute URI operations</label>
                    <label class="check"><input type="checkbox" id="chatNoLlm"> Heuristic planner only</label>
                    <button class="primary" type="submit" id="chatAskBtn">Send</button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </article>
        <section class="nodes-layout view-block" data-section="nodes">
        <article class="panel">
          <div class="panel-head"><h2>Nodes</h2><span class="subtle" id="nodeCount"></span></div>
          <div class="panel-body">
            <div class="list" id="nodesList"></div>
            <details class="add-node-help" style="margin-top:10px">
              <summary>➕ Dodaj node (wybierz typ połączenia)</summary>
              <div class="stack" style="margin-top:8px">
                <p class="subtle">Każdy typ node ma inny poziom integracji i wymaga innej wiedzy. Wybierz typ, wypełnij formularz i otwórz pełną instrukcję. <a href="/docs/nodes" target="_blank" rel="noreferrer">📖 Dokumentacja typów node</a></p>
                <div class="node-kind-tabs" id="nodeKindTabs">
                  <button type="button" class="node-kind-tab" data-kind="server" onclick="selectNodeKind('server')">🖥️ Server <span class="subtle">shell/SSH</span></button>
                  <button type="button" class="node-kind-tab" data-kind="pc" onclick="selectNodeKind('pc')">💻 PC <span class="subtle">app + shell</span></button>
                  <button type="button" class="node-kind-tab" data-kind="rdp" onclick="selectNodeKind('rdp')">🪟 RDP <span class="subtle">pulpit zdalny</span></button>
	                  <button type="button" class="node-kind-tab" data-kind="smartphone" onclick="selectNodeKind('smartphone')">📱 Smartphone <span class="subtle">webpage → APK</span></button>
	                  <button type="button" class="node-kind-tab" data-kind="browser-debug" onclick="selectNodeKind('browser-debug')">🌐 Browser Debug <span class="subtle">CDP</span></button>
	                  <button type="button" class="node-kind-tab" data-kind="browser-chrome-plugin" onclick="selectNodeKind('browser-chrome-plugin')">🧩 Chrome Plugin <span class="subtle">extension</span></button>
	                  <button type="button" class="node-kind-tab" data-kind="browser-firefox-plugin" onclick="selectNodeKind('browser-firefox-plugin')">🧩 Firefox Plugin <span class="subtle">extension</span></button>
	                  <button type="button" class="node-kind-tab" data-kind="webpage" onclick="selectNodeKind('webpage')">📄 Webpage <span class="subtle">jedna strona JS</span></button>
	                  <button type="button" class="node-kind-tab" data-kind="api" onclick="selectNodeKind('api')">🔌 API <span class="subtle">HTTP/auth</span></button>
	                  <button type="button" class="node-kind-tab" data-kind="device" onclick="selectNodeKind('device')">🧩 Device <span class="subtle">multi-API</span></button>
                </div>

                <!-- SERVER -->
                <div class="node-kind-form" id="nodeForm-server" style="display:none">
                  <p class="subtle">🖥️ <strong>Server</strong> — sterowanie przez <strong>shell/SSH</strong>. Headless maszyna; instalujesz węzeł urirun zdalnie przez SSH. Wymaga: dostęp SSH (user@host), uprawnienia do instalacji. <a href="/docs/nodes#server" target="_blank" rel="noreferrer">instrukcja</a></p>
                  <label class="stack"><span class="subtle">Nazwa node'a</span><input id="srvName" placeholder="server-01"></label>
                  <label class="stack"><span class="subtle">Host / IP</span><input id="srvHost" oninput="srvSnippet()" placeholder="192.168.1.50"></label>
                  <div class="artifact-actions">
                    <label class="stack" style="flex:1"><span class="subtle">SSH user</span><input id="srvUser" oninput="srvSnippet()" placeholder="ubuntu"></label>
                    <label class="stack"><span class="subtle">Port node'a</span><input id="srvPort" oninput="srvSnippet()" value="8765" style="width:90px"></label>
                  </div>
                  <p class="subtle">Uruchom zdalnie (instaluje węzeł i serwuje go w tle):</p>
                  <pre id="srvSnippet" class="mono">— podaj host i usera —</pre>
                  <div class="artifact-actions">
                    <button type="button" onclick="saveTypedNode('server','srvName',srvUrl())">💾 Zapisz node (po instalacji)</button>
                    <span id="srvStatus" class="subtle"></span>
                  </div>
                </div>

                <!-- PC -->
                <div class="node-kind-form" id="nodeForm-pc" style="display:none">
                  <p class="subtle">💻 <strong>PC</strong> — sterowanie przez <strong>aplikację desktop + shell</strong>. Maszyna z GUI; uruchamiasz węzeł lokalnie (lub przez aplikację ifURI). Wymaga: dostęp do pulpitu, terminal. <a href="/docs/nodes#pc" target="_blank" rel="noreferrer">instrukcja</a></p>
                  <label class="stack"><span class="subtle">Nazwa node'a</span><input id="pcName" placeholder="lenovo"></label>
                  <label class="stack"><span class="subtle">URL węzła (po uruchomieniu)</span><input id="pcUrl" placeholder="http://192.168.1.20:8765"></label>
                  <p class="subtle">Na PC uruchom węzeł:</p>
                  <pre class="mono">curl -fsSL https://get.ifuri.com/node.sh | bash -s -- --name pc --port 8765 --background</pre>
                  <div class="artifact-actions">
                    <button type="button" onclick="saveTypedNode('pc','pcName',document.getElementById('pcUrl').value)">💾 Zapisz node</button>
                    <span id="pcStatus" class="subtle"></span>
                  </div>
                </div>

                <!-- RDP -->
                <div class="node-kind-form" id="nodeForm-rdp" style="display:none">
                  <p class="subtle">🪟 <strong>RDP</strong> — <strong>pulpit zdalny</strong> (Windows/xrdp). Sterujesz klawiaturą/myszą/ekranem zdalnego pulpitu. Wymaga: host RDP, login, port 3389, węzeł urirun z connectorem KVM po stronie pulpitu. <a href="/docs/nodes#rdp" target="_blank" rel="noreferrer">instrukcja</a></p>
                  <label class="stack"><span class="subtle">Nazwa node'a</span><input id="rdpName" placeholder="win-desktop"></label>
                  <div class="artifact-actions">
                    <label class="stack" style="flex:1"><span class="subtle">Host RDP</span><input id="rdpHost" oninput="rdpSnippet()" placeholder="192.168.1.30"></label>
                    <label class="stack"><span class="subtle">Port RDP</span><input id="rdpPort" oninput="rdpSnippet()" value="3389" style="width:90px"></label>
                  </div>
                  <label class="stack"><span class="subtle">URL węzła urirun na pulpicie</span><input id="rdpUrl" placeholder="http://192.168.1.30:8765"></label>
                  <p class="subtle">Połącz pulpit (przykład xfreerdp):</p>
                  <pre id="rdpSnippet" class="mono">— podaj host RDP —</pre>
                  <div class="artifact-actions">
                    <button type="button" onclick="saveTypedNode('rdp','rdpName',document.getElementById('rdpUrl').value)">💾 Zapisz node</button>
                    <span id="rdpStatus" class="subtle"></span>
                  </div>
                </div>

                <!-- SMARTPHONE (two-stage: webpage node now then mobile node after APK) -->
                <div class="node-kind-form" id="nodeForm-smartphone" style="display:none">
                  <p class="subtle">📱 <strong>Smartphone</strong> — dwa etapy: <strong>(1) webpage node</strong> od razu po otwarciu strony w przeglądarce telefonu (sterowanie przez JS na stronie), <strong>(2) mobile node</strong> po instalacji APK/Termux (pełny węzeł: pliki, system). Wymaga: serwis android-node (port 8195) + telefon w tej samej sieci. <a href="/docs/nodes#smartphone" target="_blank" rel="noreferrer">instrukcja</a></p>
                  <div class="artifact-actions">
                    <button type="button" id="phoneSvcBtn" onclick="startPhoneService()">▶ Uruchom serwis android-node</button>
                    <button type="button" onclick="restartPhoneService()">↻ Restart 8195</button>
                    <button type="button" id="addPhoneNodeBtn" onclick="showAddPhoneNodeQR()">📱 Pokaż QR</button>
                    <span id="addPhoneNodeStatus" class="subtle"></span>
                  </div>
                  <div id="phoneNodeQrContainer" style="display:none;margin-top:8px">
                    <div id="phoneNodeQr" class="phone-node-qr"></div>
                    <p class="subtle">URL instalacji: <code id="phoneNodeUrl"></code></p>
                    <p class="subtle" id="phoneNodeReach"></p>
                    <div id="phoneWebNodes" class="subtle">Brak podłączonych telefonów (webpage node) — otwórz URL na telefonie.</div>
                    <label class="stack" style="margin-top:6px"><span class="subtle">Po instalacji APK — zarejestruj jako mobile node (nazwa + URL telefonu, port 8765)</span></label>
                    <div class="artifact-actions">
                      <input id="phoneNodeName" placeholder="nexus7">
                      <input id="phoneNodeNodeUrl" placeholder="http://192.168.x.x:8765">
                      <button type="button" onclick="savePhoneNode()">💾 Zapisz mobile node</button>
                      <span id="phoneNodeSaveStatus" class="subtle"></span>
                    </div>
                  </div>
                </div>

                <!-- BROWSER DEBUG -->
                <div class="node-kind-form" id="nodeForm-browser-debug" style="display:none">
                  <p class="subtle">🌐 <strong>Browser Debug</strong> — sterowanie <strong>całą przeglądarką</strong> przez DevTools/CDP. Wszystkie karty: otwieraj/zamykaj/nawiguj. Wymaga: przeglądarka z <code>--remote-debugging-port=9222</code> + connector webnode. <a href="/docs/nodes#browser-debug" target="_blank" rel="noreferrer">instrukcja</a></p>
                  <div class="phone-node-qr" id="connectQr-browser-debug"></div>
                  <p class="subtle">QR powyżej = ścieżka <strong>relay</strong> (otwórz na urządzeniu, <code>http://HOST:8195/</code>, <strong>HTTP</strong>). Pola CDP poniżej = osobny tryb debugowania: lista kart i pełne sterowanie przez DevTools, ale wymaga uruchomienia przeglądarki z <code>--remote-debugging-port=9222</code>.</p>
                  <label class="stack"><span class="subtle">Nazwa node'a</span><input id="brName" placeholder="chrome"></label>
                  <label class="stack"><span class="subtle">Endpoint debugowania (CDP)</span><input id="brUrl" placeholder="http://127.0.0.1:9222" oninput="updateEndpointQr('brUrl','cdpQr-browser-debug')"></label>
                  <div class="phone-node-qr" id="cdpQr-browser-debug"><span class="subtle">wpisz endpoint CDP — QR pojawi się tutaj</span></div>
                  <p class="subtle">Uruchom przeglądarkę z debugowaniem:</p>
                  <pre class="mono">google-chrome --remote-debugging-port=9222 --remote-debugging-address=127.0.0.1</pre>
                  <div class="artifact-actions">
                    <button type="button" onclick="saveTypedNode('browser-debug','brName',document.getElementById('brUrl').value)">💾 Zapisz node</button>
                    <span id="brStatus" class="subtle"></span>
                  </div>
                </div>

                <!-- CHROME PLUGIN -->
                <div class="node-kind-form" id="nodeForm-browser-chrome-plugin" style="display:none">
                  <p class="subtle">🧩 <strong>Chrome Plugin</strong> — kontrola aktywnej karty przez rozszerzenie Chrome. Używa <code>browser-plugin://chrome/...</code> i może czytać DOM, listować urządzenia strony, uruchamiać kamerę oraz przekazywać inne URI do node <code>/run</code>. <a href="/docs/nodes#browser-chrome-plugin" target="_blank" rel="noreferrer">instrukcja</a></p>
                  <label class="stack"><span class="subtle">Nazwa node'a</span><input id="chromePluginName" placeholder="chrome-plugin"></label>
                  <label class="stack"><span class="subtle">Node URL dla popupu pluginu</span><input id="chromePluginUrl" placeholder="http://127.0.0.1:8765"></label>
                  <p class="subtle">Załaduj folder <code>/home/tom/github/if-uri/chrome-plugin</code> w <code>chrome://extensions</code> jako unpacked extension.</p>
                  <div class="artifact-actions">
                    <button type="button" onclick="saveTypedNode('browser-chrome-plugin','chromePluginName',document.getElementById('chromePluginUrl').value)">💾 Zapisz node</button>
                    <span id="chromePluginStatus" class="subtle"></span>
                  </div>
                </div>

                <!-- FIREFOX PLUGIN -->
                <div class="node-kind-form" id="nodeForm-browser-firefox-plugin" style="display:none">
                  <p class="subtle">🧩 <strong>Firefox Plugin</strong> — kontrola aktywnej karty przez rozszerzenie Firefox. Używa <code>browser-plugin://firefox/...</code> i zachowuje kompatybilność z <code>browser://</code>. <a href="/docs/nodes#browser-firefox-plugin" target="_blank" rel="noreferrer">instrukcja</a></p>
                  <label class="stack"><span class="subtle">Nazwa node'a</span><input id="firefoxPluginName" placeholder="firefox-plugin"></label>
                  <label class="stack"><span class="subtle">Node URL dla popupu pluginu</span><input id="firefoxPluginUrl" placeholder="http://127.0.0.1:8765"></label>
                  <p class="subtle">Załaduj folder <code>/home/tom/github/if-uri/firefox-plugin</code> w <code>about:debugging#/runtime/this-firefox</code>.</p>
                  <div class="artifact-actions">
                    <button type="button" onclick="saveTypedNode('browser-firefox-plugin','firefoxPluginName',document.getElementById('firefoxPluginUrl').value)">💾 Zapisz node</button>
                    <span id="firefoxPluginStatus" class="subtle"></span>
                  </div>
                </div>

                <!-- WEBPAGE -->
                <div class="node-kind-form" id="nodeForm-webpage" style="display:none">
                  <p class="subtle">📄 <strong>Webpage</strong> — sterowanie <strong>konkretną stroną</strong> przez HTML/JS (relay). Otwórz QR na urządzeniu — strona rejestruje się sama w serwisie android-node pod <code>http://HOST:8195/</code> (czysty <strong>HTTP</strong>, bez „s") i staje się webpage node: lista URI process, urządzenia strony (kamera/mikrofon), sensory, akcje navigate/eval/iframe. Tryb debugowania przeglądarki (CDP/DevTools) jest w osobnej zakładce <strong>Browser Debug</strong>. <a href="/docs/nodes#webpage" target="_blank" rel="noreferrer">instrukcja</a></p>
                  <div class="phone-node-qr" id="connectQr-webpage"></div>
                  <div id="webpageNodes" class="subtle">Brak podłączonych stron — otwórz QR na urządzeniu (telefon/przeglądarka).</div>
                  <label class="stack"><span class="subtle">Nazwa node'a</span><input id="webName" placeholder="page-checkout"></label>
                  <div class="artifact-actions">
                    <button type="button" onclick="saveWebpageNode()">💾 Zapisz webpage node</button>
                    <span id="webStatus" class="subtle"></span>
                  </div>
                </div>

                <!-- API NODE -->
	                <div class="node-kind-form" id="nodeForm-api" style="display:none">
	                  <p class="subtle">🔌 <strong>API Node</strong> — zewnętrzne API HTTP/REST/OpenAPI z autoryzacją. Sekret zostanie zapisany w keyring, a w configu zostanie tylko <code>secretRef</code>. <a href="/docs/nodes#api" target="_blank" rel="noreferrer">instrukcja</a></p>
	                  <label class="stack"><span class="subtle">Nazwa node'a</span><input id="apiNodeName" placeholder="crm-api"></label>
	                  <label class="stack"><span class="subtle">Base URL API</span><input id="apiNodeUrl" placeholder="https://api.example.test/v1"></label>
	                  <div class="artifact-actions">
	                    <label class="stack" style="flex:1"><span class="subtle">API id</span><input id="apiNodeApiId" value="main"></label>
	                    <label class="stack" style="flex:1"><span class="subtle">Kind/protocol</span><input id="apiNodeApiKind" value="rest"></label>
	                  </div>
	                  <div class="artifact-actions">
	                    <label class="stack" style="flex:1"><span class="subtle">Auth type</span><input id="apiNodeAuthType" placeholder="bearer / api-key / basic"></label>
	                    <label class="stack" style="flex:2"><span class="subtle">Token/API key (keyring)</span><input id="apiNodeSecret" type="password" autocomplete="off" placeholder="nie zapisuje się w pliku"></label>
	                  </div>
	                  <div class="artifact-actions">
	                    <button type="button" onclick="saveApiNode()">💾 Zapisz API node</button>
	                    <span id="apiNodeStatus" class="subtle"></span>
	                  </div>
	                </div>

	                <!-- DEVICE NODE -->
	                <div class="node-kind-form" id="nodeForm-device" style="display:none">
	                  <p class="subtle">🧩 <strong>Device Node</strong> — urządzenie z wieloma interfejsami, np. kamera IP/RPi/NAS: panel WWW, RTSP/RTMP, SSH, SMB/NFS. <a href="/docs/nodes#device" target="_blank" rel="noreferrer">instrukcja</a></p>
	                  <label class="stack"><span class="subtle">Nazwa node'a</span><input id="deviceNodeName" placeholder="rpi-camera"></label>
	                  <label class="stack"><span class="subtle">Główny URL/panel</span><input id="deviceNodeUrl" placeholder="http://rpi.local"></label>
	                  <label class="stack"><span class="subtle">apis[] JSON</span><textarea id="deviceNodeApis" rows="7">[
  {"id":"panel","kind":"web","url":"http://rpi.local"},
  {"id":"stream","kind":"rtsp","role":"camera","url":"rtsp://rpi.local/live"},
  {"id":"share","kind":"smb","url":"smb://rpi.local/share"},
  {"id":"ssh","kind":"ssh","url":"ssh://pi@rpi.local"}
]</textarea></label>
	                  <div class="artifact-actions">
	                    <button type="button" onclick="saveDeviceNode()">💾 Zapisz device node</button>
	                    <span id="deviceNodeStatus" class="subtle"></span>
	                  </div>
	                </div>

	                <hr style="border:none;border-top:1px solid var(--border,#334155);margin:12px 0">
                <details>
                  <summary class="subtle">🔎 Skan LAN / wpis ręczny / token (zaawansowane)</summary>
                  <div class="stack" style="margin-top:8px">
                    <div class="artifact-actions">
                      <button type="button" id="scanNodesBtn" onclick="scanNodes()">🔎 Skanuj sieć (LAN)</button>
                      <span id="scanNodesStatus" class="subtle"></span>
                    </div>
                    <div id="scanNodesResults" class="list"></div>
                    <label class="stack"><span class="subtle">Nazwa node'a</span><input id="addNodeName" oninput="nodeAddSnippet()" placeholder="office-node"></label>
                    <label class="stack"><span class="subtle">URL node'a</span><input id="addNodeUrl" oninput="nodeAddSnippet()" placeholder="http://host-or-ip:8765"></label>
                    <div class="artifact-actions">
                      <button type="button" onclick="saveNodeFromForm()">💾 Zapisz node</button>
                      <a id="addNodeHealth" href="#" target="_blank" rel="noreferrer">otwórz /health</a>
                      <span id="addNodeStatus" class="subtle"></span>
                    </div>
                    <label class="stack"><span class="subtle">Token zarządzania węzłem (X-Urirun-Token)</span>
                      <input id="addNodeToken" type="password" autocomplete="off" placeholder="wklej token (keyring, nie plaintext)"></label>
                    <div class="artifact-actions">
                      <button type="button" onclick="saveNodeToken()">🔑 Zapisz token (keyring)</button>
                      <span id="addNodeTokenStatus" class="subtle"></span>
                    </div>
                    <pre id="addNodeSnippet" class="mono">— wpisz nazwę i URL powyżej —</pre>
                  </div>
                </details>
              </div>
            </details>
          </div>
        </article>
        <article class="panel">
          <div class="panel-head"><h2>URI Processes</h2><span class="subtle" id="routeCount"></span><span id="routesNodeFilter" class="subtle"></span></div>
          <div class="panel-body"><div class="list" id="routesList"></div></div>
        </article>
        </section>
      </div>
      <aside class="stack">
        <article class="panel view-block" data-section="activity">
          <div class="panel-head"><h2>Logs</h2><span class="subtle" id="logCount"></span></div>
          <div class="panel-body"><div id="logsList"></div></div>
        </article>
      </aside>
    </section>
  </main>
  <nav class="bottom-nav">
    <button data-view="overview">Overview</button>
    <button data-view="chat">Chat</button>
    <button data-view="discovery">Discovery</button>
    <button data-view="artifacts">Artifacts</button>
    <button data-view="widgets">Widgets</button>
    <button data-view="twin">Digital Twin</button>
    <button data-view="tasks">Tasks</button>
    <button data-view="host">Host</button>
    <button data-view="nodes">Nodes</button>
    <button data-view="activity">Activity</button>
  </nav>
  <script src="/dashboard.js"></script>
</body>
</html>
"""

NODE_TYPES_DOC_HTML = r"""<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>urirun — typy node i konfiguracja połączeń</title>
<style>
  body { max-width: 820px; margin: 0 auto; padding: 2rem 1rem; font-family: system-ui, sans-serif;
         line-height: 1.6; color: #e2e8f0; background: #0f172a; }
  h1 { color: #38bdf8; } h2 { color: #38bdf8; margin-top: 2rem; border-top: 1px solid #334155; padding-top: 1rem; }
  code, pre { font-family: ui-monospace, monospace; background: #0d1117; border-radius: 4px; }
  code { padding: 1px 5px; color: #4ade80; } pre { display: block; padding: .8rem; overflow-x: auto; color: #4ade80; }
  table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
  th, td { border: 1px solid #334155; padding: 6px 10px; text-align: left; font-size: .9rem; }
  th { background: #1e293b; color: #38bdf8; }
  a { color: #38bdf8; } .lead { color: #94a3b8; }
</style>
</head>
<body>
<h1>Typy node i konfiguracja połączeń</h1>
<p class="lead">Każdy node ma inny poziom integracji i wymaga innej wiedzy. Wybierz typ pasujący do
maszyny/urządzenia i postępuj według sekcji poniżej. Wszystkie node wystawiają trasy <code>URI</code>,
ale różnią się <strong>transportem</strong> i tym, <strong>co</strong> potrafią.</p>

<table>
  <tr><th>Typ</th><th>Transport</th><th>Wymagana wiedza</th><th>Connector</th></tr>
  <tr><td>🖥️ server</td><td>shell / SSH</td><td>SSH, instalacja zdalna</td><td>get-node + shell</td></tr>
  <tr><td>💻 pc</td><td>aplikacja + shell</td><td>pulpit, terminal</td><td>get-node + kvm</td></tr>
  <tr><td>🪟 rdp</td><td>pulpit zdalny (RDP)</td><td>RDP, login Windows</td><td>kvm / rdp</td></tr>
  <tr><td>📱 smartphone</td><td>webpage → APK/Termux</td><td>instalacja apki, sieć LAN</td><td>android-node + adb</td></tr>
  <tr><td>🌐 browser-debug</td><td>DevTools (CDP)</td><td>uruchomienie z debug portem</td><td>webnode</td></tr>
  <tr><td>🧩 browser-chrome-plugin</td><td>Chrome Extension</td><td>Load unpacked, permissions</td><td>chrome-plugin</td></tr>
  <tr><td>🧩 browser-firefox-plugin</td><td>Firefox Extension</td><td>Temporary Add-on, permissions</td><td>firefox-plugin</td></tr>
  <tr><td>📄 webpage</td><td>HTML/JS na stronie</td><td>CDP, plugin albo page bridge</td><td>webnode / js-urirun-com</td></tr>
  <tr><td>🔌 api</td><td>HTTP/REST/OpenAPI</td><td>URL API + auth</td><td>http-api / fetch / oauth</td></tr>
  <tr><td>🧩 device</td><td>wiele protokołów</td><td>panel, RTSP, SSH, SMB/NAS</td><td>camera / rtsp / ssh / smb</td></tr>
</table>

<h2 id="server">🖥️ Server — shell / SSH</h2>
<p>Headless maszyna (VPS, serwer). Sterowanie przez shell; węzeł urirun instalujesz zdalnie po SSH.</p>
<p><strong>Potrzebujesz:</strong> dostęp SSH (<code>user@host</code>), prawa do instalacji.</p>
<pre>ssh user@HOST "curl -fsSL https://get.ifuri.com/node.sh | bash -s -- --name HOST --port 8765 --background"</pre>
<p>Następnie w dashboardzie zapisz node z URL <code>http://HOST:8765</code>. Test: <code>http://HOST:8765/health</code>.</p>

<h2 id="pc">💻 PC — aplikacja + shell</h2>
<p>Maszyna z GUI (laptop, desktop). Uruchamiasz węzeł lokalnie lub przez aplikację ifURI; dochodzi
sterowanie pulpitem (connector <code>kvm</code>: zrzut ekranu, klawiatura, mysz).</p>
<pre>curl -fsSL https://get.ifuri.com/node.sh | bash -s -- --name pc --port 8765 --background</pre>
<p>Zapisz node z URL <code>http://IP-PC:8765</code>.</p>

<h2 id="rdp">🪟 RDP — pulpit zdalny</h2>
<p>Windows/xrdp przez RDP (port 3389). Łączysz się z pulpitem i sterujesz nim; po stronie pulpitu
działa węzeł urirun z connectorem KVM.</p>
<p><strong>Potrzebujesz:</strong> host RDP, login, klient RDP (np. <code>xfreerdp</code>).</p>
<pre>xfreerdp /v:HOST:3389 /u:USER /p:PASS /cert:ignore</pre>
<p>Na pulpicie uruchom węzeł (jak PC) i zapisz node z URL <code>http://HOST:8765</code>.</p>

<h2 id="smartphone">📱 Smartphone — webpage node → mobile node</h2>
<p>Dwa etapy integracji telefonu:</p>
<ol>
  <li><strong>Webpage node (od razu):</strong> uruchom serwis android-node/webpage i otwórz jego URL w przeglądarce
  telefonu. Przeglądarka rejestruje się jako <code>webpage</code> node — sterowanie przez
  JS na otwartej stronie: nawigacja, eval, lista urządzeń, kamera i akcje strony. Nic nie instalujesz.</li>
  <li><strong>Mobile node (pełny):</strong> ze strony pobierasz APK lub uruchamiasz skrypt Termux.
  Telefon staje się pełnym węzłem (port 8765): pliki, system, wejście — przez connector <code>adb</code>.</li>
</ol>
<pre>urirun-android-node serve     # serwis dystrybucji (port 8195), QR + APK + bootstrap</pre>
<p>W dashboardzie: <em>Smartphone → Uruchom serwis android-node → Pokaż QR</em>. Zeskanuj telefonem.
Podłączone telefony pojawią się na liście „webpage node"; po instalacji APK zapisz je jako „mobile node".</p>

<h2 id="browser-debug">🌐 Browser Debug — cała przeglądarka (CDP)</h2>
<p>Sterowanie całą przeglądarką przez Chrome DevTools Protocol: wszystkie karty (otwórz/zamknij/nawiguj),
status, zrzuty. Connector <code>webnode</code>, zakres <code>browser</code>. Stary typ <code>browser</code>
jest aliasem do <code>browser-debug</code>.</p>
<pre>google-chrome --remote-debugging-port=9222 --remote-debugging-address=127.0.0.1</pre>
<pre>urirun run "webnode://browser/tabs/query/list" --entry-points --execute --allow 'webnode://*'</pre>
<p>Zapisz node z endpointem <code>http://127.0.0.1:9222</code> i typem <code>browser-debug</code>.</p>

<h2 id="browser-chrome-plugin">🧩 Chrome Plugin — aktywna karta przez rozszerzenie</h2>
<p>Tryb bez debug portu. Rozszerzenie działa w aktywnej karcie, obsługuje
<code>browser-plugin://chrome/...</code> oraz kompatybilne <code>browser://...</code>,
a inne URI przekazuje do skonfigurowanego node <code>/run</code>.</p>
<pre>cd /home/tom/github/if-uri/chrome-plugin
make test
# chrome://extensions -> Developer mode -> Load unpacked -> ten folder</pre>

<h2 id="browser-firefox-plugin">🧩 Firefox Plugin — aktywna karta przez rozszerzenie</h2>
<p>Analogiczny tryb dla Firefox. Rozszerzenie obsługuje
<code>browser-plugin://firefox/...</code> oraz kompatybilne <code>browser://...</code>.</p>
<pre>cd /home/tom/github/if-uri/firefox-plugin
make test
# about:debugging#/runtime/this-firefox -> Load Temporary Add-on</pre>

<h2 id="webpage">📄 Webpage — pojedyncza strona (HTML/JS)</h2>
<p>Sterowanie <strong>konkretną stroną/kartą</strong>: nawigacja, eval JS, klik po selektorze,
wpisywanie, zrzut, lista urządzeń strony, kamera, sensory, iframe/proxy. Może działać przez
CDP page scope, plugin albo page bridge na porcie <code>8195</code>. Stary typ <code>web</code>
jest aliasem do <code>webpage</code>.</p>
<pre># lista kart i ich id:
urirun run "webnode://browser/tabs/query/list" --entry-points --execute --allow 'webnode://*'
# steruj jedną stroną:
WEBNODE_TARGET=&lt;id&gt; urirun run "webnode://page/command/navigate" \
  --entry-points --execute --allow 'webnode://*' --payload '{"url":"https://example.com"}'</pre>
<p>Zapisz node z endpointem CDP i typem <code>webpage</code>, albo otwórz QR z serwisu
<code>8195</code>, żeby strona zarejestrowała się jako webpage node.</p>

<h2 id="api">🔌 API — zewnętrzny endpoint z autoryzacją</h2>
<p>API node służy do podpinania SaaS, lokalnych usług HTTP, REST/OpenAPI albo paneli sterowania.
Sekret przekazany w formularzu jest zapisywany w keyring jako <code>secretRef</code>, a nie w pliku config.</p>
<pre>urirun host add-node crm-api https://api.example.test/v1 \
  --kind api --api-id main --api-kind rest \
  --auth-type bearer --auth-token PASTE_ONCE</pre>
<pre>{
  "name": "crm-api",
  "url": "https://api.example.test/v1",
  "kind": "api",
  "apis": [
    {"id": "main", "kind": "rest", "url": "https://api.example.test/v1",
     "auth": {"type": "bearer", "token": "PASTE_ONCE"}}
  ]
}</pre>
<p>Discovery pokazuje wtedy route'y konfiguracyjne, np. <code>api://crm-api/main/command/request</code>.</p>
<p>HTTP/REST/OpenAPI może być wykonane bezpośrednio przez hosta. Przykład payloadu:</p>
<pre>{
  "uri": "api://crm-api/main/command/request",
  "mode": "execute",
  "payload": {"method": "GET", "path": "/accounts", "query": {"limit": 10}}
}</pre>
<p>Wariant neutralny dla plannerów to <code>configured://host/node-api/command/request</code>
z payloadem zawierającym <code>node</code> i <code>apiId</code>.</p>

<h2 id="device">🧩 Device — kamera, RPi, NAS, nietypowe urządzenie</h2>
<p>Device node ma wiele interfejsów API. Przykład: RPi jako kamera i NAS ma panel WWW,
RTSP stream, SMB share i SSH shell. Jeden obiekt node grupuje je jako <code>apis[]</code>.</p>
<pre>urirun host add-node rpi-camera http://rpi.local \
  --kind device \
  --api '{"id":"panel","kind":"web","url":"http://rpi.local"}' \
  --api '{"id":"stream","kind":"rtsp","role":"camera","url":"rtsp://rpi.local/live"}' \
  --api '{"id":"share","kind":"smb","url":"smb://rpi.local/share"}' \
  --api '{"id":"ssh","kind":"ssh","url":"ssh://pi@rpi.local"}'</pre>
<pre>{
  "name": "rpi-camera",
  "url": "http://rpi.local",
  "kind": "device",
  "apis": [
    {"id": "panel", "kind": "web", "url": "http://rpi.local"},
    {"id": "stream", "kind": "rtsp", "role": "camera", "url": "rtsp://rpi.local/live"},
    {"id": "share", "kind": "smb", "url": "smb://rpi.local/share"},
    {"id": "ssh", "kind": "ssh", "url": "ssh://pi@rpi.local"}
  ]
}</pre>
<p>Discovery tworzy syntetyczne route'y: <code>device://</code>, <code>media://</code>,
<code>camera://</code>, <code>ssh://</code> i <code>fs://</code>. Wykonanie tych route'ów
powinny przejąć odpowiednie connectory. Host wykona tylko interfejsy HTTP-like;
dla RTSP/SMB/SSH zwróci <code>connector_required</code>, zamiast udawać wykonanie.</p>

<p class="lead" style="margin-top:2rem">⬅ <a href="/?view=nodes">Powrót do dashboardu</a></p>
</body>
</html>
"""

SCANNER_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>urirun phone scanner</title>
  <style>
    :root { color-scheme: dark; --bg:#0b0f14; --panel:#111827; --ink:#f8fafc; --muted:#94a3b8; --line:#334155; --accent:#14b8a6; --bad:#f87171; }
    * { box-sizing: border-box; }
    body { margin:0; font:15px/1.45 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:var(--bg); color:var(--ink); }
    header { padding:12px 14px; border-bottom:1px solid var(--line); display:flex; justify-content:space-between; gap:10px; align-items:center; }
    h1 { margin:0; font-size:18px; }
    main { display:grid; gap:12px; padding:12px; }
    video, canvas { width:100%; max-height:72vh; object-fit:contain; background:#000; border:1px solid var(--line); border-radius:8px; }
    .controls { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
    button, select, input { min-height:44px; border:1px solid var(--line); border-radius:7px; background:var(--panel); color:var(--ink); font:inherit; padding:0 12px; }
    button.primary { background:var(--accent); border-color:var(--accent); color:#042f2e; font-weight:700; }
    button.remote-click { outline:3px solid #fde68a; outline-offset:2px; }
    button:disabled { opacity:.55; }
    .field { display:grid; gap:4px; color:var(--muted); font-size:13px; }
    .inline-check { min-height:44px; display:flex; gap:8px; align-items:center; color:var(--muted); }
    .inline-check input { min-height:auto; }
    .status { color:var(--muted); overflow-wrap:anywhere; }
    .error { color:var(--bad); }
  </style>
</head>
<body>
  <header>
    <h1>urirun phone scanner</h1>
    <span class="status" id="state">idle</span>
  </header>
  <main>
    <video id="video" autoplay playsinline muted></video>
    <canvas id="canvas" hidden></canvas>
    <div class="controls">
      <button class="primary" id="start">Start camera</button>
      <button id="torch" disabled>Light off</button>
      <button class="primary" id="capture" disabled>Scan now</button>
      <button class="primary" id="best" disabled>Best PDF</button>
      <select id="bestCount">
        <option value="6">6 frames</option>
        <option value="4">4 frames</option>
        <option value="8">8 frames</option>
      </select>
      <select id="quality">
        <option value="0.92">JPEG 92%</option>
        <option value="0.82">JPEG 82%</option>
        <option value="0.70">JPEG 70%</option>
      </select>
      <label class="field">Scan interval (s)<input type="number" id="scanInterval" min="1" max="60" step="0.5" inputmode="decimal"></label>
      <label class="inline-check"><input type="checkbox" id="startBest" checked> best after start</label>
      <label class="inline-check"><input type="checkbox" id="auto"> <span id="autoIntervalLabel">auto every 3s</span></label>
    </div>
    <p class="status">Use this page from the phone on the same LAN. Mobile browsers usually require HTTPS or a trusted local exception for camera access.</p>
  </main>
  <script src="/assets/urirun.js"
          data-site="urirun-phone-scanner"
          data-endpoint="/api/uri/event"
          data-action-endpoint="/api/uri/invoke"
          data-load="0"
          data-clicks="0"
          data-forms="0"
          data-spa="0"
          data-debug="1"></script>
  <script>
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const state = document.getElementById('state');
    const startBtn = document.getElementById('start');
    const torchBtn = document.getElementById('torch');
    const captureBtn = document.getElementById('capture');
    const bestBtn = document.getElementById('best');
    const bestCount = document.getElementById('bestCount');
    const quality = document.getElementById('quality');
    const scanInterval = document.getElementById('scanInterval');
    const autoIntervalLabel = document.getElementById('autoIntervalLabel');
    const startBest = document.getElementById('startBest');
    const auto = document.getElementById('auto');
    let stream = null;
    let timer = null;
    let bestRunning = false;
    let torchOn = false;
    let startCameraPromise = null;
    let startCameraClickPromise = null;
    let torchClickPromise = null;
    const scannerParams = new URLSearchParams(location.search);
    const DEFAULT_SCANNER_PARAMS = {
      autostart: '1',
      auto: '1',
      best: '1',
      count: '6',
      minScore: '45',
    };

    function applyDefaultScannerParams() {
      let changed = false;
      Object.entries(DEFAULT_SCANNER_PARAMS).forEach(([name, value]) => {
        if (!scannerParams.has(name)) {
          scannerParams.set(name, value);
          changed = true;
        }
      });
      if (!scannerParams.has('interval') && !scannerParams.has('scanInterval') && !scannerParams.has('intervalMs')) {
        scannerParams.set('interval', '3');
        changed = true;
      }
      if (!changed) return;
      const query = scannerParams.toString();
      history.replaceState(null, '', `${location.pathname}${query ? `?${query}` : ''}${location.hash || ''}`);
    }

    applyDefaultScannerParams();

    function truthyParam(name, fallback=false) {
      if (!scannerParams.has(name)) return fallback;
      const value = String(scannerParams.get(name) || '').toLowerCase();
      return !['0', 'false', 'no', 'off'].includes(value);
    }

    function numericParam(name, fallback) {
      const raw = Number(scannerParams.get(name));
      return Number.isFinite(raw) && raw > 0 ? raw : fallback;
    }

    function scanIntervalMs(options={}) {
      if (Object.prototype.hasOwnProperty.call(options || {}, 'interval')) {
        const seconds = Number(options.interval);
        if (Number.isFinite(seconds) && seconds > 0) return seconds * 1000;
      }
      if (Object.prototype.hasOwnProperty.call(options || {}, 'intervalSeconds')) {
        const seconds = Number(options.intervalSeconds);
        if (Number.isFinite(seconds) && seconds > 0) return seconds * 1000;
      }
      if (Object.prototype.hasOwnProperty.call(options || {}, 'intervalMs')) {
        const ms = Number(options.intervalMs);
        if (Number.isFinite(ms) && ms > 0) return ms;
      }
      if (scannerParams.has('interval')) return numericParam('interval', 3) * 1000;
      if (scannerParams.has('scanInterval')) return numericParam('scanInterval', 3) * 1000;
      return numericParam('intervalMs', 3000);
    }

    function writeScannerUrlState() {
      const query = scannerParams.toString();
      history.replaceState(null, '', `${location.pathname}${query ? `?${query}` : ''}${location.hash || ''}`);
    }

    function formatSeconds(value) {
      const rounded = Math.round(Number(value) * 10) / 10;
      return Number.isFinite(rounded) ? String(rounded).replace(/\.0$/, '') : '3';
    }

    function syncIntervalControl(options={}) {
      const seconds = formatSeconds(scanIntervalMs(options) / 1000);
      scanInterval.value = seconds;
      autoIntervalLabel.textContent = `auto every ${seconds}s`;
      return Number(seconds);
    }

    function updateIntervalFromControl() {
      const seconds = Number(scanInterval.value);
      if (!Number.isFinite(seconds) || seconds <= 0) {
        syncIntervalControl();
        return;
      }
      const normalized = formatSeconds(seconds);
      scannerParams.set('interval', normalized);
      scannerParams.delete('scanInterval');
      scannerParams.delete('intervalMs');
      writeScannerUrlState();
      syncIntervalControl();
      if (auto.checked) startAutoLoop();
      announce('interval-changed', {interval: Number(normalized)}).catch(() => {});
    }

    function setState(text, error=false) {
      state.textContent = text;
      state.className = error ? 'status error' : 'status';
    }

    // Audible/tactile confirmation that scan + OCR + identification finished.
    // 'ok' = new document saved, 'duplicate' = recognised as already archived,
    // 'superseded' = replaced a worse earlier scan, 'error' = processing failed.
    let feedbackAudioCtx = null;
    function feedbackEnabled() {
      return truthyParam('beep', true);
    }

    function unlockFeedbackAudio() {
      if (!feedbackEnabled()) return Promise.resolve(null);
      try {
        const Ctx = window.AudioContext || window.webkitAudioContext;
        if (!Ctx) return Promise.resolve(null);
        feedbackAudioCtx = feedbackAudioCtx || new Ctx();
        const resume = feedbackAudioCtx.state === 'suspended'
          ? feedbackAudioCtx.resume().catch(() => null)
          : Promise.resolve(feedbackAudioCtx);
        return resume.then(() => feedbackAudioCtx);
      } catch (_e) {
        return Promise.resolve(null);
      }
    }

    function feedbackTone(kind) {
      if (!feedbackEnabled()) return;
      try {
        if (navigator.vibrate) {
          navigator.vibrate(kind === 'error' ? [120, 60, 120] : kind === 'duplicate' ? [40, 40, 40] : 30);
        }
      } catch (_e) {}
      unlockFeedbackAudio().then((ctx) => {
        if (!ctx) return;
        // Each tone: [frequencyHz, startOffsetSec, durationSec].
        const tones = kind === 'error'
          ? [[220, 0, 0.32]]
          : kind === 'duplicate'
            ? [[620, 0, 0.09], [620, 0.13, 0.09]]
            : kind === 'superseded'
              ? [[660, 0, 0.09], [990, 0.11, 0.16]]
              : [[880, 0, 0.12], [1320, 0.12, 0.16]];
        const now = ctx.currentTime;
        for (const [freq, at, dur] of tones) {
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.type = 'sine';
          osc.frequency.value = freq;
          gain.gain.setValueAtTime(0.0001, now + at);
          gain.gain.exponentialRampToValueAtTime(0.25, now + at + 0.02);
          gain.gain.exponentialRampToValueAtTime(0.0001, now + at + dur);
          osc.connect(gain).connect(ctx.destination);
          osc.start(now + at);
          osc.stop(now + at + dur + 0.02);
        }
      }).catch(() => {});
    }

    function captureFeedbackKind(data) {
      const doc = (data && data.document) || {};
      if (doc.superseded || (data && data.superseded)) return 'superseded';
      if (doc.duplicate || (data && data.duplicate)) return 'duplicate';
      return 'ok';
    }

    function invokeURI(uri, payload={}) {
      if (window.urirun && typeof window.urirun.invoke === 'function') {
        return window.urirun.invoke(uri, payload);
      }
      return fetch('/api/uri/invoke', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({uri, payload})
      }).then((response) => response.json());
    }

    async function announce(event, extra={}) {
      try {
        await invokeURI('scanner://host/session/command/log', {
          event,
          href: location.href,
          width: window.innerWidth,
          height: window.innerHeight,
          userAgent: navigator.userAgent,
          at: new Date().toISOString(),
          ...extra
        });
      } catch (_) {}
    }

    async function startCamera(options={}) {
      if (stream && stream.getVideoTracks && stream.getVideoTracks().some((track) => track.readyState === 'live')) {
        await waitForVideoReady();
        refreshTorchButton();
        return cameraStatus();
      }
      stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: {
          facingMode: { ideal: 'environment' },
          width: { ideal: 2560 },
          height: { ideal: 1440 }
        }
      });
      video.srcObject = stream;
      if (video.play) await video.play().catch(() => {});
      await waitForVideoReady();
      captureBtn.disabled = false;
      bestBtn.disabled = false;
      refreshTorchButton();
      setState('camera ready');
      await announce('camera-started', {tracks: stream.getVideoTracks().map((track) => track.label)});
      const shouldStartBest = Object.prototype.hasOwnProperty.call(options || {}, 'startBest') ? !!options.startBest : startBest.checked;
      if (auto.checked) startAutoLoop();
      if (shouldStartBest) {
        setTimeout(() => bestPdf(options || {}).catch((err) => setState(err.message, true)), 350);
      }
      return cameraStatus();
    }

    function runStartCamera(options={}) {
      if (!startCameraPromise) {
        startCameraPromise = startCamera(options).finally(() => {
          startCameraPromise = null;
        });
      }
      return startCameraPromise;
    }

    function beginStartCamera(options={}) {
      const promise = runStartCamera(options);
      startCameraClickPromise = promise;
      promise.finally(() => {
        if (startCameraClickPromise === promise) startCameraClickPromise = null;
      });
      return promise;
    }

    function dispatchRemoteButtonClick(button) {
      button.classList.add('remote-click');
      const makeEvent = (name) => new Event(name, {bubbles: true, cancelable: true});
      try {
        button.dispatchEvent(makeEvent('pointerdown'));
        button.dispatchEvent(makeEvent('mousedown'));
        button.dispatchEvent(makeEvent('pointerup'));
        button.dispatchEvent(makeEvent('mouseup'));
        button.click();
      } finally {
        setTimeout(() => button.classList.remove('remote-click'), 450);
      }
    }

    async function clickStartCameraButton(payload={}) {
      if (Object.prototype.hasOwnProperty.call(payload || {}, 'startBest')) {
        startBest.checked = !!payload.startBest;
      }
      setState('URI click Start camera');
      dispatchRemoteButtonClick(startBtn);
      const status = await (startCameraClickPromise || beginStartCamera(payload || {}));
      return {ok: true, clicked: true, button: 'Start camera', uri: 'scanner://page/ui/button/start-camera/command/click', status};
    }

    function cameraTrack() {
      return stream && stream.getVideoTracks ? stream.getVideoTracks()[0] : null;
    }

    function torchInfo() {
      const track = cameraTrack();
      let supported = false;
      let settings = {};
      if (track) {
        try {
          const capabilities = track.getCapabilities ? track.getCapabilities() : {};
          supported = !!(capabilities && Object.prototype.hasOwnProperty.call(capabilities, 'torch'));
        } catch (_) {}
        try {
          settings = track.getSettings ? track.getSettings() : {};
        } catch (_) {}
      }
      return {
        supported,
        enabled: torchOn,
        ready: !!track,
        label: track ? track.label : '',
        settings: {torch: Object.prototype.hasOwnProperty.call(settings, 'torch') ? settings.torch : null}
      };
    }

    function refreshTorchButton() {
      const info = torchInfo();
      torchBtn.disabled = !info.supported;
      torchBtn.textContent = torchOn ? 'Light on' : 'Light off';
      torchBtn.className = torchOn ? 'primary' : '';
      return info;
    }

    async function setTorch(enabled=true) {
      if (!stream) {
        await runStartCamera({startBest: false});
      }
      const track = cameraTrack();
      if (!track) throw new Error('camera stream not ready');
      const capabilities = track.getCapabilities ? track.getCapabilities() : {};
      if (track.getCapabilities && !Object.prototype.hasOwnProperty.call(capabilities || {}, 'torch')) {
        refreshTorchButton();
        throw new Error('torch not supported by this browser/camera');
      }
      await track.applyConstraints({advanced: [{torch: !!enabled}]});
      torchOn = !!enabled;
      const info = refreshTorchButton();
      setState(torchOn ? 'light on' : 'light off');
      await announce('torch-changed', {enabled: torchOn, supported: info.supported});
      return {ok: true, uri: 'scanner://page/camera/command/torch', enabled: torchOn, torch: info, status: cameraStatus()};
    }

    async function clickTorchButton(payload={}) {
      if (!stream) {
        await runStartCamera({startBest: false});
      }
      const info = refreshTorchButton();
      if (!info.supported) throw new Error('torch not supported by this browser/camera');
      if (Object.prototype.hasOwnProperty.call(payload || {}, 'enabled')) {
        torchBtn.dataset.nextTorch = payload.enabled ? '1' : '0';
      }
      setState('URI click Light');
      dispatchRemoteButtonClick(torchBtn);
      const result = await (torchClickPromise || setTorch(Object.prototype.hasOwnProperty.call(payload || {}, 'enabled') ? !!payload.enabled : !torchOn));
      return {ok: true, clicked: true, button: 'Light', uri: 'scanner://page/ui/button/torch/command/click', result, status: cameraStatus()};
    }

    function sleep(ms) {
      return new Promise((resolve) => setTimeout(resolve, ms));
    }

    function waitForVideoReady(timeout=3000) {
      if (video.videoWidth && video.videoHeight) return Promise.resolve();
      return new Promise((resolve) => {
        let done = false;
        const finish = () => {
          if (done) return;
          done = true;
          video.removeEventListener('loadedmetadata', finish);
          video.removeEventListener('canplay', finish);
          resolve();
        };
        video.addEventListener('loadedmetadata', finish);
        video.addEventListener('canplay', finish);
        setTimeout(finish, timeout);
      });
    }

    async function sendFrame(options={}) {
      if (!stream) return;
      await waitForVideoReady();
      const w = video.videoWidth || 1920;
      const h = video.videoHeight || 1080;
      canvas.width = w;
      canvas.height = h;
      canvas.getContext('2d').drawImage(video, 0, 0, w, h);
      const quality = Number(document.getElementById('quality').value || '0.92');
      const image = canvas.toDataURL('image/jpeg', quality);
      return invokeURI('scanner://host/capture/command/run', {
        source: 'phone',
        image,
        width: w,
        height: h,
        userAgent: navigator.userAgent,
        capturedAt: new Date().toISOString(),
        ...options
      });
    }

    async function capture(options={}) {
      const w = video.videoWidth || 1920;
      const h = video.videoHeight || 1080;
      setState(`uploading ${w}x${h}...`);
      try {
        const data = await sendFrame({archive: true, ...options});
        if (!data || data.ok === false) throw new Error((data && data.error) || 'scan failed');
        if (data.rejected) {
          const sc = data.quality && data.quality.score != null ? Number(data.quality.score).toFixed(0) : '?';
          const reasons = data.quality && Array.isArray(data.quality.reasons) ? data.quality.reasons.join(', ') : '';
          const why = data.reason || reasons || 'low quality scan';
          setState(`discarded — ${why} (score ${sc}, min ${data.minScore})`, true);
          feedbackTone('error');
          return data;
        }
        const kind = captureFeedbackKind(data);
        const label = kind === 'duplicate' ? 'already saved' : kind === 'superseded' ? 'updated' : 'saved';
        const savedArtifact = data.primaryArtifact || data.documentArtifact || data.artifact || {};
        setState(`${label} ${savedArtifact.path || data.uri}`);
        feedbackTone(kind);
        return data;
      } catch (err) {
        feedbackTone('error');
        throw err;
      }
    }

    async function bestPdf(options={}) {
      if (!stream || bestRunning) return;
      bestRunning = true;
      bestBtn.disabled = true;
      captureBtn.disabled = true;
      const total = Number(options.count || document.getElementById('bestCount').value || '6');
      const intervalMs = scanIntervalMs(options);
      const seriesId = `best-${Date.now()}-${Math.random().toString(16).slice(2)}`;
      try {
        let best = null;
        for (let frame = 1; frame <= total; frame += 1) {
          setState(`frame ${frame}/${total}...`);
          const data = await sendFrame({
            archive: false,
            mode: 'best-candidate',
            seriesId,
            frameIndex: frame,
            frameCount: total
          });
          if (!data || data.ok === false) throw new Error((data && data.error) || 'candidate scan failed');
          best = data.series && data.series.best ? data.series.best : data.candidate;
          const score = best && best.quality ? Number(best.quality.score || 0).toFixed(1) : '0.0';
          setState(`frame ${frame}/${total}, best score ${score}`);
          if (frame < total) await sleep(intervalMs);
        }
        const minScore = Number(Object.prototype.hasOwnProperty.call(options || {}, 'minScore') ? options.minScore : numericParam('minScore', 45));
        const finalData = await invokeURI('scanner://host/best/command/finish', {seriesId, minScore});
        if (!finalData || finalData.ok === false) throw new Error((finalData && finalData.error) || 'best scan failed');
        const kind = captureFeedbackKind(finalData);
        const label = kind === 'duplicate' ? 'already saved' : kind === 'superseded' ? 'updated best' : 'saved best';
        setState(`${label} ${finalData.document && finalData.document.path ? finalData.document.path : finalData.uri}`);
        feedbackTone(kind);
        return finalData;
      } catch (err) {
        feedbackTone('error');
        throw err;
      } finally {
        bestRunning = false;
        bestBtn.disabled = !stream;
        captureBtn.disabled = !stream;
      }
    }

    function bestOptions(options={}) {
      return {
        count: Number(options.count || numericParam('count', Number(document.getElementById('bestCount').value || '6'))),
        minScore: Number(Object.prototype.hasOwnProperty.call(options || {}, 'minScore') ? options.minScore : numericParam('minScore', 45)),
        intervalMs: scanIntervalMs(options),
      };
    }

    function startAutoLoop(options={}) {
      clearInterval(timer);
      if (!auto.checked) return null;
      const run = () => {
        if (!stream || bestRunning) return;
        bestPdf(bestOptions(options)).catch((err) => setState(err.message, true));
      };
      timer = setInterval(run, scanIntervalMs(options));
      return timer;
    }

    async function beginAutonomousScanning(options={}) {
      auto.checked = Object.prototype.hasOwnProperty.call(options || {}, 'auto') ? !!options.auto : true;
      startBest.checked = Object.prototype.hasOwnProperty.call(options || {}, 'startBest') ? !!options.startBest : true;
      await announce('autonomous-start-requested', {auto: auto.checked, startBest: startBest.checked});
      const status = await runStartCamera({startBest: startBest.checked, ...bestOptions(options)});
      startAutoLoop(options);
      return {ok: true, uri: 'scanner://page/camera/command/autonomous', status, auto: auto.checked};
    }

    function cameraStatus() {
      const track = cameraTrack();
      return {
        ok: true,
        uri: 'scanner://page/camera/query/status',
        ready: !!stream,
        runningBest: bestRunning,
        width: video.videoWidth || 0,
        height: video.videoHeight || 0,
        torch: torchInfo(),
        track: track ? {label: track.label, readyState: track.readyState, enabled: track.enabled} : null,
        localActions: window.urirun && window.urirun.listActions ? window.urirun.listActions() : []
      };
    }

    function registerCameraActions() {
      if (!window.urirun || typeof window.urirun.registerAction !== 'function') return;
      window.urirun.registerAction('scanner://page/ui/button/start-camera/command/click', (payload) => clickStartCameraButton(payload || {}), {
        label: 'Click Start camera button', layer: 'page', kind: 'command', sideEffects: ['dom-click', 'camera-permission', 'media-stream']
      });
      window.urirun.registerAction('scanner://page/camera/command/start', (payload) => runStartCamera(payload || {}), {
        label: 'Start camera', layer: 'page', kind: 'command', sideEffects: ['camera-permission', 'media-stream']
      });
      window.urirun.registerAction('scanner://page/ui/button/torch/command/click', (payload) => clickTorchButton(payload || {}), {
        label: 'Click Light button', layer: 'page', kind: 'command', sideEffects: ['dom-click', 'camera-torch']
      });
      window.urirun.registerAction('scanner://page/camera/command/torch', (payload) => setTorch(!payload || !Object.prototype.hasOwnProperty.call(payload, 'enabled') ? true : !!payload.enabled), {
        label: 'Set camera light/torch', layer: 'page', kind: 'command', sideEffects: ['camera-torch']
      });
      window.urirun.registerAction('scanner://page/camera/command/scan', (payload) => capture(payload || {}), {
        label: 'Scan current frame', layer: 'page', kind: 'command', sideEffects: ['network', 'document-write']
      });
      window.urirun.registerAction('scanner://page/camera/command/best-pdf', (payload) => bestPdf(payload || {}), {
        label: 'Capture best PDF', layer: 'page', kind: 'command', sideEffects: ['camera-read', 'network', 'document-write']
      });
      window.urirun.registerAction('scanner://page/camera/command/autonomous', (payload) => beginAutonomousScanning(payload || {}), {
        label: 'Autonomous receipt/invoice scanning', layer: 'page', kind: 'command', sideEffects: ['camera-permission', 'camera-read', 'network', 'document-write']
      });
      window.urirun.registerAction('scanner://page/camera/query/status', () => cameraStatus(), {
        label: 'Camera page status', layer: 'page', kind: 'query', sideEffects: []
      });
      window.urirun.registerAction('scanner://page/actions/query/list', () => ({ok: true, actions: window.urirun.listActions()}), {
        label: 'List page actions', layer: 'page', kind: 'query', sideEffects: []
      });
      window.urirun.track('scanner_actions_ready', { count: window.urirun.listActions().length });
    }

    async function sendActionResult(action, result, error) {
      try {
        await fetch('/api/page/actions/result', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            id: action.id,
            target: action.target || 'scanner',
            uri: action.uri,
            ok: !error && (!result || result.ok !== false),
            error: error ? String(error.message || error) : '',
            result: result || null,
            at: new Date().toISOString()
          })
        });
      } catch (_) {}
    }

    function actionTimeoutMs(action) {
      const payload = action && action.payload ? action.payload : {};
      const raw = Number(payload.timeoutMs || payload.timeout || action.timeoutMs || 0);
      if (Number.isFinite(raw) && raw >= 1000) return Math.min(raw, 120000);
      const uri = action && action.uri ? String(action.uri) : '';
      if (uri.includes('/camera/command/best-pdf') || uri.includes('/camera/command/autonomous')) return 60000;
      if (uri.includes('/camera/command/start') || uri.includes('/ui/button/start-camera/command/click')) return 20000;
      return 15000;
    }

    function withActionTimeout(promise, action) {
      const timeoutMs = actionTimeoutMs(action);
      const uri = action && action.uri ? action.uri : 'page action';
      let timeoutId = null;
      const timeout = new Promise((_, reject) => {
        timeoutId = setTimeout(() => {
          reject(new Error(`page action timed out after ${timeoutMs}ms: ${uri}; keep the scanner tab visible and accept camera permission if prompted`));
        }, timeoutMs);
      });
      return Promise.race([promise, timeout]).finally(() => {
        if (timeoutId) clearTimeout(timeoutId);
      });
    }

    let _pollPageActionsInflight = false;
    async function pollPageActions() {
      if (_pollPageActionsInflight) return;
      if (!window.urirun || typeof window.urirun.invoke !== 'function') return;
      _pollPageActionsInflight = true;
      let data = null;
      try {
        const response = await fetch('/api/page/actions/poll?target=scanner&limit=4', {cache: 'no-store'});
        data = await response.json();
      } catch (_) {
        _pollPageActionsInflight = false;
        return;
      }
      const actions = data && Array.isArray(data.actions) ? data.actions : [];
      for (const action of actions) {
        try {
          setState(`URI ${action.uri}`);
          const result = await withActionTimeout(
            window.urirun.invoke(action.uri, action.payload || {}, {mode: action.mode || 'execute', localOnly: true}),
            action
          );
          await sendActionResult(action, result, null);
        } catch (err) {
          setState(err.message || String(err), true);
          await sendActionResult(action, null, err);
        }
      }
      _pollPageActionsInflight = false;
    }

    function applyInitialScannerOptions() {
      startBest.checked = truthyParam('best', startBest.checked);
      auto.checked = truthyParam('auto', auto.checked);
      const count = String(numericParam('count', Number(bestCount.value || '6')));
      if ([...bestCount.options].some((option) => option.value === count)) bestCount.value = count;
      const qualityValue = scannerParams.get('quality');
      if (qualityValue && [...quality.options].some((option) => option.value === qualityValue)) quality.value = qualityValue;
      syncIntervalControl();
    }

    applyInitialScannerOptions();
    announce('open', {autostart: truthyParam('autostart', false), auto: auto.checked, startBest: startBest.checked});
    registerCameraActions();
    setInterval(() => pollPageActions().catch(() => {}), 1000);
    window.addEventListener('pointerdown', unlockFeedbackAudio, {once: true, passive: true});
    window.addEventListener('touchstart', unlockFeedbackAudio, {once: true, passive: true});
    window.addEventListener('keydown', unlockFeedbackAudio, {once: true});
    startBtn.addEventListener('click', () => {
      unlockFeedbackAudio();
      beginStartCamera().catch((err) => {
        feedbackTone('error');
        setState(err.message, true);
      });
    });
    torchBtn.addEventListener('click', () => {
      const requested = Object.prototype.hasOwnProperty.call(torchBtn.dataset, 'nextTorch') ? torchBtn.dataset.nextTorch === '1' : !torchOn;
      delete torchBtn.dataset.nextTorch;
      const promise = setTorch(requested).catch((err) => setState(err.message, true));
      torchClickPromise = promise;
      promise.finally(() => {
        if (torchClickPromise === promise) torchClickPromise = null;
      });
    });
    captureBtn.addEventListener('click', () => {
      unlockFeedbackAudio();
      capture().catch((err) => setState(err.message, true));
    });
    bestBtn.addEventListener('click', () => {
      unlockFeedbackAudio();
      bestPdf().catch((err) => {
        bestRunning = false;
        bestBtn.disabled = !stream;
        captureBtn.disabled = !stream;
        setState(err.message, true);
      });
    });
    scanInterval.addEventListener('change', updateIntervalFromControl);
    scanInterval.addEventListener('blur', updateIntervalFromControl);
    auto.addEventListener('change', () => {
      if (auto.checked && !stream) {
        beginAutonomousScanning({auto: true, startBest: startBest.checked}).catch((err) => setState(err.message, true));
      } else {
        startAutoLoop();
      }
    });
    if (truthyParam('autostart', false)) {
      setTimeout(() => {
        beginAutonomousScanning({auto: auto.checked, startBest: startBest.checked}).catch((err) => {
          setState(`camera permission needed: ${err.message || err}`, true);
        });
      }, 350);
    }
  </script>
</body>
</html>
"""

