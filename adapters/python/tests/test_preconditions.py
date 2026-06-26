# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# The precondition / readiness kernel: turn "degraded-but-fixable" into acquire -> prove -> retry.
# A human-gated precondition (portal grant, login) becomes a one-tap acquire item, not a dead end.
import unittest

from urirun.node import preconditions as P


class PreconditionEnsureTests(unittest.TestCase):
    def setUp(self):
        P.clear()
        self.addCleanup(P.clear)

    def test_already_satisfied_is_a_no_op(self):
        P.provider("net", "always", check=lambda ctx: True)
        r = P.ensure("net")
        self.assertTrue(r["ok"] and r["satisfied"])
        self.assertNotIn("acquired", r)

    def test_auto_provider_acquires_then_proves(self):
        state = {"installed": False}
        P.provider("tool", "installer", check=lambda ctx: state["installed"],
                   satisfy=lambda ctx: state.update(installed=True), hint="install tool")
        r = P.ensure("tool")
        self.assertTrue(r["ok"] and r["satisfied"] and r["acquired"])
        self.assertTrue(state["installed"])

    def test_auto_provider_that_fails_recheck_falls_to_acquire(self):
        # satisfy runs but the precondition is still not met -> surface acquire, record the attempt
        P.provider("flaky", "broken", check=lambda ctx: False,
                   satisfy=lambda ctx: None, hint="manual fix")
        r = P.ensure("flaky")
        self.assertFalse(r["satisfied"])
        self.assertEqual(r["next"], {"kind": "acquire"})

    def test_human_gated_surfaces_one_tap_acquire_item(self):
        P.provider("portal-grant", "wayland-portal", check=lambda ctx: False,
                   human_gated=True, hint="Grant capture permission once per session")
        r = P.ensure("portal-grant")
        self.assertFalse(r["ok"])
        self.assertEqual(r["next"], {"kind": "acquire"})
        self.assertTrue(r["acquire"]["humanGated"])
        self.assertIn("Grant capture", r["acquire"]["hint"])

    def test_human_gated_is_not_auto_attempted(self):
        calls = {"satisfy": 0}
        # human_gated provider whose satisfy must NEVER be called automatically
        P.provider("login", "browser-login", check=lambda ctx: False,
                   satisfy=lambda ctx: calls.update(satisfy=calls["satisfy"] + 1),
                   human_gated=True, hint="log in")
        P.ensure("login")
        self.assertEqual(calls["satisfy"], 0)

    def test_higher_priority_satisfied_provider_wins(self):
        P.provider("x", "low", check=lambda ctx: False, priority=10)
        P.provider("x", "high", check=lambda ctx: True, priority=90)
        self.assertEqual(P.ensure("x")["provider"], "high")

    def test_unknown_precondition_reports_no_provider(self):
        r = P.ensure("nope")
        self.assertFalse(r["ok"])
        self.assertIn("no provider", r["reason"])

    def test_status_is_read_only(self):
        state = {"done": False}
        P.provider("t", "p", check=lambda ctx: state["done"],
                   satisfy=lambda ctx: state.update(done=True))
        s = P.status("t")
        self.assertFalse(s["satisfied"])
        self.assertFalse(state["done"])  # status must NOT acquire


class ReadyURIHandlerTests(unittest.TestCase):
    def setUp(self):
        P.clear()
        self.addCleanup(P.clear)

    def test_check_handler(self):
        P.provider("p", "prov", check=lambda ctx: True)
        self.assertTrue(P._uri_ready_check(precondition="p")["satisfied"])
        self.assertFalse(P._uri_ready_check(precondition="")["ok"])  # missing arg

    def test_ensure_handler_surfaces_acquire(self):
        P.provider("p", "prov", check=lambda ctx: False, human_gated=True, hint="do it")
        r = P._uri_ready_ensure(precondition="p")
        self.assertEqual(r["next"], {"kind": "acquire"})

    def test_report_and_bindings(self):
        P.provider("p", "prov", check=lambda ctx: True)
        self.assertIn("p", P._uri_ready_report()["preconditions"])
        self.assertIsInstance(P.ready_bindings(), dict)


if __name__ == "__main__":
    unittest.main()
