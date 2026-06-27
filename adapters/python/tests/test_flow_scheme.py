# Author: Tom Sapletta · https://tom.sapletta.com
# Tests for flow:// URI scheme dispatch (Faza 2) and recall drift guard (Faza 1).
from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

from urirun.host.dispatch import _flow_scheme_dispatch, inprocess_fallback


def _ok_episode(episode_id: str, goal: str, steps: list) -> dict:
    return {
        "episode_id": episode_id,
        "goal": goal,
        "plan": {"steps": steps, "flow_key": "fk-test"},
        "reality": {"fingerprint": "fp-abc"},
        "outcome": {"status": "ok"},
        "ts": "2026-01-01T00:00:00Z",
    }


class TestFlowSchemeDispatch(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="flow-scheme-")
        self._old = os.environ.get("URIRUN_TWIN_MEMORY")
        os.environ["URIRUN_TWIN_MEMORY"] = os.path.join(self.tmp, "mem.json")

    def tearDown(self):
        if self._old is None:
            os.environ.pop("URIRUN_TWIN_MEMORY", None)
        else:
            os.environ["URIRUN_TWIN_MEMORY"] = self._old
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _mem(self):
        from urirun.node.twin_store import durable_memory
        return durable_memory()

    def test_query_get_returns_plan_by_episode_id(self):
        steps = [{"id": "s", "uri": "kvm://host/screen/query/capture"}]
        self._mem().remember_episode(_ok_episode("ep-xyz", "capture screen", steps))
        result = _flow_scheme_dispatch("flow://host/ep-xyz/query/get")
        self.assertIsNotNone(result)
        self.assertTrue(result.get("ok"))
        out = result.get("result") or {}
        self.assertEqual(out.get("episode_id"), "ep-xyz")
        self.assertEqual(len(out.get("steps") or []), 1)

    def test_query_get_returns_none_for_unknown_name(self):
        result = _flow_scheme_dispatch("flow://host/ep-doesnotexist/query/get")
        self.assertIsNone(result)

    def test_query_get_via_skill_name(self):
        steps = [{"id": "s", "uri": "kvm://host/screen/query/capture"}]
        mem = self._mem()
        mem.remember_episode(_ok_episode("ep-abc", "daily screenshot", steps))
        mem.remember_skill("daily-screenshot", {"episode_id": "ep-abc", "ts": "2026-01-01T00:00:00Z"})
        result = _flow_scheme_dispatch("flow://host/daily-screenshot/query/get")
        self.assertIsNotNone(result)
        out = result.get("result") or {}
        self.assertEqual(out.get("episode_id"), "ep-abc")
        self.assertEqual(out.get("skill"), "daily-screenshot")

    def test_command_run_dispatches_steps(self):
        steps = [{"id": "s", "uri": "twin://host/env/query/drift", "payload": {}, "depends_on": []}]
        self._mem().remember_episode(_ok_episode("ep-run", "drift check", steps))
        dispatched: list[str] = []
        def fake_call(uri, payload=None, *a, **kw):
            dispatched.append(uri)
            return {"ok": True, "result": {"value": {"ok": True, "drift": False, "known": True}}}
        with mock.patch("urirun.v2_service.call", side_effect=fake_call):
            result = _flow_scheme_dispatch("flow://host/ep-run/command/run", {"execute": True})
        self.assertIsNotNone(result)
        self.assertTrue(result.get("ok"), result)
        self.assertIn("twin://host/env/query/drift", dispatched)

    def test_command_run_unknown_name_returns_none(self):
        result = _flow_scheme_dispatch("flow://host/no-such-plan/command/run")
        self.assertIsNone(result)

    def test_unknown_verb_returns_none(self):
        steps = [{"id": "s", "uri": "twin://host/env/query/drift"}]
        self._mem().remember_episode(_ok_episode("ep-verb", "test", steps))
        result = _flow_scheme_dispatch("flow://host/ep-verb/command/unknown-verb")
        self.assertIsNone(result)

    def test_short_uri_returns_none(self):
        self.assertIsNone(_flow_scheme_dispatch("flow://host/short"))

    def test_inprocess_fallback_routes_flow_scheme(self):
        """inprocess_fallback tier-2c should route flow:// URIs."""
        steps = [{"id": "s", "uri": "kvm://host/screen/query/capture"}]
        self._mem().remember_episode(_ok_episode("ep-fb", "fallback test", steps))
        result = inprocess_fallback("flow://host/ep-fb/query/get")
        self.assertIsNotNone(result)
        self.assertTrue(result.get("ok"))


