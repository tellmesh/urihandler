# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""One generic exporter so EVERY connector gets the polyglot/schema/compile-time gate for free.

A connector declares ``CONTRACTS`` (and optionally ``WIRES``) once as dataclasses. From that single
source this module emits three neutral artifacts that the cross-language conformance harness and any
off-the-shelf consumer read:

  * ``contracts.json``        — neutral document (contracts + wires) the py/js/go/rust peers validate
  * ``contracts.schema.json`` — standard JSON Schema (draft 2020-12) per route input/output
  * ``ts/contracts.d.ts``     — TypeScript types for compile-time enforcement

The point of pushing this DOWN into the toolkit: the translation is pure and identical for all ~37
connectors, so the gate is not re-implemented per connector — each connector's emitter shrinks to one
call. Run for any connector::

    python -m urirun_connectors_toolkit.contract_export urirun_connector_kvm.contracts xlang

Note on neutral formats: ``contract_to_dict`` (contract_gate) emits the MCP/A2A registry shape
(``input``/``output`` keys, inverseRoute only when reversible). The polyglot harness needs a richer,
self-contained doc (``inp``/``out``, ``inverseRoute`` always present as null, plus the ``wires`` graph),
so ``neutral_document`` is its own serializer for that consumer.
"""
from __future__ import annotations

import importlib
import json
import os

from .contract_jsonschema import to_json_schema
from .contract_typescript import to_typescript

SCHEMA_VERSION = 1


def neutral_document(contracts: dict, wires=()) -> dict:
    """Build the polyglot ``contracts.json`` content from ``{route: Contract}`` + ``[Wire]``."""
    return {
        "schemaVersion": SCHEMA_VERSION,
        "source": "connector CONTRACTS (dataclass) — GENERATED, do not hand-edit",
        "contracts": {
            route: {
                "version": c.version,
                "effect": c.effect,
                "reversible": c.reversible,
                "inverseRoute": (c.inverse_route or None),
                "inp": c.inp,
                "out": c.out,
                "errors": list(c.errors),
                "examples": [dict(ex) for ex in c.examples],
            }
            for route, c in contracts.items()
        },
        "wires": [
            {"producer": w.producer, "consumer": w.consumer, "mapping": w.mapping,
             "note": getattr(w, "note", "")}
            for w in wires
        ],
    }


def schema_document(contracts: dict) -> dict:
    """Standard JSON Schema document: per-route ``input``/``output`` schemas."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "route contracts — generated JSON Schema",
        "source": "connector CONTRACTS (dataclass) — GENERATED, do not hand-edit",
        "routes": {
            route: {"input": to_json_schema(c.inp), "output": to_json_schema(c.out)}
            for route, c in contracts.items()
        },
    }


def write_artifacts(contracts: dict, wires=(), out_dir: str = ".") -> list[str]:
    """Write all three artifacts under ``out_dir`` (creates ``out_dir/ts`` for the .d.ts)."""
    os.makedirs(os.path.join(out_dir, "ts"), exist_ok=True)
    written = []

    def _dump_json(name, obj):
        path = os.path.join(out_dir, name)
        with open(path, "w") as fh:
            json.dump(obj, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        written.append(path)

    _dump_json("contracts.json", neutral_document(contracts, wires))
    _dump_json("contracts.schema.json", schema_document(contracts))
    ts_path = os.path.join(out_dir, "ts", "contracts.d.ts")
    with open(ts_path, "w") as fh:
        fh.write(to_typescript(contracts))
    written.append(ts_path)
    return written


def _load(module_path: str):
    """Import a connector's contracts module; return (CONTRACTS, WIRES)."""
    mod = importlib.import_module(module_path)
    contracts = getattr(mod, "CONTRACTS")
    wires = getattr(mod, "WIRES", [])
    return contracts, wires


def main(argv=None) -> int:
    import sys
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print("usage: python -m urirun_connectors_toolkit.contract_export "
              "<module.with.CONTRACTS> [out_dir]", file=sys.stderr)
        return 2
    module_path = args[0]
    out_dir = args[1] if len(args) > 1 else "."
    contracts, wires = _load(module_path)
    written = write_artifacts(contracts, wires, out_dir)
    print(f"wrote {len(written)} artefakty z {module_path} "
          f"({len(contracts)} tras, {len(wires)} krawędzi):")
    for p in written:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
