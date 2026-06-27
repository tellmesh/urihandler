#!/usr/bin/env python3
"""Python wire peer — cross-ROUTE handoff over a wire, reusing the KERNEL wire functions.

Proves the kernel's wire layer (wire_payload / consumer_input_check, added alongside check_wire) is
data-shape-driven: it operates on the neutral contracts loaded from JSON, so a producer in one
language and a consumer in another compose through one contract. Mirrors peer.mjs.

  conform                 — static-check every wire edge (check_wire)
  produce <route>         — print the golden ok envelope
  consume <prod> <cons>   — read an envelope on stdin, build the consumer payload via the wire,
                            validate it, print {ok, mode, builtInput, problems}
"""
import json
import os
import sys
from types import SimpleNamespace

from urirun_connectors_toolkit.contract_gate import (
    check_wire, consumer_input_check, find_wire, wire_payload,
)

DOC = json.load(open(os.path.join(os.path.dirname(__file__),
                                  os.environ.get("XLANG_CONTRACTS", "contracts.kvm.json"))))
CONTRACTS = {r: SimpleNamespace(inverse_route=c.get("inverseRoute") or "",
                                **{k: v for k, v in c.items() if k != "inverseRoute"})
             for r, c in DOC["contracts"].items()}
WIRES = [SimpleNamespace(**w) for w in DOC["wires"]]


def _ok_example(route):
    for ex in CONTRACTS[route].examples:
        if ex["result"].get("ok"):
            return ex["result"]
    raise SystemExit(f"{route}: no golden ok example")


def main() -> int:
    cmd = sys.argv[1]
    if cmd == "conform":
        bad = []
        for w in WIRES:
            bad += [f"{w.producer}->{w.consumer}: {p}" for p in check_wire(w, CONTRACTS)]
        if bad:
            print("PY  wire conform FAIL:", bad, file=sys.stderr)
            return 1
        print(f"PY  wire conform OK — {len(WIRES)} edges", file=sys.stderr)
        return 0
    if cmd == "produce":
        json.dump(_ok_example(sys.argv[2]), sys.stdout)
        return 0
    if cmd == "consume":
        producer, consumer = sys.argv[2], sys.argv[3]
        envelope = json.load(sys.stdin)
        wire = find_wire(WIRES, producer, consumer)
        payload = wire_payload(wire, envelope)
        mode, problems = consumer_input_check(CONTRACTS[consumer], payload, wire)
        json.dump({"ok": not problems, "lang": "py", "mode": mode,
                   "builtInput": payload, "problems": problems}, sys.stdout)
        return 0 if not problems else 1
    raise SystemExit(f"unknown cmd {cmd!r}")


if __name__ == "__main__":
    raise SystemExit(main())
