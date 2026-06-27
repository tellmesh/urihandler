#!/usr/bin/env python3
"""Emit the NEUTRAL contract artifact from a real connector's CONTRACTS.

The point: the single source of truth becomes a language-neutral JSON file (inp/out/effect/
reversible/inverseRoute/errors/examples). Every language's gate is a thin READER of this file —
not a re-translation. Here we emit from the real fs connector (fully runnable, has a reversible
write-b64/delete pair), so the cross-language proof runs against actual production contracts.
"""
import importlib
import json
import sys

# Emit any connector's contracts: `emit_contracts.py [module]` where module exposes CONTRACTS.
_MOD = sys.argv[1] if len(sys.argv) > 1 else "urirun_connector_fs.contracts"
CONTRACTS = importlib.import_module(_MOD).CONTRACTS


def emit() -> dict:
    out = {"schemaVersion": 1, "contracts": {}}
    for route, c in CONTRACTS.items():
        out["contracts"][route] = {
            "effect": c.effect,
            "reversible": c.reversible,
            "inverseRoute": c.inverse_route or None,
            "inp": c.inp,
            "out": c.out,
            "errors": list(c.errors),
            "examples": list(c.examples),
        }
    return out


if __name__ == "__main__":
    doc = emit()
    json.dump(doc, sys.stdout, indent=2)
    print(file=sys.stderr)
    print(f"emitted {len(doc['contracts'])} contracts", file=sys.stderr)
