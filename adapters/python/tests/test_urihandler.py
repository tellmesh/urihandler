# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.

import unittest

import urirun
from urirun import build_invocation, dispatch, parse_uri, v2


class UriHandlerTests(unittest.TestCase):
    def test_parse_uri(self):
        self.assertEqual(parse_uri("device://device-01/led/set/on?trace=1#ui"), {
            "fragment": "ui",
            "package": "device",
            "query": {"trace": "1"},
            "raw": "device://device-01/led/set/on?trace=1#ui",
            "segments": ["led", "set", "on"],
            "target": "device-01",
        })

    def test_build_invocation(self):
        self.assertEqual(build_invocation({
            "package": "device",
            "segments": ["led", "set", "on"],
            "target": "device-01",
        }), {
            "args": ["device-01", "on"],
            "functionName": "led_set",
            "package": "device",
            "segments": ["led", "set", "on"],
            "target": "device-01",
        })

    def test_dispatch(self):
        registry = {
            "device": {
                "led_set": lambda target, state, payload, invocation: {
                    "ok": True,
                    "payload": payload,
                    "state": state,
                    "target": target,
                }
            }
        }
        self.assertEqual(dispatch("device://device-01/led/set/on", registry, {"source": "test"}), {
            "ok": True,
            "payload": {"source": "test"},
            "state": "on",
            "target": "device-01",
        })

    def test_missing_registry_entries(self):
        with self.assertRaises(KeyError):
            dispatch("device://device-01/led/set/on", {}, {})
        with self.assertRaises(KeyError):
            dispatch("device://device-01/led/set/on", {"device": {}}, {})

    def test_v2_connector_bindings_from_decorators(self):
        previous = dict(v2.DECORATED_BINDINGS)
        v2.DECORATED_BINDINGS.clear()
        try:
            from urirun import command

            @command("demo://host/http/query/status", meta={"connector": "demo"})
            def demo_status(url: str, expectStatus: int = 200):
                return ["demo-http-check", "{url}", "{expectStatus}"]

            @urirun.command("other://host/example/command/run", meta={"connector": "other"})
            def other_command(name: str):
                return ["echo", "{name}"]

            document = urirun.connector_bindings(connector="demo")
            self.assertEqual(document["version"], "urirun.bindings.v2")
            self.assertEqual(list(document["bindings"]), ["demo://host/http/query/status"])

            route = document["bindings"]["demo://host/http/query/status"]
            self.assertEqual(route["argv"], ["demo-http-check", "{url}", "{expectStatus}"])
            self.assertEqual(route["inputSchema"]["required"], ["url"])
            self.assertFalse(route["inputSchema"]["additionalProperties"])

            registry = urirun.compile_registry(document)
            routes = urirun.list_routes(registry)
            self.assertEqual([route["uri"] for route in routes], ["demo://host/http/query/status"])
        finally:
            v2.DECORATED_BINDINGS.clear()
            v2.DECORATED_BINDINGS.update(previous)

    def test_connector_helper_uses_human_defaults(self):
        previous = dict(v2.DECORATED_BINDINGS)
        v2.DECORATED_BINDINGS.clear()
        try:
            demo = urirun.connector("demo-tools", scheme="demo", meta={"area": "test"})

            @demo.command("http/query/status", meta={"label": "Check status"})
            def demo_status(url: str, expectStatus: int = 200):
                return ["demo-http-check", "{url}", "{expectStatus}"]

            self.assertEqual(demo.uri("http/query/status"), "demo://host/http/query/status")

            document = demo.bindings()
            self.assertEqual(list(document["bindings"]), ["demo://host/http/query/status"])

            route = document["bindings"]["demo://host/http/query/status"]
            self.assertEqual(route["meta"]["connector"], "demo-tools")
            self.assertEqual(route["meta"]["area"], "test")
            self.assertEqual(route["meta"]["label"], "Check status")
            self.assertEqual(route["inputSchema"]["required"], ["url"])
            self.assertFalse(route["inputSchema"]["additionalProperties"])

            registry = urirun.compile_registry(document)
            result = urirun.run("demo://host/http/query/status", registry, {"url": "https://example.com"})
            self.assertEqual(result["result"]["command"], ["demo-http-check", "https://example.com", "200"])
        finally:
            v2.DECORATED_BINDINGS.clear()
            v2.DECORATED_BINDINGS.update(previous)

    def test_entry_point_bindings_generate_registry(self):
        def provider():
            return {
                "version": v2.VERSION,
                "bindings": {
                    "demo://host/http/query/status": {
                        "kind": "command",
                        "adapter": "argv-template",
                        "inputSchema": {
                            "type": "object",
                            "required": ["url"],
                            "properties": {
                                "url": {"type": "string"},
                                "expectStatus": {"type": "integer", "default": 200},
                            },
                            "additionalProperties": False,
                        },
                        "argv": ["demo-http-check", "{url}", "{expectStatus}"],
                        "meta": {"connector": "demo-tools"},
                    }
                },
            }

        class EntryPoint:
            name = "demo-tools"
            value = "demo_tools:urirun_bindings"

            def load(self):
                return provider

        original = v2.metadata.entry_points
        v2.metadata.entry_points = lambda: [EntryPoint()]
        try:
            document = urirun.entry_point_binding_document()
            self.assertEqual(document["bindingCount"], 1)
            binding = document["bindings"][0]
            self.assertEqual(binding["uri"], "demo://host/http/query/status")
            self.assertEqual(binding["source"]["type"], "python-entry-point")
            self.assertEqual(binding["source"]["group"], "urirun.bindings")

            registry = urirun.compile_registry(document)
            result = urirun.run("demo://host/http/query/status", registry, {"url": "https://example.com"})
            self.assertTrue(result["ok"])
            self.assertEqual(
                result["result"]["command"],
                ["demo-http-check", "https://example.com", "200"],
            )
        finally:
            v2.metadata.entry_points = original


if __name__ == "__main__":
    unittest.main()
