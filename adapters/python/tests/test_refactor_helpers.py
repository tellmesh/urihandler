# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Targeted unit tests for the pure helpers produced by the CC-reduction refactor.

These lock in the behaviour of the extracted helpers that are not exercised by an
end-to-end path elsewhere: the recovery-action dispatch, the document-frame quality
scorers, the document-sync decision loop, and the dashboard /api routing table.
"""
import unittest

from urirun import host_dashboard
from urirun.node import recovery


class RecoveryActionsDispatchTests(unittest.TestCase):
    """recovery_actions was refactored from a long if/elif into category dispatch."""

    def _ids(self, error, **kw):
        return [a["id"] for a in recovery.recovery_actions(error, **kw)]

    def test_transient_categories_retry_and_refresh(self):
        for cat in ("UNAVAILABLE", "DEADLINE_EXCEEDED"):
            ids = self._ids({"category": cat, "message": ""})
            self.assertIn("retry-transient-step", ids)
            self.assertIn("refresh-discovery", ids)

    def test_transient_with_target_adds_health_check(self):
        ids = self._ids({"category": "UNAVAILABLE", "message": ""},
                        step={"uri": "proc://node1/process/query/list"})
        self.assertEqual(ids[0], "check-target-health")

    def test_auth_categories(self):
        for cat in ("UNAUTHENTICATED", "PERMISSION_DENIED"):
            self.assertEqual(self._ids({"category": cat, "message": ""}), ["authorize-target"])

    def test_not_found_route_vs_resource(self):
        route = self._ids({"category": "NOT_FOUND", "message": "route not found", "type": "registry"},
                          step={"uri": "fs://host/file/command/write"})
        self.assertIn("refresh-routes", route)
        self.assertIn("resolve-connector", route)  # scheme present
        resource = self._ids({"category": "NOT_FOUND", "message": "file gone"})
        self.assertEqual(resource, ["mark-missing-resource"])

    def test_single_action_categories(self):
        self.assertEqual(self._ids({"category": "INVALID_ARGUMENT", "message": ""}), ["repair-payload"])
        self.assertEqual(self._ids({"category": "FAILED_PRECONDITION", "message": ""}), ["prepare-precondition"])

    def test_llm_model_message_overrides_category(self):
        self.assertEqual(self._ids({"category": "UNAVAILABLE", "message": "URIRUN_LLM_MODEL not set"}),
                         ["use-known-intent-or-configure-llm"])

    def test_unknown_category_falls_back_to_inspect(self):
        self.assertEqual(self._ids({"category": "WEIRD", "message": ""}), ["inspect-error"])

    def test_actions_are_fresh_copies(self):
        # the static-category dispatch must not hand callers a shared mutable dict
        a = recovery.recovery_actions({"category": "INVALID_ARGUMENT", "message": ""})
        a[0]["mutated"] = True
        b = recovery.recovery_actions({"category": "INVALID_ARGUMENT", "message": ""})
        self.assertNotIn("mutated", b[0])


class DocumentFrameQualityTests(unittest.TestCase):
    """_document_frame_quality was split into one scorer per signal; verify they compose."""

    BAD_IMG = "/nonexistent-frame-for-tests.jpg"  # → visual metrics ok:False → visual score 0

    def test_strong_document_scores_and_reasons(self):
        q = host_dashboard._document_frame_quality(
            {"ok": True, "bboxArea": 0.42, "width": 300, "height": 500},
            {"ok": True, "chars": 200, "text": "x" * 200},
            {"type": "paragon", "date": "2026-01-01", "amount": "12,50"},
            self.BAD_IMG,
        )
        self.assertTrue(q["documentLike"])
        self.assertGreater(q["score"], 100)
        for reason in ("crop", "size", "paragon", "date", "amount", "ocr"):
            self.assertIn(reason, q["reasons"])

    def test_rejected_crop_is_floored_at_zero(self):
        q = host_dashboard._document_frame_quality(
            {"ok": False, "partialEdge": True}, {"ok": False}, {}, self.BAD_IMG)
        self.assertEqual(q["score"], 0.0)
        self.assertFalse(q["documentLike"])
        self.assertEqual(q["reasons"], ["partial-edge"])

    def test_crop_scorer_isolated(self):
        reasons = []
        self.assertEqual(host_dashboard._crop_quality_score({"ok": True}, reasons), 42.0)
        self.assertEqual(reasons, ["crop"])
        reasons2 = []
        self.assertEqual(host_dashboard._crop_quality_score({"ok": False, "reason": "blur"}, reasons2), -20.0)
        self.assertEqual(reasons2, ["crop-rejected"])

    def test_doctype_scorer_tiers(self):
        self.assertEqual(host_dashboard._doctype_quality_score("paragon", []), 32.0)
        self.assertEqual(host_dashboard._doctype_quality_score("rachunek", []), 20.0)
        self.assertEqual(host_dashboard._doctype_quality_score("umowa", []), 10.0)
        self.assertEqual(host_dashboard._doctype_quality_score("dokument", []), 0.0)


class DecisionLoopTests(unittest.TestCase):
    """_decision_loop_for_document_sync was split into status/nextIntent/observation builders."""

    def _loop(self, **kw):
        base = dict(prompt="send docs to node", sync_node="n1",
                    selected_nodes=["n1"], selected_targets=["node:n1"], flow={"id": "f"}, timeline=[])
        base.update(kw)
        return host_dashboard._decision_loop_for_document_sync(**base)

    def test_dry_run(self):
        dl = self._loop(execute=False)
        self.assertEqual(dl["execution"]["status"], "dry-run")
        self.assertEqual(dl["nextIntent"]["id"], "execute-document-sync")
        self.assertEqual(dl["observation"]["kind"], "dry-run")

    def test_completed(self):
        dl = self._loop(execute=True)
        self.assertEqual(dl["execution"]["status"], "done")
        self.assertIsNone(dl["nextIntent"])
        self.assertEqual(dl["observation"]["kind"], "uri-flow-complete")

    def test_failed_blocks_when_no_retry(self):
        dl = self._loop(execute=True, error={"message": "boom"})
        self.assertEqual(dl["execution"]["status"], "blocked")
        self.assertEqual(dl["nextIntent"]["id"], "repair-uri-chain")
        self.assertEqual(dl["observation"]["kind"], "uri-step-failed")

    def test_recovered_records_initial_error(self):
        dl = self._loop(execute=True, recovered=True, initial_error={"message": "first"})
        self.assertEqual(dl["observation"]["kind"], "uri-flow-recovered")
        self.assertEqual(dl["observation"]["initialError"], {"message": "first"})


class DashboardApiRoutingTests(unittest.TestCase):
    """_dashboard_api_response was converted from an if-chain to a dispatch table."""

    def test_unknown_path_is_404(self):
        status, payload = host_dashboard._dashboard_api_response("/api/nope", "proj", None, None, {})
        self.assertEqual(status, 404)
        self.assertFalse(payload["ok"])

    def test_route_table_covers_expected_endpoints(self):
        for path in ("/api/summary", "/api/tasks", "/api/checks", "/api/logs",
                     "/api/artifacts", "/api/chat/history", "/api/services/live", "/api/scanner/live"):
            self.assertIn(path, host_dashboard._API_ROUTES)


if __name__ == "__main__":
    unittest.main()
