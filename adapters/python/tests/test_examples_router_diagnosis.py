# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Example flows must be diagnosable by the extracted URI router.

This is a workflow acceptance gate, not an execution test: it scans curated flow/scenario
YAML examples, builds a synthetic route catalogue from their own URIs, and asks
``urirun-connector-router`` to diagnose every step. That proves examples keep using URI
shapes the router can parse and place before any node/browser/hardware action runs.
"""
from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

from urirun_connector_router.routing import diagnose_plan, parse_uri  # noqa: E402


REPO = Path(__file__).resolve().parents[4]
EXCLUDED_PARTS = {"_site", "venv", "generated", ".state", "node_modules"}
FLOW_PATTERNS = (
    "examples/**/*.flow.yaml",
    "examples/**/flows/*.yaml",
    "examples/**/scenarios/*.yaml",
    "urirun/examples/**/*.yaml",
)
KNOWN_SAFETY_BLOCKED = {
    "examples/12-full_e2e_connect_lab/flows/user_scenario.yaml",
    "examples/34-all-connectors-flow/flows/install.flow.yaml",
}


def _example_flow_paths() -> list[Path]:
    paths: set[Path] = set()
    for pattern in FLOW_PATTERNS:
        paths.update(REPO.glob(pattern))
    return sorted(p for p in paths if not (EXCLUDED_PARTS & set(p.parts)))


def _steps(path: Path) -> list[dict]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(doc, dict):
        return []
    steps = doc.get("steps") or []
    return [s for s in steps if isinstance(s, dict) and s.get("uri")]


def _synthetic_mesh(steps: list[dict]) -> dict:
    nodes: dict[str, dict] = {}
    routes: list[dict] = []
    for step in steps:
        uri = str(step["uri"])
        target = str(parse_uri(uri).get("target") or "")
        if target and target not in ("host", "local"):
            nodes.setdefault(target, {"name": target, "url": f"http://{target}.invalid"})
        routes.append({
            "uri": uri,
            "safe": True,
            "adapter": "remote-node" if target not in ("", "host", "local") else "local-function",
        })
    return {"nodes": list(nodes.values()), "routes": routes}


def test_example_flows_are_router_diagnosable_before_execution():
    paths = _example_flow_paths()
    assert paths, "no example flow files found"

    checked = 0
    failures: list[str] = []
    for path in paths:
        steps = _steps(path)
        if not steps:
            continue
        checked += len(steps)
        report = diagnose_plan(steps, _synthetic_mesh(steps), probe=False)
        if report["ok"]:
            continue

        rel = str(path.relative_to(REPO))
        blocked = report.get("blockedSteps") or []
        blocked_layers = {b.get("blockedAt") for b in blocked}
        if rel in KNOWN_SAFETY_BLOCKED and blocked_layers == {"safety"}:
            continue
        failures.append(f"{rel}: {blocked[:5]}")

    assert checked >= 100
    assert not failures
