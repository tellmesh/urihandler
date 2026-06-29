from __future__ import annotations

import json

from urirun.node.transport import (
    _annotate_deploy_allow_compat,
    _deploy_allow_list,
    _parse_sse_line,
    discover_node,
    event_topic,
    parse_ports,
)


# ─── parse_ports ─────────────────────────────────────────────────────────────

def test_parse_ports_single():
    assert parse_ports("8765") == [8765]


def test_parse_ports_csv():
    assert parse_ports("8765,8766,8767") == [8765, 8766, 8767]


def test_parse_ports_range():
    assert parse_ports("8760-8763") == [8760, 8761, 8762, 8763]


def test_parse_ports_mixed():
    result = parse_ports("8765,8770-8772")
    assert result == [8765, 8770, 8771, 8772]


def test_parse_ports_single_range_endpoint():
    assert parse_ports("9000-9000") == [9000]


# ─── _deploy_allow_list ──────────────────────────────────────────────────────

def test_deploy_allow_list_from_top_level():
    data = {"allow": ["env://", "fs://"]}
    assert _deploy_allow_list(data) == ["env://", "fs://"]


def test_deploy_allow_list_from_policy():
    data = {"policy": {"allow": ["shell://"]}}
    assert _deploy_allow_list(data) == ["shell://"]


def test_deploy_allow_list_none_when_absent():
    assert _deploy_allow_list({}) is None
    assert _deploy_allow_list(None) is None
    assert _deploy_allow_list("string") is None


# ─── _annotate_deploy_allow_compat ───────────────────────────────────────────

def test_annotate_no_warning_when_all_present():
    before = {"allow": ["env://"]}
    result = {"ok": True, "allow": ["env://", "fs://"]}
    out = _annotate_deploy_allow_compat(result, merge=True, before=before, requested_allow=["fs://"])
    assert "warnings" not in out


def test_annotate_warns_when_merge_drops_entry():
    before = {"allow": ["env://"]}
    result = {"ok": True, "allow": ["fs://"]}
    out = _annotate_deploy_allow_compat(result, merge=True, before=before, requested_allow=["fs://"])
    warnings = out.get("warnings", [])
    assert any(w.get("code") == "DEPLOY_ALLOW_MERGE_MISMATCH" for w in warnings)
    assert "env://" in out["warnings"][0]["missingAllow"]


def test_annotate_skips_when_merge_false():
    before = {"allow": ["env://"]}
    result = {"ok": True, "allow": ["fs://"]}
    out = _annotate_deploy_allow_compat(result, merge=False, before=before, requested_allow=["fs://"])
    assert "warnings" not in out


def test_annotate_skips_when_not_ok():
    before = {"allow": ["env://"]}
    result = {"ok": False, "allow": ["fs://"]}
    out = _annotate_deploy_allow_compat(result, merge=True, before=before, requested_allow=["env://"])
    assert "warnings" not in out


# ─── _parse_sse_line ─────────────────────────────────────────────────────────

def test_parse_sse_line_data():
    line = 'data: {"event": "run", "uri": "env://node/x"}'
    new_id, ev = _parse_sse_line(line, 5)
    assert ev is not None
    assert ev["event"] == "run"
    assert ev["_id"] == 5


def test_parse_sse_line_id_updates_cursor():
    new_id, ev = _parse_sse_line("id: 42", 0)
    assert new_id == 42
    assert ev is None


def test_parse_sse_line_blank_no_event():
    new_id, ev = _parse_sse_line("", 3)
    assert new_id == 3
    assert ev is None


def test_parse_sse_line_malformed_json_ignored():
    new_id, ev = _parse_sse_line("data: {not json}", 7)
    assert new_id == 7
    assert ev is None


def test_parse_sse_line_empty_data_ignored():
    new_id, ev = _parse_sse_line("data:  ", 1)
    assert ev is None


# ─── event_topic ─────────────────────────────────────────────────────────────

def test_event_topic_includes_prefix_node_event_scheme():
    ev = {"node": "laptop", "event": "run", "uri": "env://laptop/runtime/query/health"}
    topic = event_topic("urirun/events", ev)
    assert topic.startswith("urirun/events/laptop/run")
    assert "env" in topic


def test_event_topic_fallbacks_when_missing():
    topic = event_topic("urirun/events", {})
    assert topic.startswith("urirun/events/")
    assert "node" in topic


def test_event_topic_uses_service_when_no_node():
    ev = {"service": "dashboard", "event": "error"}
    topic = event_topic("urirun/events", ev)
    assert "dashboard" in topic


# ─── discover_node ──────────────────────────────────────────────────────────

def test_discover_node_treats_health_ok_false_as_unreachable(monkeypatch):
    def fake_http_json(method, url, **kwargs):
        if url.endswith("/health"):
            return {"ok": False, "error": "unknown device"}
        if url.endswith("/routes"):
            return {"routes": [{"uri": "webpage://web1/page/query/info"}]}
        return {"ok": False, "error": "not found"}

    monkeypatch.setattr("urirun.node.transport.http_json", fake_http_json)

    node = discover_node({
        "name": "android-web1",
        "url": "http://host:8195/api/webpage-node/relay/web1",
        "kind": "webpage",
    })

    assert node["reachable"] is False
    assert node["health"] == {"ok": False, "error": "unknown device"}
    assert node["routes"] == []
    assert node["error"] == "unknown device"
