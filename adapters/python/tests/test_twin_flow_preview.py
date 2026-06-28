from __future__ import annotations

import sys
import types

from urirun.host.twin_bridge import twin_flow_preview


def test_twin_flow_preview_overlays_router_env_domain_violation(monkeypatch):
    module = types.ModuleType("urirun_connector_twin.core")

    def plan_generate(flow, prompt="", node="", include_mock=False):
        return {
            "ok": True,
            "environment": {"node": node, "bestSurface": "cdp"},
            "plan": {
                "prompt": prompt,
                "node": node,
                "steps": [{
                    "step": 1,
                    "id": "capture",
                    "uri": "kvm://host/screen/query/capture",
                    "payload": {"monitor": 99},
                    "feasible": True,
                    "reversible": True,
                }],
                "totalSteps": 1,
                "feasibleSteps": 1,
                "infeasibleSteps": 0,
                "needsMock": False,
            },
        }

    module.plan_generate = plan_generate
    monkeypatch.setitem(sys.modules, "urirun_connector_twin.core", module)

    preview = twin_flow_preview(
        "zrob zrzut ekranu 99 monitora",
        {
            "task": {"source": "litellm"},
            "steps": [{
                "id": "capture",
                "uri": "kvm://host/screen/query/capture",
                "payload": {"monitor": 99},
            }],
        },
        node="host",
        routing_report={
            "accepted": False,
            "violations": [{
                "kind": "env-domain-invalid",
                "uri": "kvm://host/screen/query/capture",
                "parameter": "monitor",
                "value": 99,
                "allowed": [1, 2, 3],
            }],
        },
    )

    step = preview["plan"]["steps"][0]
    assert preview["taskType"] == "litellm"
    assert preview["plan"]["feasibleSteps"] == 0
    assert preview["plan"]["infeasibleSteps"] == 1
    assert step["feasible"] is False
    assert step["blocked_by"] == "env-domain-invalid"
    assert step["routingViolations"][0]["allowed"] == [1, 2, 3]
