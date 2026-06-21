"""Tests for `urirun agent` (action space + planner loop)."""

from __future__ import annotations

import sys

import urirun
from urirun.runtime import agent


def _registry():
    emit_json = [sys.executable, "-c", "print('{\"ok\": true, \"v\": 1}')"]
    doc = {
        "version": "urirun.bindings.v2",
        "bindings": {
            "demo://host/thing/query/read": {
                "adapter": "argv-template", "kind": "command", "argv": emit_json,
                "inputSchema": {"type": "object", "additionalProperties": False, "properties": {}},
                "meta": {"connector": "demo", "label": "read"}, "uri": "demo://host/thing/query/read",
            },
            "demo://host/thing/command/write": {
                "adapter": "argv-template", "kind": "command", "argv": emit_json,
                "inputSchema": {"type": "object", "additionalProperties": False, "properties": {}},
                "meta": {"connector": "demo", "label": "write"}, "uri": "demo://host/thing/command/write",
            },
        },
    }
    return urirun.compile_registry(doc)


def test_action_space_marks_query_and_command():
    space = {r["uri"]: r for r in agent.action_space(_registry())}
    assert space["demo://host/thing/query/read"]["kind"] == "query"
    assert space["demo://host/thing/command/write"]["kind"] == "command"


def test_run_plan_runs_query_and_gates_command():
    registry = _registry()
    steps = [
        {"uri": "demo://host/thing/query/read", "payload": {}},
        {"uri": "demo://host/thing/command/write", "payload": {}},
    ]
    trace = agent.run_plan(registry, steps, allow_commands=False)
    read, write = trace
    assert read["ran"] is True and read["ok"] is True and read["data"]["v"] == 1
    assert write["ran"] is False  # command gated


def test_run_plan_allows_command_with_permission():
    registry = _registry()
    trace = agent.run_plan(registry, [{"uri": "demo://host/thing/command/write", "payload": {}}], allow_commands=True)
    assert trace[0]["ran"] is True and trace[0]["ok"] is True


def test_load_planner_resolves_module_function():
    fn = agent._load_planner("urirun.runtime.agent:action_space")
    assert fn is agent.action_space
