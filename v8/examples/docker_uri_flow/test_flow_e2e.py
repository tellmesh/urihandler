"""Docker-free end-to-end test for the cross-service URI flow.

It launches the three workers on ephemeral ports, points the orchestrator at
them with URI_SERVICE_MAP, and runs the real flow - so correctness is verifiable
in CI without Docker. The same code runs unchanged inside Compose (env unset ->
service DNS on port 8080).
"""

from __future__ import annotations

import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib import request

ROOT = Path(__file__).resolve().parent
FLOW = ROOT / "flows" / "cross_service_report.yaml"


def load_runner():
    spec = importlib.util.spec_from_file_location("flow_runner", ROOT / "orchestrator" / "flow_runner.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def start(cmd: list[str], port: int, extra_env: dict | None = None) -> subprocess.Popen:
    env = os.environ.copy()
    env["WORKER_PORT"] = str(port)
    env.update(extra_env or {})
    return subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_health(port: int, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with request.urlopen(f"http://127.0.0.1:{port}/health", timeout=0.3) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"worker on port {port} did not become healthy")


def run_e2e() -> dict:
    ports = {"python-worker": free_port(), "node-worker": free_port(), "shell-worker": free_port()}
    runner = load_runner()
    procs: list[subprocess.Popen] = []
    with tempfile.TemporaryDirectory() as reports:
        try:
            procs.append(start([sys.executable, str(ROOT / "python-worker" / "server.py")], ports["python-worker"]))
            procs.append(start(["node", str(ROOT / "node-worker" / "server.js")], ports["node-worker"]))
            procs.append(start([sys.executable, str(ROOT / "shell-worker" / "server.py")], ports["shell-worker"],
                               {"REPORT_DIR": reports}))
            for port in ports.values():
                wait_health(port)

            os.environ["URI_SERVICE_MAP"] = json.dumps(
                {host: f"http://127.0.0.1:{port}" for host, port in ports.items()})
            result = runner.run_flow(runner.parse_flow(FLOW))
        finally:
            os.environ.pop("URI_SERVICE_MAP", None)
            for proc in procs:
                proc.terminate()
            for proc in procs:
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()

        assert result["ok"], result
        report_path = Path(result["results"]["write_report"]["result"]["path"])
        assert report_path.exists(), f"report not written: {report_path}"
        assert "supplier-report-june-2026" in report_path.name
        assert result["results"]["summarize_report"]["result"]["ready"] is True
        assert "report=" in report_path.read_text(encoding="utf-8")
        return result


def test_cross_service_flow_runs_without_docker():
    run_e2e()


if __name__ == "__main__":
    run_e2e()
    print("PASS docker_uri_flow e2e (no docker)")
