# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# Tests for Episode CAPTURE (Krok 3): twin_bridge.capture_episode assembles a finished run
# into a content-addressed Episode and persists it so recall_episode can find it by intent×env.
import os
import shutil
import tempfile
import unittest

from urirun.host.twin_bridge import capture_episode, _infer_node_from_flow
from urirun.node.episode import intent_signature
from urirun.node.twin_store import durable_memory


class TestInferNodeFromFlow(unittest.TestCase):
    """_infer_node_from_flow must return the ACTUAL node from step URIs, not the UI-default
    selected_targets value, so recall keys are keyed by the correct env fingerprint."""

    def test_remote_node_extracted_from_step_uris(self):
        flow = {"steps": [
            {"uri": "env://lenovo/runtime/query/health"},
            {"uri": "log://lenovo/session/command/write"},
        ]}
        assert _infer_node_from_flow(flow, ["host"]) == "lenovo"

    def test_host_fallback_when_all_steps_are_host(self):
        flow = {"steps": [{"uri": "kvm://host/screen/query/capture"}]}
        assert _infer_node_from_flow(flow, ["host"]) == "host"

    def test_first_non_host_authority_wins(self):
        flow = {"steps": [
            {"uri": "kvm://host/screen/query/capture"},
            {"uri": "kvm://remote/screen/query/capture"},
        ]}
        assert _infer_node_from_flow(flow, ["host"]) == "remote"

    def test_steps_with_host_authority_win_over_selectedNodes(self):
        # step URIs say "host" → steps are ground truth, selectedNodes is ignored
        flow = {"steps": [{"uri": "kvm://host/screen/query/capture"}],
                "selectedNodes": ["office"]}
        assert _infer_node_from_flow(flow, ["host"]) == "host"

    def test_selectedNodes_fallback_when_no_step_uris(self):
        # no step URIs → fall back to flow["selectedNodes"]
        flow = {"steps": [{"id": "s1"}], "selectedNodes": ["office"]}
        assert _infer_node_from_flow(flow, ["host"]) == "office"

    def test_empty_flow_uses_selected_targets_stripped(self):
        assert _infer_node_from_flow({}, ["node:lenovo"]) == "lenovo"

    def test_empty_everything_defaults_to_host(self):
        assert _infer_node_from_flow({}, []) == "host"

    def test_capture_episode_uses_actual_node_not_ui_default(self):
        """Regression: selectedTargets=['host'] (UI default) MUST NOT poison recall key
        when steps execute on a different node (e.g. 'lenovo')."""
        import os, shutil, tempfile
        tmp = tempfile.mkdtemp(prefix="ep-node-infer-")
        old = os.environ.get("URIRUN_TWIN_MEMORY")
        try:
            os.environ["URIRUN_TWIN_MEMORY"] = os.path.join(tmp, "twin.json")
            mem = durable_memory()
            mem.remember("lenovo", {"platform": "fedora", "best": "kvm"})
            fp_lenovo = mem.known_good("lenovo")["fingerprint"]

            flow = {"steps": [
                {"id": "s1", "uri": "env://lenovo/runtime/query/health"},
                {"id": "s2", "uri": "log://lenovo/session/command/write"},
            ]}
            ids = capture_episode(
                execute=True, flow=flow, prompt="zrob screenshot na lenovo",
                selected_targets=["host"],  # ← UI default, NOT "node:lenovo"
                timeline=flow["steps"], results={"s1": {"ok": True}, "s2": {"ok": True}},
                status="ok",
            )
            assert ids is not None
            # Episode must be recallable by lenovo's fingerprint, not host's
            hit = durable_memory().recall_episode(
                intent_signature("zrob screenshot na lenovo"), fp_lenovo)
            assert hit is not None, (
                "Episode should be keyed to lenovo env_fp, not host")
        finally:
            if old is None:
                os.environ.pop("URIRUN_TWIN_MEMORY", None)
            else:
                os.environ["URIRUN_TWIN_MEMORY"] = old
            shutil.rmtree(tmp, ignore_errors=True)


