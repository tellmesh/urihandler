"""Faza 6: next.kind='acquire' wired into the thin-driver.

When a connector returns next:{kind:"acquire", acquire:{precondition:"..."}} the driver:
1. Calls ready://<node>/ready/command/ensure — if satisfied → retry → continue
2. If NOT satisfiable → surface blocked item, abort with ok=False + blocked dict
"""
from __future__ import annotations

from urirun.node import flow


def _mesh() -> dict:
    return {
        "serviceMap": {"laptop": "http://laptop.local:8766"},
        "routes": [
            {
                "uri": "kvm://laptop/screen/query/capture",
                "node": "laptop",
                "kind": "query",
                "adapter": "remote-node",
                "safe": True,
            }
        ],
    }


def _one_kvm_step() -> dict:
    return {
        "task": {"id": "t"},
        "steps": [{"id": "capture", "uri": "kvm://laptop/screen/query/capture",
                   "payload": {}, "depends_on": []}],
    }


def test_acquire_auto_satisfy_then_step_succeeds(monkeypatch):
    """next.kind=acquire + auto provider that fixes it → retry → flow succeeds."""
    calls = []

    def fake_call(uri, payload, registry, mode):
        calls.append(uri)
        if "screen/query/capture" in uri:
            if len([u for u in calls if "screen/query/capture" in u]) == 1:
                # First attempt: precondition not satisfied
                return {"uri": uri, "ok": False,
                        "next": {"kind": "acquire"},
                        "acquire": {"precondition": "portal-screen"}}
            # Retry after ensure: success
            return {"uri": uri, "ok": True, "result": {"value": {"ok": True}}}
        if "ready/command/ensure" in uri:
            # Auto provider satisfies the precondition
            return {"ok": True, "satisfied": True, "acquired": True,
                    "precondition": payload.get("precondition")}
        # twin drift/remember optional steps
        return {"ok": True, "result": {"value": {"ok": True}}}

    monkeypatch.setattr(flow.v2_service, "call", fake_call)
    result = flow.execute_flow(_one_kvm_step(), _mesh(), {}, execute=True)

    assert result["ok"] is True
    assert any("retry" in str(e.get("id", "")) for e in result["timeline"]), result["timeline"]
    ensure_calls = [u for u in calls if "ready/command/ensure" in u]
    assert len(ensure_calls) == 1, "ensure must be called exactly once"


def test_acquire_human_gated_blocks_flow(monkeypatch):
    """next.kind=acquire + human-gated precondition → flow aborts with blocked dict."""
    calls = []

    def fake_call(uri, payload, registry, mode):
        calls.append(uri)
        if "screen/query/capture" in uri:
            return {"uri": uri, "ok": False,
                    "next": {"kind": "acquire"},
                    "acquire": {"precondition": "portal-screen",
                                "hint": "Grant screen-capture in Settings > Privacy"}}
        if "ready/command/ensure" in uri:
            # Human-gated: cannot auto-satisfy
            return {"ok": False, "satisfied": False,
                    "next": {"kind": "acquire"},
                    "acquire": {"precondition": "portal-screen",
                                "humanGated": True,
                                "hint": "Grant screen-capture in Settings > Privacy"}}
        return {"ok": True, "result": {"value": {"ok": True}}}

    monkeypatch.setattr(flow.v2_service, "call", fake_call)
    result = flow.execute_flow(_one_kvm_step(), _mesh(), {}, execute=True)

    assert result["ok"] is False
    assert "blocked" in result, f"expected 'blocked' in result, got: {list(result.keys())}"
    assert result["blocked"].get("humanGated") is True
    assert "Grant screen-capture" in result["blocked"].get("hint", "")
    blocked_entries = [e for e in result["timeline"] if e.get("id", "").endswith(":blocked")]
    assert len(blocked_entries) == 1


def test_acquire_ensure_unreachable_blocks_flow(monkeypatch):
    """When ready:// ensure call itself fails (node unreachable) → treat as unresolvable."""
    calls = []

    def fake_call(uri, payload, registry, mode):
        calls.append(uri)
        if "screen/query/capture" in uri:
            return {"uri": uri, "ok": False,
                    "next": {"kind": "acquire"},
                    "acquire": {"precondition": "portal-screen"}}
        if "ready/command/ensure" in uri:
            # Ensure call fails (no route to node)
            return {"ok": False, "error": {"message": "no route to node"}}
        return {"ok": True, "result": {"value": {"ok": True}}}

    monkeypatch.setattr(flow.v2_service, "call", fake_call)
    result = flow.execute_flow(_one_kvm_step(), _mesh(), {}, execute=True)

    assert result["ok"] is False
    assert "blocked" in result or result.get("next", {}).get("kind") == "acquire"


def test_no_acquire_when_step_fails_without_next_kind(monkeypatch):
    """A plain failure without next.kind=acquire must NOT trigger the ensure path."""
    ensure_called = []

    def fake_call(uri, payload, registry, mode):
        if "ready/command/ensure" in uri:
            ensure_called.append(uri)
        if "screen/query/capture" in uri:
            return {"uri": uri, "ok": False, "error": {"message": "boom"}}
        return {"ok": True, "result": {"value": {"ok": True}}}

    monkeypatch.setattr(flow.v2_service, "call", fake_call)
    result = flow.execute_flow(_one_kvm_step(), _mesh(), {}, execute=True)

    assert result["ok"] is False
    assert ensure_called == [], "ensure must NOT be called for plain failures"
