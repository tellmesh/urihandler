# Author: Tom Sapletta · https://tom.sapletta.com
# Guards the execute_flow ↔ TwinMemory wiring: a known-good environment profile is captured once
# after preflight, and drift is recorded as a timeline entry (diagnosis only — never aborts).
from __future__ import annotations

from urirun.node import flow as F
from urirun.node.reversible import TwinMemory


def _mesh():
    return {"routes": [{"uri": "kvm://laptop/cdp/page/command/navigate"}],
            "serviceMap": {}, "nodes": [{"name": "laptop"}]}


def _profile(platform="linux", wayland=True, best="cdp", monitors=None):
    return {"platform": platform, "wayland": wayland,
            "monitors": monitors if monitors is not None else [{"w": 1920, "h": 1080}],
            "best": best, "osLevelReliable": True, "controlStrategies": {"cdp": "feasible"}}


def _flow():
    return {"steps": [
        {"id": "s1", "uri": "kvm://laptop/cdp/page/command/navigate", "payload": {"url": "https://x"}},
    ]}


def test_kvm_targets_collects_distinct_cdp_and_kvm_nodes_only():
    flow = {"steps": [
        {"id": "a", "uri": "kvm://laptop/cdp/page/command/navigate"},
        {"id": "b", "uri": "kvm://laptop/cdp/page/command/click"},   # same target, deduped
        {"id": "c", "uri": "kvm://desktop/ui/command/fill"},         # different kvm target
        {"id": "d", "uri": "host://host/api/summary"},               # not kvm-controlled -> ignored
    ]}
    assert F._kvm_targets(flow) == ["laptop", "desktop"]


def test_capture_known_good_stores_profile_per_target(monkeypatch):
    seen = []
    def _call(uri, payload, registry, mode="execute"):
        seen.append(uri)
        if "env/query/profile" in uri:
            return {"ok": True, "result": {"value": _profile()}}
        return {"ok": True, "result": {"value": {"ok": True}}}
    monkeypatch.setattr(F.v2_service, "call", _call)
    mem = TwinMemory()
    F._capture_known_good(_flow(), {}, mem)
    assert mem.known_good("laptop") is not None
    assert mem.known_good("laptop")["snapshot"]["platform"] == "linux"
    # the capture probed env/query/profile exactly once per target
    assert sum("env/query/profile" in u for u in seen) == 1


def test_capture_known_good_skips_targets_that_wont_answer(monkeypatch):
    def _call(uri, payload, registry, mode="execute"):
        if "env/query/profile" in uri:
            return {"ok": False, "error": "unreachable"}   # doctor down
        return {"ok": True, "result": {"value": {"ok": True}}}
    monkeypatch.setattr(F.v2_service, "call", _call)
    mem = TwinMemory()
    F._capture_known_good(_flow(), {}, mem)
    # no baseline recorded, but no exception raised either — best-effort contract
    assert mem.known_good("laptop") is None


def test_drift_timeline_emits_entry_when_environment_changed(monkeypatch):
    first = {"prof": _profile(monitors=[{"w": 1920, "h": 1080}])}
    def _call(uri, payload, registry, mode="execute"):
        if "env/query/profile" in uri:
            return {"ok": True, "result": {"value": first["prof"]}}
        return {"ok": True, "result": {"value": {"ok": True}}}
    monkeypatch.setattr(F.v2_service, "call", _call)
    mem = TwinMemory()
    F._capture_known_good(_flow(), {}, mem)         # baseline = 1 monitor
    first["prof"] = _profile(monitors=[{"w": 1920, "h": 1080}, {"w": 1080, "h": 1920}])  # drift: 2 monitors
    entries = F._drift_timeline(_flow(), {}, mem)
    assert len(entries) == 1
    assert entries[0]["target"] == "laptop"
    assert entries[0]["action"] == "environment-drift"
    assert entries[0]["drift"]["drifted"] is True


def test_drift_timeline_empty_when_matches_known_good(monkeypatch):
    def _call(uri, payload, registry, mode="execute"):
        if "env/query/profile" in uri:
            return {"ok": True, "result": {"value": _profile()}}
        return {"ok": True, "result": {"value": {"ok": True}}}
    monkeypatch.setattr(F.v2_service, "call", _call)
    mem = TwinMemory()
    F._capture_known_good(_flow(), {}, mem)
    assert F._drift_timeline(_flow(), {}, mem) == []


def test_execute_flow_with_memory_does_not_abort_on_drift(monkeypatch):
    """The contract: drift is diagnosed, never fatal. A drifted run still returns ok and runs its
    steps; the operator/recovery layer decides what a drift means — the flow itself doesn't bail."""
    state = {"prof": _profile(monitors=[{"w": 1920, "h": 1080}])}
    def _call(uri, payload, registry, mode="execute"):
        if "env/query/profile" in uri:
            return {"ok": True, "result": {"value": state["prof"]}}
        return {"ok": True, "result": {"value": {"ok": True, "url": payload.get("url")}}}
    monkeypatch.setattr(F.v2_service, "call", _call)
    mem = TwinMemory()
    # first run establishes the baseline
    F.execute_flow(_flow(), _mesh(), {}, execute=True, recover=False, memory=mem)
    # second run sees a drifted environment
    state["prof"] = _profile(monitors=[{"w": 1920, "h": 1080}, {"w": 1080, "h": 1920}])
    out = F.execute_flow(_flow(), _mesh(), {}, execute=True, recover=False, memory=mem)
    assert out["ok"] is True                          # did NOT abort
    drifts = [e for e in out["timeline"] if e.get("action") == "environment-drift"]
    assert len(drifts) == 1
    assert drifts[0]["drift"]["drifted"] is True


def test_execute_flow_without_memory_is_a_noop_for_twin(monkeypatch):
    """Backward compatibility: callers that don't pass a memory see no twin machinery at all —
    no extra profile probes, no drift entries, identical behavior to before the wiring existed."""
    probes = []
    def _call(uri, payload, registry, mode="execute"):
        if "env/query/profile" in uri:
            probes.append(uri)
        return {"ok": True, "result": {"value": {"ok": True}}}
    monkeypatch.setattr(F.v2_service, "call", _call)
    out = F.execute_flow(_flow(), _mesh(), {}, execute=True, recover=False)
    assert out["ok"] is True
    assert probes == []                               # no doctor probe when memory is None
    assert not any(e.get("action") == "environment-drift" for e in out["timeline"])
