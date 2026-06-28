# Regression: collect_attachments must not harvest a route's contract EXAMPLES as artifacts.
#
# The routing plan embeds each route's contract in `route.meta.contract`, and a screen-capture
# contract's `examples` carry sample results tagged `kind: screenshot` with placeholder paths
# (e.g. /home/u/.urirun/artifacts/s.png). The recursive attachment walk used to descend into that
# diagnostic block and surface the example paths as phantom "screenshot missing file" attachments
# next to the one real capture. The walk now skips routing/contract/examples/inputSchema keys.
import unittest

from urirun_scanner.artifacts_admin import collect_attachments


class CollectAttachmentsContractTests(unittest.TestCase):
    def _envelope(self):
        return {
            "results": {
                "kvm_host_screen_query_capture": {
                    "ok": True,
                    "result": {
                        "kind": "screenshot",
                        "live": False,
                        "path": "/home/tom/.urirun/artifacts/screenshots/urirun-kvm-shot-746070.png",
                    },
                }
            },
            "routing": {
                "steps": [
                    {
                        "route": {
                            "meta": {
                                "contract": {
                                    "examples": [
                                        {"payload": {}, "result": {
                                            "kind": "screenshot",
                                            "path": "/home/u/.urirun/artifacts/s.png", "via": "grim"}},
                                        {"payload": {"scope": "browser"}, "result": {
                                            "kind": "screenshot",
                                            "path": "/home/u/.urirun/artifacts/screenshots/shot.png",
                                            "via": "cdp"}},
                                    ]
                                }
                            }
                        }
                    }
                ]
            },
        }

    def test_contract_example_paths_are_not_attached(self):
        atts = collect_attachments(self._envelope(), project="test", limit=24)
        paths = [a["path"] for a in atts]
        self.assertNotIn("/home/u/.urirun/artifacts/s.png", paths)
        self.assertNotIn("/home/u/.urirun/artifacts/screenshots/shot.png", paths)

    def test_real_capture_is_still_attached(self):
        atts = collect_attachments(self._envelope(), project="test", limit=24)
        paths = [a["path"] for a in atts]
        self.assertEqual(len(atts), 1)
        self.assertTrue(any("urirun-kvm-shot-746070.png" in p for p in paths))


if __name__ == "__main__":
    unittest.main()
