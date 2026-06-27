#!/usr/bin/env python3
"""Python gate — loads the NEUTRAL contracts.json (not the dataclass) and reuses the kernel
validator. Proves the kernel is DATA-SHAPE-DRIVEN: it validates contracts loaded from JSON exactly
as it does ones built from @dataclass. CLI mirrors gate.mjs so they pipe together.

  conform                 — validate every contract's golden examples (the oracle)
  produce <route>         — print the golden ok envelope as JSON (a "node" emitting a result)
  consume <route>         — read an envelope on stdin, validate it against <route>.out
"""
import json
import os
import sys
from types import SimpleNamespace

from urirun_connectors_toolkit.contract_gate import check, conform

DOC = json.load(open(os.path.join(os.path.dirname(__file__), "contracts.json")))
CONTRACTS = {r: SimpleNamespace(inverse_route=c.get("inverseRoute") or "",
                                **{k: v for k, v in c.items() if k != "inverseRoute"})
             for r, c in DOC["contracts"].items()}


def _ok_example(route):
    for ex in CONTRACTS[route].examples:
        if ex["result"].get("ok"):
            return ex["result"]
    raise SystemExit(f"{route}: no golden ok example")


def main() -> int:
    cmd = sys.argv[1]
    if cmd == "conform":
        conform(CONTRACTS)
        print(f"PY  conform OK — {len(CONTRACTS)} contracts", file=sys.stderr)
        return 0
    if cmd == "produce":
        json.dump(_ok_example(sys.argv[2]), sys.stdout)
        return 0
    if cmd == "consume":
        route = sys.argv[2]
        env = json.load(sys.stdin)
        try:
            check(CONTRACTS[route].out, env, "out")
            json.dump({"ok": True, "lang": "py", "route": route}, sys.stdout)
            return 0
        except AssertionError as exc:
            json.dump({"ok": False, "lang": "py", "route": route, "problem": str(exc)}, sys.stdout)
            return 1
    raise SystemExit(f"unknown cmd {cmd!r}")


if __name__ == "__main__":
    raise SystemExit(main())
