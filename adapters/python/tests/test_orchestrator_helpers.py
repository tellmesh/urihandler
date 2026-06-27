"""Tests for chat_orchestrator helpers extracted for CC reduction."""
from __future__ import annotations

from urirun.host.chat_orchestrator import (
    _is_selected_remote_node,
    _flag_remote_capture_inline,
    _suggest_recall_for_memory,
)


# ── _is_selected_remote_node ──────────────────────────────────────────────────

def _node(name: str, url: str) -> dict:
    return {"name": name, "url": url}


def test_remote_node_in_sel_is_remote():
    assert _is_selected_remote_node(_node("lenovo", "http://192.168.1.10:8765"), {"lenovo"}) is True


def test_localhost_node_is_not_remote():
    assert _is_selected_remote_node(_node("host", "http://127.0.0.1:8765"), {"host"}) is False


def test_localhost_by_name_is_not_remote():
    assert _is_selected_remote_node(_node("host", "http://localhost:8765"), {"host"}) is False


def test_node_not_in_sel_is_not_remote():
    assert _is_selected_remote_node(_node("nas", "http://192.168.1.20:8765"), {"lenovo"}) is False


def test_empty_url_is_not_remote():
    assert _is_selected_remote_node({"name": "lenovo", "url": ""}, {"lenovo"}) is False


def test_nodeUrl_field_accepted():
    n = {"name": "lenovo", "nodeUrl": "http://192.168.1.10:8765"}
    assert _is_selected_remote_node(n, {"lenovo"}) is True


# ── _flag_remote_capture_inline ───────────────────────────────────────────────

def _discovered(nodes: list[dict], routes: list[dict] | None = None) -> dict:
    return {"nodes": nodes, "routes": routes or []}


def test_sets_base64_on_capture_step_for_remote_node():
    flow = {"steps": [{"uri": "kvm://lenovo/screen/query/capture", "payload": {}}]}
    disc = _discovered([_node("lenovo", "http://192.168.1.10:8765")])
    _flag_remote_capture_inline(flow, disc, ["lenovo"])
    assert flow["steps"][0]["payload"]["base64"] is True


def test_does_not_set_base64_for_localhost_node():
    flow = {"steps": [{"uri": "kvm://host/screen/query/capture", "payload": {}}]}
    disc = _discovered([_node("host", "http://127.0.0.1:8765")])
    _flag_remote_capture_inline(flow, disc, ["host"])
    assert "base64" not in flow["steps"][0]["payload"]


def test_does_not_set_base64_when_no_selected_nodes():
    flow = {"steps": [{"uri": "kvm://lenovo/screen/query/capture"}]}
    disc = _discovered([_node("lenovo", "http://192.168.1.10:8765")])
    _flag_remote_capture_inline(flow, disc, [])
    assert "base64" not in (flow["steps"][0].get("payload") or {})


def test_non_capture_steps_not_modified():
    flow = {"steps": [
        {"uri": "kvm://lenovo/ui/command/click", "payload": {}},
        {"uri": "kvm://lenovo/screen/query/capture", "payload": {}},
    ]}
    disc = _discovered([_node("lenovo", "http://192.168.1.10:8765")])
    _flag_remote_capture_inline(flow, disc, ["lenovo"])
    assert "base64" not in flow["steps"][0]["payload"]
    assert flow["steps"][1]["payload"]["base64"] is True


def test_creates_payload_dict_if_missing():
    flow = {"steps": [{"uri": "kvm://lenovo/screen/query/capture"}]}
    disc = _discovered([_node("lenovo", "http://192.168.1.10:8765")])
    _flag_remote_capture_inline(flow, disc, ["lenovo"])
    assert flow["steps"][0]["payload"]["base64"] is True


def test_empty_flow_steps_is_noop():
    flow = {"steps": []}
    disc = _discovered([_node("lenovo", "http://192.168.1.10:8765")])
    _flag_remote_capture_inline(flow, disc, ["lenovo"])  # no error


# ── _suggest_recall_for_memory ────────────────────────────────────────────────

def test_returns_none_when_twin_memory_is_none():
    assert _suggest_recall_for_memory({}, None) is None


def test_calls_suggest_recall_with_real_memory(monkeypatch):
    class _FakeMem:
        pass

    captured = {}

    def _fake_suggest_recall(flow, memory):
        captured["flow"] = flow
        captured["memory"] = memory
        return {"flowKey": "k1", "ts": 1}

    monkeypatch.setattr(
        "urirun.host.chat_orchestrator._suggest_recall_for_memory.__code__",
        _suggest_recall_for_memory.__code__,
    )
    import urirun.host.chat_orchestrator as orch
    original = None
    try:
        import urirun.node.flow as fl
        original = fl.suggest_recall
        fl.suggest_recall = _fake_suggest_recall
        result = _suggest_recall_for_memory({"steps": []}, _FakeMem())
        assert result == {"flowKey": "k1", "ts": 1}
        assert captured["flow"] == {"steps": []}
    finally:
        if original is not None:
            fl.suggest_recall = original
