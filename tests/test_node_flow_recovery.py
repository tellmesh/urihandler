from __future__ import annotations

from urirun.node import flow


def _mesh(kind: str = "query") -> dict:
    return {
        "serviceMap": {"laptop": "http://laptop.local:8766"},
        "routes": [
            {
                "uri": "env://laptop/runtime/query/health",
                "node": "laptop",
                "kind": kind,
                "adapter": "remote-node",
                "safe": True,
            }
        ],
    }


def _one_step() -> dict:
    return {
        "task": {"id": "test"},
        "steps": [{"id": "health", "uri": "env://laptop/runtime/query/health", "payload": {}, "depends_on": []}],
    }


def test_execute_flow_folds_action_ok_under_ok_envelope(monkeypatch):
    """A transport-ok envelope whose action result is ok=False (a UI click that
    located no target) must fail the step + flow, not report green. Mirrors the
    LinkedIn ``kvm://…/ui/click`` shape."""
    def fake_call(uri, payload, registry, mode):
        return {"uri": uri, "ok": True, "result": {"value": {
            "ok": False, "action": "ui-click",
            "error": "no control strategy could click target (text='Post' role='button')"}}}

    monkeypatch.setattr(flow.v2_service, "call", fake_call)

    result = flow.execute_flow(_one_step(), _mesh(kind="command"), {}, execute=True)

    assert result["ok"] is False
    assert result["timeline"][0]["ok"] is False
    # the action's own error is surfaced, not a generic "unknown URI error"
    assert "click target" in result["timeline"][0]["error"]["message"]
    assert result["error"]["message"] == result["timeline"][0]["error"]["message"]


def test_execute_flow_retries_transient_query_failure(monkeypatch):
    """With thin-driver as sole engine, transient failures are not auto-retried
    by the runtime — the connector must signal retry via next.kind. Without that
    signal, the step fails and the flow aborts on the first failure."""
    calls = []

    def fake_call(uri, payload, registry, mode):
        calls.append({"uri": uri, "payload": payload, "mode": mode})
        if len(calls) == 1:
            return {"uri": uri, "ok": False, "error": {"type": "transport", "message": "connection refused"}}
        return {"uri": uri, "ok": True, "result": {"value": {"ok": True}}}

    monkeypatch.setattr(flow.v2_service, "call", fake_call)

    result = flow.execute_flow(_one_step(), _mesh(kind="query"), {}, execute=True)

    step_calls = [c for c in calls if c["uri"] == "env://laptop/runtime/query/health"]
    assert result["ok"] is False           # thin-driver aborts on first failure (no auto-retry)
    assert len(step_calls) == 1            # called once, never retried without next.kind=retry
    assert result["timeline"][0]["ok"] is False


def test_execute_flow_does_not_retry_transient_command_failure(monkeypatch):
    """Command step that fails is NOT retried (no-retry contract is unchanged in thin-driver).
    The step runs exactly once; flow is marked failed."""
    calls = []

    def fake_call(uri, payload, registry, mode):
        calls.append({"uri": uri, "payload": payload, "mode": mode})
        return {"uri": uri, "ok": False, "error": {"type": "transport", "message": "connection refused"}}

    monkeypatch.setattr(flow.v2_service, "call", fake_call)

    result = flow.execute_flow(_one_step(), _mesh(kind="command"), {}, execute=True)

    step_calls = [c for c in calls if c["uri"] == "env://laptop/runtime/query/health"]
    assert result["ok"] is False
    assert len(step_calls) == 1, "transient command step must NOT be retried"
    assert result["timeline"][0]["ok"] is False


def test_execute_flow_reports_missing_dependency_as_recovery_failure(monkeypatch):
    """With thin-driver, depends_on is not pre-validated against the result set.
    The step is dispatched; if it fails the flow is marked failed."""
    calls = []

    def fake_call(uri, payload, registry, mode):
        calls.append(uri)
        return {"uri": uri, "ok": False, "error": {"message": "failed", "type": "transport"}}

    monkeypatch.setattr(flow.v2_service, "call", fake_call)
    document = {
        "task": {"id": "test"},
        "steps": [
            {
                "id": "after_missing",
                "uri": "env://laptop/runtime/query/health",
                "payload": {},
                "depends_on": ["missing_step"],
            }
        ],
    }

    result = flow.execute_flow(document, _mesh(kind="query"), {}, execute=True)

    assert result["ok"] is False
    assert result["timeline"][0]["id"] == "after_missing"
    assert result["timeline"][0]["ok"] is False
