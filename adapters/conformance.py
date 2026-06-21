#!/usr/bin/env python3
"""Cross-language SDK conformance: every urirun SDK must emit the same contract.

Builds the reference `hash` connector with each available language SDK, reduces
each output to its essential contract, and asserts they are identical and valid.
This is the executable definition of "the SDKs are standardized": same connector
in, same urirun.bindings.v2 out.

    python3 adapters/conformance.py

Adding a language is one entry in LANGS below (plus its example/hash connector).
A language whose toolchain is absent is skipped, so CI stays green. Exit 0 when
all available SDKs agree and validate, 1 otherwise.
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROUTE = "hash://host/sha256/command/file"

# name, required tool, command (run in adapters/<dir>), extra env.
LANGS = [
    {"name": "go", "tool": "go", "cmd": ["go", "run", "./example/hash-connector"], "dir": "go"},
    {"name": "php", "tool": "php", "cmd": ["php", "example/hash-connector.php"], "dir": "php"},
    {"name": "ruby", "tool": "ruby", "cmd": ["ruby", "example/hash_connector.rb"], "dir": "ruby"},
    {"name": "perl", "tool": "perl", "cmd": ["perl", "example/hash_connector.pl"], "dir": "perl"},
    {"name": "bash", "tool": "bash", "cmd": ["bash", "example/hash-connector.sh"], "dir": "bash"},
    {"name": "rust", "tool": "cargo", "cmd": ["cargo", "run", "--quiet", "--example", "hash_connector"],
     "dir": "rust", "env": {"CARGO_NET_OFFLINE": "true"}},
    {"name": "ts", "tool": "tsc",
     "cmd": ["bash", "-c", "tsc -p . >/dev/null 2>&1 && node dist/example/hash-connector.js"], "dir": "ts"},
    {"name": "java", "tool": "javac",
     "cmd": ["bash", "-c", "d=$(mktemp -d); javac -d $d Urirun.java example/HashConnector.java && java -cp $d HashConnector"],
     "dir": "java"},
    {"name": "csharp", "tool": "dotnet",
     "cmd": ["dotnet", "run", "--project", ".", "--verbosity", "quiet"], "dir": "csharp"},
]


def essential(doc: dict) -> dict:
    """Reduce a bindings.v2 document to the language-independent contract."""
    assert doc.get("version") == "urirun.bindings.v2", "wrong version"
    b = doc["bindings"][ROUTE]
    schema = b.get("inputSchema", {})
    return {
        "route": ROUTE,
        "kind": b.get("kind"),
        "adapter": b.get("adapter"),
        "argv": list(b.get("argv", [])),
        "required": sorted(schema.get("required", [])),
        "properties": sorted((schema.get("properties") or {}).keys()),
        "additionalProperties": schema.get("additionalProperties", None),
    }


def python_reference() -> dict:
    sys.path.insert(0, os.path.join(HERE, "python"))
    import urirun

    c = urirun.connector("hash", scheme="hash")

    @c.command("sha256/command/file")
    def f(path: str):  # noqa: ARG001 - the signature is the schema
        return ["sha256sum", "{path}"]

    return c.bindings()


def main() -> int:
    outputs: dict[str, dict] = {"python": python_reference()}

    for lang in LANGS:
        if not shutil.which(lang["tool"]):
            print(f"skip {lang['name']} ({lang['tool']} not available)")
            continue
        env = {**os.environ, **lang.get("env", {})}
        try:
            out = subprocess.run(lang["cmd"], cwd=os.path.join(HERE, lang["dir"]),
                                 capture_output=True, text=True, check=True, env=env)
            outputs[lang["name"]] = json.loads(out.stdout)
        except Exception as exc:  # noqa: BLE001
            print(f"WARN {lang['name']}: {exc}")

    sys.path.insert(0, os.path.join(HERE, "python"))
    from urirun import validate_binding_document as validate

    contracts: dict[str, dict] = {}
    errors = 0
    for name, doc in outputs.items():
        result = validate(doc)
        ok = result.get("ok") if isinstance(result, dict) else result
        if not ok:
            print(f"FAIL {name}: bindings do not validate against urirun")
            errors += 1
            continue
        contracts[name] = essential(doc)

    ref = contracts.get("python")
    for name, contract in sorted(contracts.items()):
        if name == "python":
            continue
        if contract != ref:
            print(f"FAIL {name}: contract differs from python")
            print(f"  python: {json.dumps(ref, sort_keys=True)}")
            print(f"  {name}: {json.dumps(contract, sort_keys=True)}")
            errors += 1
        else:
            print(f"ok   {name}: matches python and validates")
    print("ok   python: reference, validates")

    print(f"\n{len(contracts)} SDK(s) checked, {errors} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
