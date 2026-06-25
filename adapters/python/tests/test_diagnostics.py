# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# The experience playbook: a known failure signature -> a NAMED cause + a specific,
# partly auto-applicable remediation, surfaced through recovery_plan.diagnosis.
import unittest

from urirun.node import recovery
from urirun.node.diagnostics import diagnose


def _err(message, category="UNKNOWN"):
    return {"message": message, "category": category}


class DiagnoseTests(unittest.TestCase):
    def test_ui_target_not_located_routes_to_cdp_dom(self):
        d = diagnose(_err("ui-click: target not located (text='Post')"),
                     step={"uri": "kvm://laptop/ui/command/click"})
        self.assertEqual(d["rule"], "ui-target-not-located")
        # the fix is the OCR-immune DOM path, page-ready wait, and a retried orchestrated act
        auto = d["autoApplicable"]
        self.assertIn("ensure-cdp-dom", auto)
        self.assertIn("retry-via-act", auto)
        # actions are URIs templated on the failing node
        uris = [a.get("uri") for a in d["remediation"]]
        self.assertIn("kvm://laptop/cdp/session/command/ensure", uris)

    def test_no_onscreen_text_also_matches_ui_target(self):
        d = diagnose(_err("no on-screen text matches 'Opublikuj'"),
                     step={"uri": "kvm://laptop/ui/command/click-text"})
        self.assertEqual(d["rule"], "ui-target-not-located")

    def test_debugger_down_proposes_dedicated_profile(self):
        d = diagnose(_err("debugger did not come up"),
                     step={"uri": "browser://laptop/cdp/session/command/launch"})
        self.assertEqual(d["rule"], "cdp-debugger-down")
        self.assertEqual(d["autoApplicable"], ["ensure-cdp-dedicated-profile"])

    def test_node_exec_timeout(self):
        d = diagnose(_err("node error: TimeoutExpired: Command core:ui_wait timed out after 30 seconds",
                          category="DEADLINE_EXCEEDED"),
                     step={"uri": "kvm://laptop/ui/query/wait"})
        self.assertEqual(d["rule"], "node-exec-timeout")
        self.assertIn("retry-bounded", d["autoApplicable"])

    def test_route_not_served_gated_on_not_found(self):
        d = diagnose(_err("Route not found: kvm.doctor.query", category="NOT_FOUND"),
                     step={"uri": "kvm://laptop/doctor/query/report"})
        self.assertEqual(d["rule"], "route-not-served")
        self.assertIn("adopt-scheme", d["autoApplicable"])

    def test_route_not_served_category_gate(self):
        # without NOT_FOUND the route-not-served rule is skipped (no other rule matches here)
        self.assertIsNone(diagnose(_err("route not found", category="WEIRD"),
                                   step={"uri": "kvm://laptop/x/y/z"}))

    def test_empty_target(self):
        d = diagnose(_err("a target (text/name/role) is required"),
                     step={"uri": "kvm://laptop/ui/command/click"})
        self.assertEqual(d["rule"], "empty-ui-target")

    def test_no_match_returns_none(self):
        self.assertIsNone(diagnose(_err("something totally unrecognised")))
        self.assertIsNone(diagnose(_err("")))  # empty message never matches


class RecoveryPlanEnrichmentTests(unittest.TestCase):
    def test_plan_carries_diagnosis_when_signature_known(self):
        plan = recovery.recovery_plan(_err("ui-click: target not located"),
                                      step={"uri": "kvm://laptop/ui/command/click"})
        self.assertIn("diagnosis", plan)
        self.assertEqual(plan["diagnosis"]["rule"], "ui-target-not-located")
        # the legacy `actions` contract is untouched (still present)
        self.assertIn("actions", plan)

    def test_plan_omits_diagnosis_when_unknown(self):
        plan = recovery.recovery_plan(_err(""), step={"uri": "kvm://laptop/ui/command/click"})
        self.assertNotIn("diagnosis", plan)


if __name__ == "__main__":
    unittest.main()