class TestCaptureEpisode(unittest.TestCase):

    GOAL = "Zrób screenshot pulpitu"

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="episode-capture-")
        self.path = os.path.join(self.tmp, "twin-memory.json")
        self._old = os.environ.get("URIRUN_TWIN_MEMORY")
        os.environ["URIRUN_TWIN_MEMORY"] = self.path

    def tearDown(self):
        if self._old is None:
            os.environ.pop("URIRUN_TWIN_MEMORY", None)
        else:
            os.environ["URIRUN_TWIN_MEMORY"] = self._old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _seed_env(self, node="host"):
        mem = durable_memory()
        mem.remember(node, {"platform": "linux", "best": "kvm", "wayland": True})
        return mem.known_good(node)["fingerprint"]

    def test_capture_persists_and_is_recallable_by_intent_env(self):
        fp = self._seed_env("host")
        flow = {"steps": [{"id": "s1", "uri": "kvm://host/screen/query/capture"}]}
        ids = capture_episode(
            execute=True, flow=flow, prompt=self.GOAL, selected_targets=["host"],
            timeline=flow["steps"], results={"s1": {"ok": True, "value": {}}},
            status="ok", next_intent={"uri": "kvm://host/next"},
        )
        self.assertIsNotNone(ids)
        # Pure-query flows get a stable dedup key ("obs-"); command flows keep "ep-".
        self.assertTrue(ids["episode_id"].startswith(("ep-", "obs-")))
        self.assertTrue(ids["intent_sig"].startswith("intent-"))
        self.assertEqual(ids["next_intent"], "kvm://host/next")

        hit = durable_memory().recall_episode(intent_signature(self.GOAL), fp)
        self.assertIsNotNone(hit, "ok episode should be recallable by (intent, env)")
        self.assertEqual(hit["goal"], self.GOAL)
        self.assertEqual(hit["outcome"]["status"], "ok")
        self.assertEqual(hit["reality"]["fingerprint"], fp)
        self.assertTrue(hit["plan"]["flow_key"])

    def test_artifacts_are_captured_from_results(self):
        self._seed_env("host")
        flow = {"steps": [{"id": "s1", "uri": "camera://host/capture"}]}
        results = {"s1": {"ok": True, "value": {"sha256": "abc123", "kind": "scan",
                                                "path": "/data/x.png", "uri": "artifact://x"}}}
        capture_episode(execute=True, flow=flow, prompt="skan", selected_targets=["host"],
                        timeline=flow["steps"], results=results, status="ok")
        ep = durable_memory().known_good_episodes()[0]
        self.assertEqual(len(ep["artifacts"]), 1)
        self.assertEqual(ep["artifacts"][0]["sha256"], "abc123")

    def test_demo_run_is_not_captured(self):
        ids = capture_episode(execute=False, flow={"steps": []}, prompt="x",
                              selected_targets=[], timeline=[], results={}, status="ok")
        self.assertIsNone(ids)
        self.assertEqual(durable_memory().known_good_episodes(), [])

    def test_reversible_steps_generate_proofs(self):
        self._seed_env("host")
        flow = {"steps": [
            {"id": "s1", "uri": "kvm://host/input/command/type"},
            {"id": "s2", "uri": "kvm://host/window/command/focus"},
        ]}
        timeline = [
            {"id": "s1", "uri": "kvm://host/input/command/type", "ok": True,
             "reversible": True, "inverse": {"uri": "kvm://host/input/command/type_undo"}},
            {"id": "s2", "uri": "kvm://host/window/command/focus", "ok": True,
             "reversible": False},
        ]
        capture_episode(execute=True, flow=flow, prompt="wpisz tekst", selected_targets=["host"],
                        timeline=timeline, results={}, status="ok")
        ep = durable_memory().known_good_episodes()[0]
        self.assertEqual(len(ep["proofs"]), 1, "only reversible steps produce proofs")
        pf = ep["proofs"][0]
        self.assertEqual(pf["uri"], "kvm://host/input/command/type")
        self.assertTrue(pf["verdict"])
        self.assertTrue(pf["proof_key"].startswith("pf-"))

    def test_failed_run_persisted_but_not_recalled(self):
        flow = {"steps": [{"id": "s1", "uri": "kvm://host/x/command/y"}]}
        capture_episode(execute=True, flow=flow, prompt="zrób coś", selected_targets=["host"],
                        timeline=flow["steps"], results={}, status="failed")
        eps = durable_memory().known_good_episodes()
        self.assertEqual(len(eps), 1, "failed run is still recorded (feeds recovery, not recall)")
        self.assertEqual(eps[0]["outcome"]["status"], "failed")
        self.assertIsNone(durable_memory().recall_episode(intent_signature("zrób coś"), ""))


if __name__ == "__main__":
    unittest.main()
