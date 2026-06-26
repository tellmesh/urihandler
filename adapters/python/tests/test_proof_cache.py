# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# Unit tests for the connector proof-cache: the content-addressed reversibility ledger
# (TwinMemory.remember_proof/recall_proof) and the twin://host/proof/* routes
# (check / record / gate). The probe seam is patched, so no Docker / served connector is
# needed; passing scenario_sig explicitly keeps the proof_key deterministic and connector-free.
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from urirun.node import flow
from urirun.node.episode import proof_key
from urirun.node.reversible import TwinMemory
from urirun.node.twin_store import durable_memory


# ─────────────────────────────────────────────────── store layer ──── #

class TestProofStore(unittest.TestCase):
    """TwinMemory caches positive verdicts only."""

    def test_remember_only_positive(self):
        m = TwinMemory()
        m.remember_proof("pf-pos", {"verdict": True, "uri": "fs://a"})
        m.remember_proof("pf-neg", {"verdict": False, "uri": "fs://b"})
        self.assertIsNotNone(m.recall_proof("pf-pos"))
        self.assertIsNone(m.recall_proof("pf-neg"), "a negative verdict is not durable proof")

    def test_remember_ignores_empty_key(self):
        m = TwinMemory()
        m.remember_proof("", {"verdict": True})
        self.assertEqual(m.proof_store, {})

    def test_recall_miss_returns_none(self):
        self.assertIsNone(TwinMemory().recall_proof("nope"))


# ─────────────────────────────────────────── durable store env ──── #

class _DurableEnv(unittest.TestCase):
    """Point durable_memory() at a throwaway JSON file for the duration of the test."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="proof-cache-")
        self.path = os.path.join(self.tmp, "twin-memory.json")
        self._old = os.environ.get("URIRUN_TWIN_MEMORY")
        os.environ["URIRUN_TWIN_MEMORY"] = self.path

    def tearDown(self):
        if self._old is None:
            os.environ.pop("URIRUN_TWIN_MEMORY", None)
        else:
            os.environ["URIRUN_TWIN_MEMORY"] = self._old
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestProofDurable(_DurableEnv):

    def test_proofs_namespace_persists_across_handles(self):
        durable_memory().remember_proof("pf-x", {"verdict": True, "uri": "fs://a"})
        # a fresh handle reads it back from the same atomic JSON file
        self.assertIsNotNone(durable_memory().recall_proof("pf-x"))
        data = json.loads(open(self.path, encoding="utf-8").read())
        self.assertIn("_proofs", data)
        self.assertIn("pf-x", data["_proofs"])


# ─────────────────────────────────────────── check / record routes ──── #

class TestProofCheckRecord(_DurableEnv):

    URI = "fs://host/data/command/write"
    ENV = "env-z"
    SIG = "sig-1"

    def _pay(self, **extra):
        return {"uri": self.URI, "env_fingerprint": self.ENV, "scenario_sig": self.SIG, **extra}

    def test_check_miss_then_record_then_hit(self):
        self.assertFalse(flow._uri_proof_check(self._pay())["hit"])
        rec = flow._uri_proof_record(self._pay(verdict=True))
        self.assertTrue(rec["recorded"])
        chk = flow._uri_proof_check(self._pay())
        self.assertTrue(chk["hit"])
        self.assertTrue(chk["verdict"])
        self.assertEqual(chk["proof_key"], rec["proof_key"])

    def test_record_negative_is_no_op(self):
        rec = flow._uri_proof_record(self._pay(verdict=False))
        self.assertFalse(rec["recorded"])
        self.assertFalse(flow._uri_proof_check(self._pay())["hit"])

    def test_route_key_matches_episode_proof_key(self):
        key, used_sig = flow._proof_key_for(self.URI, self.ENV, self.SIG)
        self.assertEqual(used_sig, self.SIG)
        self.assertEqual(key, proof_key(self.URI, self.SIG, self.ENV))
        chk = flow._uri_proof_check(self._pay())
        self.assertEqual(chk["proof_key"], key)


# ─────────────────────────────────────────────── the gate ──── #

class TestProofGate(_DurableEnv):
    """check → probe → record, with the sandbox probe patched."""

    URI = "fs://host/data/command/write"
    ENV = "env-aaa"
    SIG = "sig-gate"

    def _pay(self, **extra):
        return {"uri": self.URI, "env_fingerprint": self.ENV, "scenario_sig": self.SIG, **extra}

    def test_new_env_probes_and_records(self):
        probe = {"reversible": True, "verdict": "reversible", "simulated": True}
        with mock.patch.object(flow, "_proof_probe", return_value=probe) as p:
            res = flow._uri_proof_gate(self._pay())
        self.assertTrue(res["ok"])
        self.assertEqual(res["action"], "probed-and-recorded")
        self.assertTrue(res["reversible"])
        p.assert_called_once()
        self.assertIsNotNone(durable_memory().recall_proof(res["proof_key"]))

    def test_same_context_hits_and_skips_sandbox(self):
        flow._uri_proof_record(self._pay(verdict=True))   # seed the cache
        with mock.patch.object(flow, "_proof_probe") as p:
            res = flow._uri_proof_gate(self._pay())
        self.assertEqual(res["action"], "skip")
        self.assertTrue(res["reversible"])
        self.assertTrue(res["cached"])
        p.assert_not_called()

    def test_drift_invalidates_and_reprobes(self):
        flow._uri_proof_record(self._pay(verdict=True))   # proven for env-aaa
        drifted = self._pay(env_fingerprint="env-bbb")
        probe = {"reversible": True, "simulated": True}
        with mock.patch.object(flow, "_proof_probe", return_value=probe) as p:
            res = flow._uri_proof_gate(drifted)
        self.assertEqual(res["action"], "probed-and-recorded")
        p.assert_called_once()   # new fingerprint → new key → cache miss → re-probe

    def test_irreversible_blocks_and_caches_nothing(self):
        probe = {"reversible": False, "verdict": "IRREVERSIBLE — inverse did not restore state"}
        with mock.patch.object(flow, "_proof_probe", return_value=probe):
            res = flow._uri_proof_gate(self._pay())
        self.assertEqual(res["action"], "block")
        self.assertFalse(res["reversible"])
        self.assertIsNone(durable_memory().recall_proof(res["proof_key"]))


if __name__ == "__main__":
    unittest.main()
