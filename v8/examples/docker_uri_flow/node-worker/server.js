const http = require('node:http');
const fs = require('node:fs');

const bindings = JSON.parse(fs.readFileSync('/app/bindings.json', 'utf8'));

function send(res, status, payload) {
  const data = JSON.stringify(payload, null, 2);
  res.writeHead(status, { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) });
  res.end(data);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', (chunk) => { data += chunk; });
    req.on('end', () => resolve(data ? JSON.parse(data) : {}));
    req.on('error', reject);
  });
}

function slugify(text) {
  return String(text)
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

const server = http.createServer(async (req, res) => {
  if (req.method === 'GET' && req.url === '/routes') {
    send(res, 200, { ok: true, service: 'node-worker', bindings: bindings.bindings });
    return;
  }
  if (req.method === 'GET' && req.url === '/health') {
    send(res, 200, { ok: true, service: 'node-worker' });
    return;
  }
  if (req.method === 'POST' && req.url === '/run') {
    const body = await readBody(req);
    if (body.uri !== 'node://node-worker/text/slugify') {
      send(res, 404, { ok: false, service: 'node-worker', uri: body.uri, error: 'route not found' });
      return;
    }
    const slug = slugify(body.payload?.text || '');
    send(res, 200, { ok: true, service: 'node-worker', uri: body.uri, result: { slug } });
    return;
  }
  send(res, 404, { ok: false, error: 'not found' });
});

server.listen(8080, '0.0.0.0');
