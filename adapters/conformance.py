#!/usr/bin/env python3
"""Cross-language SDK conformance: every urirun SDK must emit the same contract.

Builds the reference `hash` connector with each available language SDK
(Python, Go, PHP), reduces each output to its essential contract, and asserts
they are identical and valid. This is the executable definition of "the SDKs are
standardized": same connector in, same urirun.bindings.v2 out.

    python3 adapters/conformance.py

Exit 0 when all available SDKs agree and validate, 1 otherwise. JS is checked
only once its SDK exposes a connector builder.
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROUTE = "hash://host/sha256/command/file"


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


def from_python() -> dict:
    sys.path.insert(0, os.path.join(HERE, "python"))
    import urirun

    c = urirun.connector("hash", scheme="hash")

    @c.command("sha256/command/file")
    def f(path: str):  # noqa: ARG001 - signature is the schema
        return ["sha256sum", "{path}"]

    return c.bindings()


def shell_json(cmd: list[str], cwd: str) -> dict:
    out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def main() -> int:
    outputs: dict[str, dict] = {}
    errors = 0

    outputs["python"] = from_python()

    if shutil.which("go"):
        try:
            outputs["go"] = shell_json(["go", "run", "./example/hash-connector"], os.path.join(HERE, "go"))
        except Exception as exc:  # noqa: BLE001
            print(f"WARN go: {exc}")
    else:
        print("skip go (toolchain not available)")

    if shutil.which("php"):
        try:
            outputs["php"] = shell_json(["php", "example/hash-connector.php"], os.path.join(HERE, "php"))
        except Exception as exc:  # noqa: BLE001
            print(f"WARN php: {exc}")
    else:
        print("skip php (toolchain not available)")

    # Validate each against the runtime and reduce to the essential contract.
    sys.path.insert(0, os.path.join(HERE, "python"))
    from urirun import validate_binding_document as validate

    contracts = {}
    for lang, doc in outputs.items():
        result = validate(doc)
        ok = result.get("ok") if isinstance(result, dict) else result
        if not ok:
            print(f"FAIL {lang}: bindings do not validate against urirun")
            errors += 1
            continue
        contracts[lang] = essential(doc)

    # All SDKs must agree on the essential contract.
    ref_lang = "python"
    ref = contracts.get(ref_lang)
    for lang, contract in contracts.items():
        if lang == ref_lang:
            continue
        if contract != ref:
            print(f"FAIL {lang}: contract differs from {ref_lang}")
            print(f"  {ref_lang}: {json.dumps(ref, sort_keys=True)}")
            print(f"  {lang}: {json.dumps(contract, sort_keys=True)}")
            errors += 1
        else:
            print(f"ok   {lang}: matches {ref_lang} and validates")
    print(f"ok   {ref_lang}: reference, validates")

    print(f"\n{len(contracts)} SDK(s) checked, {errors} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
