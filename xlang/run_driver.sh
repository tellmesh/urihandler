#!/usr/bin/env bash
# External conformance driver: serve a REAL fs node, call routes over HTTP by their true URI,
# validate the transported response against the shared contracts.json.
set -euo pipefail
cd "$(dirname "$0")"
PY="${PY:-python}"
URIRUN="$(dirname "$PY")/urirun"
ND="$PWD/node"; WORK="$PWD/_work"
rm -rf "$ND" "$WORK"; mkdir -p "$ND" "$WORK"

cleanup() { [ -n "${NODE_PID:-}" ] && kill "$NODE_PID" 2>/dev/null || true; }
trap cleanup EXIT

echo "== emit + compile fs registry, serve a real node =="
$PY emit_contracts.py > contracts.json 2>/dev/null
$PY -c "import json,urirun_connector_fs.core as c; json.dump(c.urirun_bindings(), open('$ND/b.json','w'))"
$URIRUN compile "$ND/b.json" --out "$ND/registry.json" >/dev/null
PORT=$($PY -c "import socket;s=socket.socket();s.bind(('127.0.0.1',0));print(s.getsockname()[1]);s.close()")
$URIRUN node init --config "$ND/node.json" --name fsnode --registry "$ND/registry.json" \
  --host 127.0.0.1 --port "$PORT" --execute >/dev/null
$URIRUN node serve --config "$ND/node.json" --execute > "$ND/serve.log" 2>&1 &
NODE_PID=$!

# wait for health
for _ in $(seq 40); do
  if $PY -c "import urllib.request,sys; sys.exit(0 if __import__('json').loads(urllib.request.urlopen('http://127.0.0.1:$PORT/health',timeout=1).read()).get('ok') else 1)" 2>/dev/null; then break; fi
  sleep 0.25
done
echo "  node fsnode healthy on 127.0.0.1:$PORT"

echo
echo "== validate REAL wire responses against the shared contract =="
$PY driver.py "$PORT" "$WORK"
echo
echo "DONE: the served node's real over-the-wire responses conform; a lie on the wire is caught."
