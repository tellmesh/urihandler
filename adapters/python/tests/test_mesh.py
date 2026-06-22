# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.

import tempfile
import unittest
from pathlib import Path

from urirun import mesh


class MeshTests(unittest.TestCase):
    def test_host_config_add_node(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "mesh.json")
            config = mesh.init_host(path, name="host-a")
            self.assertEqual(config["host"]["name"], "host-a")

            updated = mesh.add_node(path, "node-a", "http://127.0.0.1:8765/", ["lab"])
            self.assertEqual(updated["nodes"], [{"name": "node-a", "url": "http://127.0.0.1:8765", "tags": ["lab"]}])
            self.assertEqual(mesh.load_host_config(path)["nodes"][0]["name"], "node-a")

    def test_apply_deploy_hot_swaps_registry_code_and_allow(self):
        # a live node's mutable state, as serve_node builds it
        state = {"name": "node-a",
                 "registry": {"version": "urirun.bindings.v2", "routes": {}},
                 "routes": [], "allow": []}
        body = {
            "bindings": {"version": "urirun.bindings.v2", "bindings": {
                "demo://node-a/thing/query/ping": {
                    "kind": "query", "adapter": "local-function",
                    "ref": "pushed_mod:ping",
                    "python": {"type": "python", "module": "pushed_mod", "export": "ping"},
                    "inputSchema": {"type": "object"}},
            }},
            "code": {"pushed_mod.py": "def ping(**p):\n    return {'pong': True}\n"},
            "allow": ["demo://node-a/**"],
            "name": "renamed",
            "env": {"DEPLOY_TEST_VAR": "1"},
        }
        summary = mesh.apply_deploy(state, body)

        self.assertTrue(summary["ok"])
        self.assertEqual(summary["routeCount"], 1)
        self.assertEqual(summary["schemes"], ["demo"])
        self.assertEqual(state["name"], "renamed")          # rename applied
        self.assertEqual(state["allow"], ["demo://node-a/**"])  # allow swapped
        self.assertEqual(len(state["routes"]), 1)            # registry hot-swapped
        # pushed code landed on the node's import path
        self.assertTrue((mesh.deploy_dir() / "pushed_mod.py").exists())
        import os
        self.assertEqual(os.environ.get("DEPLOY_TEST_VAR"), "1")

    def test_apply_deploy_requires_a_surface(self):
        with self.assertRaises(ValueError):
            mesh.apply_deploy({"name": "n", "registry": {}, "routes": [], "allow": []}, {})

    def test_resolve_admin_token_generate_reuse_and_precedence(self):
        import os
        with tempfile.TemporaryDirectory() as tmp:
            old_home, old_env = os.environ.get("HOME"), os.environ.pop("URIRUN_NODE_TOKEN", None)
            os.environ["HOME"] = tmp
            try:
                self.assertIsNone(mesh.resolve_admin_token(None, None, False))  # off by default
                gen = mesh.resolve_admin_token(None, None, True)                # mint + persist
                self.assertTrue(gen and mesh.node_token_path().exists())
                self.assertEqual(mesh.resolve_admin_token(None, None, True), gen)   # reused across restarts
                self.assertEqual(mesh.resolve_admin_token("auto", None, False), gen)  # 'auto' sentinel
                self.assertEqual(mesh.resolve_admin_token("pinned", None, True), "pinned")  # explicit wins
                self.assertEqual(mesh.resolve_admin_token(None, "cfg", False), "cfg")       # config next
            finally:
                if old_home is not None:
                    os.environ["HOME"] = old_home
                if old_env is not None:
                    os.environ["URIRUN_NODE_TOKEN"] = old_env

    def test_node_config_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "node.json")
            config = mesh.init_node(path, name="node-a", registry="registry.json", port=9999, execute=True)
            self.assertEqual(config["node"]["name"], "node-a")
            self.assertEqual(config["node"]["registry"], "registry.json")
            self.assertEqual(config["node"]["port"], 9999)
            self.assertTrue(config["node"]["execute"])

    def test_heuristic_flow_uses_all_reachable_nodes(self):
        nodes = [
            {"name": "pc1", "reachable": True},
            {"name": "pc2", "reachable": True},
        ]
        routes = [
            {"uri": "env://pc1/runtime/query/health", "safe": True},
            {"uri": "proc://pc1/process/query/list", "safe": True},
            {"uri": "env://pc2/runtime/query/health", "safe": True},
            {"uri": "proc://pc2/process/query/list", "safe": True},
        ]
        flow = mesh.heuristic_flow("pokaz procesy na wszystkich komputerach", routes, nodes)
        uris = [step["uri"] for step in flow["steps"]]
        self.assertIn("proc://pc1/process/query/list", uris)
        self.assertIn("proc://pc2/process/query/list", uris)

    def test_registry_from_remote_routes(self):
        registry = mesh.registry_from_routes([
            {
                "uri": "proc://pc1/process/query/list",
                "kind": "query",
                "adapter": "ps",
                "safe": True,
                "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer"}}},
            }
        ])
        flattened = mesh.routes_from_registry(registry)
        self.assertEqual(flattened[0]["uri"], "proc://pc1/process/query/list")
        self.assertEqual(flattened[0]["adapter"], "http-service")

    def test_resolve_step_payload_chains_prior_results(self):
        results = {"slugify": {"ok": True, "result": {"slug": "june-report"}}}
        payload = {"text": "hi", "slug_from": "slugify.result.slug"}
        self.assertEqual(
            mesh.resolve_step_payload(payload, results),
            {"text": "hi", "slug": "june-report"},
        )

    def test_dig_path_indexes_lists(self):
        data = {"s": {"result": {"items": ["a", "b", "c"]}}}
        self.assertEqual(mesh._dig_path(data, "s.result.items.2"), "c")

    def test_resolve_step_payload_passthrough_without_from(self):
        self.assertEqual(mesh.resolve_step_payload({"a": 1, "b": "x"}, {}), {"a": 1, "b": "x"})


if __name__ == "__main__":
    unittest.main()