class TestRecallDriftGuard(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="recall-drift-")
        self._old = os.environ.get("URIRUN_TWIN_MEMORY")
        os.environ["URIRUN_TWIN_MEMORY"] = os.path.join(self.tmp, "mem.json")

    def tearDown(self):
        if self._old is None:
            os.environ.pop("URIRUN_TWIN_MEMORY", None)
        else:
            os.environ["URIRUN_TWIN_MEMORY"] = self._old
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _recall(self, **kw):
        from urirun_connector_twin.core import flow_recall
        return flow_recall(**kw)

    def _mem(self):
        from urirun.node.twin_store import durable_memory
        return durable_memory()

    def _ep(self, episode_id: str = "ep-dr", goal: str = "capture") -> dict:
        from urirun.node.episode import intent_signature
        return {
            "episode_id": episode_id,
            "goal": goal,
            "intent_sig": intent_signature(goal),
            "plan": {"steps": [{"id": "s", "uri": "kvm://host/screen/query/capture"}]},
            "reality": {"fingerprint": "fp-known"},
            "outcome": {"status": "ok"},
            "ts": "2026-01-01T00:00:00Z",
        }

    def test_recall_skips_drift_check_when_flag_set(self):
        self._mem().remember_episode(self._ep())
        result = self._recall(episode_id="ep-dr", skip_drift_check=True)
        self.assertTrue(result.get("found"))
        self.assertEqual(result.get("source"), "episode")

    def test_recall_suppresses_episode_when_drift_detected(self):
        # _drift_ok() calls kvm://host/environment/query/profile + mem.drift() in-process.
        # Store a known-good baseline first, then return a DIFFERENT profile so drift fires.
        # environment_fingerprint keys on: platform, wayland, display, monitor COUNT, best,
        # osLevelReliable — NOT pixel dimensions, so change best/osLevelReliable to fake drift.
        known_profile = {"platform": "linux", "wayland": True, "monitors": [{"w": 2560, "h": 1600}],
                         "best": "cdp", "osLevelReliable": True}
        drifted_profile = {**known_profile, "best": "vision", "osLevelReliable": False}
        mem = self._mem()
        mem.remember("host", known_profile)
        mem.remember_episode(self._ep())
        def _drifted(uri, payload, registry, mode):
            return {"ok": True, "result": {"value": drifted_profile}}
        with mock.patch("urirun.v2_service.call", side_effect=_drifted):
            result = self._recall(episode_id="ep-dr")
        self.assertFalse(result.get("found"))
        self.assertTrue(result.get("driftDetected"))

    def test_recall_returns_episode_when_no_drift(self):
        known_profile = {"platform": "linux", "wayland": True, "monitors": [{"w": 2560, "h": 1600}],
                         "best": "cdp", "osLevelReliable": True}
        mem = self._mem()
        mem.remember("host", known_profile)
        mem.remember_episode(self._ep())
        def _no_drift(uri, payload, registry, mode):
            # Return the SAME profile so mem.drift() sees no change.
            return {"ok": True, "result": {"value": known_profile}}
        with mock.patch("urirun.v2_service.call", side_effect=_no_drift):
            result = self._recall(episode_id="ep-dr")
        self.assertTrue(result.get("found"))

    def test_flow_store_fallback_has_no_drift_guard(self):
        """Tier-3 (flow_store by intent) is offered without drift guard — it is a hint."""
        from urirun.node.episode import intent_signature
        self._mem().remember_flow("fk1", {
            "flowKey": "fk1",
            "intent_sig": intent_signature("capture screen"),
            "steps": [{"id": "s", "uri": "kvm://host/screen/query/capture"}],
            "degraded": False, "ts": "2026-01-01T00:00:00Z",
        })
        # Even if drift probe would return drifted, flow_store tier skips the guard
        def _drifted(*a, **kw):
            return {"ok": True, "result": {"value": {"drift": True, "known": True}}}
        with mock.patch("urirun.v2_service.call", side_effect=_drifted):
            result = self._recall(prompt="capture screen", env_fp="", skip_drift_check=False)
        # Tier-3 fires (env_fp empty → episode tier 2 skipped, flow_store tier 3 has no guard)
        self.assertTrue(result.get("found"))
        self.assertEqual(result.get("source"), "flow_store")
        self.assertTrue(result.get("driftUnchecked"))


if __name__ == "__main__":
    unittest.main()
