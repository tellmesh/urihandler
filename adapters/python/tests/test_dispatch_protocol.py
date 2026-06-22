# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
from __future__ import annotations

from urirun import v2
from urirun.runtime import _runtime as runtime, dispatch_protocol as dp


def _registry():
    return v2.compile_registry({
        "version": "urirun.bindings.v2",
        "bindings": {
            "util://h/echo/command/run": {
                "kind": "command", "adapter": "argv-template",
                "argv": ["python3", "-c", "import json;print(json.dumps({'hi': 1}))"],
                "inputSchema": {"type": "object", "additionalProperties": False, "properties": {}},
            },
        },
    })


# ---- request side --------------------------------------------------------------

def test_normalize_accepts_mode_and_execute_bool():
    assert dp.normalize_request({"uri": "a://b/c/d"}) == {"uri": "a://b/c/d", "payload": {}, "mode": "dry-run"}
    assert dp.normalize_request({"uri": "a://b/c/d", "mode": "execute"})["mode"] == "execute"
    assert dp.normalize_request({"uri": "a://b/c/d", "execute": True})["mode"] == "execute"
    assert dp.normalize_request({"uri": "a://b/c/d", "execute": False})["mode"] == "dry-run"
    assert dp.normalize_request({"uri": "a://b/c/d", "payload": None})["payload"] == {}


def test_validate_request_flags_problems():
    assert dp.validate_request({"uri": "util://h/echo/command/run", "mode": "execute"}) == []
    assert any("required" in e for e in dp.validate_request({}))
    assert any("absolute" in e for e in dp.validate_request({"uri": "noscheme"}))
    assert any("payload" in e for e in dp.validate_request({"uri": "a://b/c/d", "payload": 5}))
    assert any("mode" in e for e in dp.validate_request({"uri": "a://b/c/d", "mode": "go"}))


def test_make_request_is_canonical():
    assert dp.make_request("a://b/c/d", {"x": 1}, "execute") == {"uri": "a://b/c/d", "payload": {"x": 1}, "mode": "execute"}


# ---- dispatch + reply ----------------------------------------------------------

def test_dispatch_executes_under_policy_and_data_flows():
    reg = _registry()
    policy = runtime.build_policy(None, ["util://**"], None)
    env = dp.dispatch({"uri": "util://h/echo/command/run", "mode": "execute"}, reg, policy=policy)
    reply = dp.reply_fields(env)
    assert reply["ok"] is True
    assert reply["dryRun"] is False
    assert reply["data"] == {"hi": 1}                          # argv stdout parsed to data
    assert reply["meta"]["adapter"] == "argv-template"
    assert dp.validate_reply(env) == []


def test_dispatch_dry_run_is_the_default():
    reg = _registry()
    env = dp.dispatch({"uri": "util://h/echo/command/run"}, reg)
    assert dp.reply_fields(env)["dryRun"] is True


def test_dispatch_rejects_invalid_request_with_structured_error():
    env = dp.dispatch("not-a-uri", _registry())
    assert env["ok"] is False
    assert env["error"]["status"] == 400
    assert dp.validate_reply(env) == []                        # a failed reply still conforms


def test_reply_fields_projects_each_adapter_shape():
    assert dp.reply_fields({"ok": True, "uri": "a://b/c/d", "mode": "execute",
                            "result": {"type": "function", "value": {"k": 1}}})["data"] == {"k": 1}
    assert dp.reply_fields({"ok": True, "uri": "a://b/c/d", "mode": "execute",
                            "result": {"stdout": "hello"}})["data"] == "hello"


def test_schemas_are_published():
    assert dp.REQUEST_SCHEMA["required"] == ["uri"]
    assert "ok" in dp.REPLY_SCHEMA["required"]
