from __future__ import annotations

import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BINDINGS = json.loads((ROOT / "bindings.json").read_text(encoding="utf-8"))


def response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    data = json.dumps(payload, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def dispatch(uri: str, payload: dict) -> dict:
    if uri != "shell://shell-worker/report/write":
        return {"ok": False, "service": "shell-worker", "uri": uri, "error": "route not found"}
    completed = subprocess.run(
        ["/bin/sh", str(ROOT / "write_report.sh"), str(payload["slug"]), str(payload["text"])],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    path = completed.stdout.strip()
    return {
        "ok": completed.returncode == 0,
        "service": "shell-worker",
        "uri": uri,
        "result": {"path": path, "exitCode": completed.returncode, "stderr": completed.stderr},
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/routes":
            response(self, 200, {"ok": True, "service": "shell-worker", "bindings": BINDINGS["bindings"]})
            return
        if self.path == "/health":
            response(self, 200, {"ok": True, "service": "shell-worker"})
            return
        response(self, 404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/run":
            response(self, 404, {"ok": False, "error": "not found"})
            return
        length = int(self.headers.get("Content-Length") or "0")
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        result = dispatch(str(body["uri"]), body.get("payload") or {})
        response(self, 200 if result.get("ok") else 404, result)


ThreadingHTTPServer(("0.0.0.0", int(os.getenv("WORKER_PORT", "8080"))), Handler).serve_forever()
