# Author: Tom Sapletta · https://tom.sapletta.com
# The host CONSUMES the reversible engine: a normal execute_flow run becomes a transition
# registry (result["reversible"]), and rollback_flow undoes it LIFO over the inverses the
# connectors registered. Guards the wiring that turned dormant reversible.py into a live path.
from __future__ import annotations

from urirun.node import flow as F


def _execution_with_inverses():
    """A completed run where two steps' connectors returned a concrete inverse, plus a query
    (no inverse) and a self-heal marker (must be skipped by the ledger)."""
    return {
        "ok": True,
        "timeline": [
            {"id": "fill", "uri": "kvm://laptop/ui/command/fill", "ok": True},
            {"id": "nav", "uri": "kvm://laptop/cdp/page/command/navigate", "ok": True},
            {"id": "look", "uri": "kvm://laptop/ui/query/find", "ok": True},
            {"id": "fill:self-heal", "uri": "kvm://laptop/ui/command/fill", "ok": True, "type": "recovery"},
        ],
        "results": {
            "fill": {"result": {"value": {"ok": True, "did": "fill",
                     "inverse": {"uri": "kvm://laptop/ui/command/fill", "args": {"value": "OLD"}}}}},
            "nav": {"result": {"value": {"ok": True, "did": "nav",
                    "inverse": {"uri": "kvm://laptop/cdp/page/command/navigate", "args": {"url": "PREV"}}}}},
            "look": {"result": {"value": {"ok": True, "found": True}}},  # query: no inverse
        },
    }


def _mesh():
    return {"routes": [{"uri": "kvm://laptop/ui/command/fill"},
                       {"uri": "kvm://laptop/cdp/page/command/navigate"}],
            "serviceMap": {}, "nodes": [{"name": "laptop"}]}


def test_ledger_from_execution_skips_queries_and_recovery_markers():
    led = F.ledger_from_execution(_execution_with_inverses())
    # only the two real mutations with an inverse — the query and the self-heal marker are out
    assert [t.forward.uri for t in led] == [
        "kvm://laptop/ui/command/fill", "kvm://laptop/cdp/page/command/navigate"]
    assert led[1].inverse.uri == "kvm://laptop/cdp/page/command/navigate"


def test_rollback_flow_undoes_inverses_lifo(monkeypatch):
    calls = []
    monkeypatch.setattr(F.v2_service, "call",
                        lambda uri, payload, registry, mode="execute": calls.append((uri, payload))
                        or {"ok": True, "result": {"value": {"ok": True}}})
    rb = F.rollback_flow(_execution_with_inverses(), _mesh())
    assert rb["ok"] is True
    # LIFO: the navigate is undone before the fill, each with its captured prev value
    assert calls[0] == ("kvm://laptop/cdp/page/command/navigate", {"url": "PREV"})
    assert calls[1] == ("kvm://laptop/ui/command/fill", {"value": "OLD"})


def test_rollback_flow_escalates_on_failed_inverse(monkeypatch):
    def _call(uri, payload, registry, mode="execute"):
        ok = "navigate" not in uri          # the navigate inverse fails (API 500)
        return {"ok": ok, "result": {"value": {"ok": ok, "error": "boom"}}}
    monkeypatch.setattr(F.v2_service, "call", _call)
    rb = F.rollback_flow(_execution_with_inverses(), _mesh())
    assert rb["ok"] is False and "KNOWN-BAD" in rb["reason"]


def test_rollback_flow_noop_when_nothing_reversible(monkeypatch):
    monkeypatch.setattr(F.v2_service, "call", lambda *a, **k: {"ok": True})
    execution = {"ok": True, "timeline": [{"id": "q", "uri": "kvm://laptop/ui/query/find", "ok": True}],
                 "results": {"q": {"result": {"value": {"ok": True, "found": True}}}}}
    rb = F.rollback_flow(execution, _mesh())
    assert rb["ok"] is True and rb["undone"] == []


def test_run_flow_document_attaches_reversible_ledger(monkeypatch):
    # isolate the reversible-attach: stub execute_flow to a known run, neutralise the rest.
    monkeypatch.setattr(F, "execute_flow", lambda *a, **k: _execution_with_inverses())
    monkeypatch.setattr(F, "normalize_flow", lambda doc, uris: {"steps": doc.get("steps", [])})
    monkeypatch.setattr(F, "verify_flow_execution", lambda *a, **k: None)
    doc = {"steps": [{"id": "fill", "uri": "kvm://laptop/ui/command/fill", "payload": {}}]}
    result = F.run_flow_document(doc, _mesh(), execute=True)
    assert "reversible" in result
    assert result["reversible"]["rollbackable"] == 2
    fwds = [t["forward"] for t in result["reversible"]["transitions"]]
    assert "kvm://laptop/cdp/page/command/navigate" in fwds
