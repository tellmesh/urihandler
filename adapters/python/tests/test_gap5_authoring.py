# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Gap 5 — single-file authoring: `gen handlers`, `run --module`, `connector_main`."""
from __future__ import annotations

import ast
import json

import urirun
from urirun import v2
from urirun.runtime import _runtime as runtime, codegen


# ---- gen handlers ---------------------------------------------------------------

def test_gen_handlers_emits_valid_typed_stubs():
    reg = v2.compile_registry({
        "version": "urirun.bindings.v2",
        "bindings": {
            "time://host/clock/query/now": {
                "kind": "query", "adapter": "argv-template", "argv": ["echo"],
                "inputSchema": {"type": "object", "required": ["timezone"],
                                "properties": {"timezone": {"type": "string"},
                                               "fmt": {"type": "string", "default": "iso"}}},
            },
        },
    })
    src = codegen.to_handlers(reg)
    ast.parse(src)                                       # importable Python
    assert "urirun.connector('time', scheme='time', target='host')" in src
    assert "@time.handler('clock/query/now')" in src
    assert "def now(timezone: str, fmt: str = 'iso')" in src   # required first, optional defaulted
    assert "handlers" in codegen.GENERATORS


# ---- run --module ---------------------------------------------------------------

def test_run_module_dispatches_from_a_plain_file(tmp_path):
    f = tmp_path / "core.py"
    f.write_text(
        "import urirun\n"
        "c = urirun.connector('demo', scheme='demo', target='h')\n"
        "@c.handler('greet/command/hi')\n"
        "def hi(name: str = 'world') -> dict:\n"
        "    return urirun.ok(greeting=name)\n"
    )
    registry = v2._registry_from_module(str(f))
    policy = runtime.build_policy(None, ["demo://**"], None)
    env = v2.run("demo://h/greet/command/hi", registry, {"name": "x"}, mode="execute", policy=policy)
    assert env["ok"] is True
    assert env["result"]["value"]["greeting"] == "x"


def test_run_module_errors_clearly_on_empty_file(tmp_path):
    f = tmp_path / "empty.py"
    f.write_text("x = 1\n")
    try:
        v2._registry_from_module(str(f))
        assert False, "expected SystemExit"
    except SystemExit as exc:
        assert "no urirun routes" in str(exc)


# ---- connector_main -------------------------------------------------------------

def test_connector_main_aggregates_routes_and_runs(capsys):
    a = urirun.connector("cma", scheme="cma", target="h")
    b = urirun.connector("cmb", scheme="cmb", target="h")

    @a.handler("x/command/start")
    def start(v: str = "a") -> dict:
        return urirun.ok(who="a", v=v)

    @b.handler("y/command/stop")
    def stop(v: str = "b") -> dict:
        return urirun.ok(who="b", v=v)

    rc = urirun.connector_main(a, b, argv=["start", "--v", "hi"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] and out["result"]["value"] == {"who": "a", "v": "hi", "ok": True}

    rc = urirun.connector_main(a, b, argv=["bindings"])
    assert rc == 0
    merged = json.loads(capsys.readouterr().out)["bindings"]
    assert "cma://h/x/command/start" in merged and "cmb://h/y/command/stop" in merged


def test_connector_main_namespaces_clashing_route_names(capsys):
    a = urirun.connector("nsa", scheme="nsa", target="h")
    b = urirun.connector("nsb", scheme="nsb", target="h")

    @a.handler("thing/command/run")
    def run_a() -> dict:
        return urirun.ok(who="a")

    @b.handler("thing/command/run")
    def run_b() -> dict:
        return urirun.ok(who="b")

    # both routes' last segment is "run" -> namespaced by connector id
    rc = urirun.connector_main(a, b, argv=["nsa-run"])
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["result"]["value"]["who"] == "a"
