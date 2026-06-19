"""Drive the workers through the library's `service` adapter (no bespoke code).

Shows the orchestrator's job expressed with `urihandler.v8_service`: the registry
validates input (schema) and the `service` adapter POSTs to the worker. Same
registry, gated, schema-checked - the worker images stay dependency-free.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib import request

from urihandler import v8, v8_service

ROOT = Path(__file__).resolve().parent


def registry() -> dict:
    bindings: dict = {}
    for worker in ("python-worker", "node-worker", "shell-worker"):
        doc = json.loads((ROOT / worker / "bindings.json").read_text(encoding="utf-8"))
        bindings.update(doc["bindings"])
    return v8.compile_registry({"bindings": bindings})


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_health(port: int, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with request.urlopen(f"http://127.0.0.1:{port}/health", timeout=0.3) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"worker on port {port} not healthy")


def test_dry_run_describes_the_http_call_without_network():
    env = v8_service.run("python://python-worker/text/normalize", registry(), payload={"text": "Hi"})
    assert env["ok"] is True
    assert env["result"]["simulated"] is True
    assert env["result"]["url"].endswith("/run")
    assert env["result"]["request"]["uri"] == "python://python-worker/text/normalize"


def test_schema_validation_runs_before_any_dispatch():
    env = v8_service.run("python://python-worker/text/normalize", registry(), payload={})  # missing required text
    assert env["ok"] is False
    assert env["error"]["type"] == "schema"


def test_service_adapter_calls_live_workers():
    ports = {"python-worker": free_port(), "node-worker": free_port()}
    procs = [
        subprocess.Popen([sys.executable, str(ROOT / "python-worker" / "server.py")],
                         env={**os.environ, "WORKER_PORT": str(ports["python-worker"])},
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
        subprocess.Popen(["node", str(ROOT / "node-worker" / "server.js")],
                         env={**os.environ, "WORKER_PORT": str(ports["node-worker"])},
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
    ]
    os.environ["URI_SERVICE_MAP"] = json.dumps({h: f"http://127.0.0.1:{p}" for h, p in ports.items()})
    try:
        for port in ports.values():
            wait_health(port)
        reg = registry()
        normalized = v8_service.call("python://python-worker/text/normalize", {"text": " Supplier Report "}, reg)
        assert normalized["ok"] is True
        assert normalized["result"]["result"]["normalized"] == "supplier report"

        slug = v8_service.call("node://node-worker/text/slugify", {"text": "Supplier Report June 2026"}, reg)
        assert slug["ok"] is True
        assert slug["result"]["result"]["slug"] == "supplier-report-june-2026"
    finally:
        os.environ.pop("URI_SERVICE_MAP", None)
        for proc in procs:
            proc.terminate()
        for proc in procs:
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    test_dry_run_describes_the_http_call_without_network()
    test_schema_validation_runs_before_any_dispatch()
    test_service_adapter_calls_live_workers()
    print("PASS docker_uri_flow service adapter")
