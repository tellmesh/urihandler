# xlang — polyglot contract conformance proof

Proves the connector contract is **language-neutral**: one neutral `contracts.json` (emitted from a
real connector), validated independently by gates in **Python, JavaScript, and Go**, with real
cross-process / cross-language handoff and symmetric drift rejection — plus an **external
conformance driver** that calls a live served node by its real URI and validates the over-the-wire
response against the same contract.

The necessary condition: a **neutral artifact as the single source of truth** + a thin **reader** in
each language. A hand-written `contracts.<lang>` per language would be the original drift ×N.

## Files

| file | role |
|---|---|
| `emit_contracts.py [module]` | dump a connector's `CONTRACTS` → neutral `contracts.json` (default: `urirun_connector_fs.contracts`) |
| `gate.py` | Python gate — reuses the kernel validator loaded from JSON (proves it's data-shape-driven) |
| `gate.mjs` | JavaScript gate — ~60-line 1:1 port of the validator |
| `gate.go` | Go gate — port handling JSON `float64` ints (integrality check) + `map[string]any` for missing-vs-zero |
| `driver.py` | external conformance driver — calls a served node over HTTP, validates `result.value` against `out` |
| `run3.sh` | 3-language proof: conform + all-pairs round-trip + symmetric drift |
| `run_driver.sh` | serve a real fs node, validate its real over-the-wire responses |

## Run

```bash
PY=/path/to/venv/bin/python bash run3.sh        # Python + JS + Go on one contracts.json
PY=/path/to/venv/bin/python bash run_driver.sh  # external driver vs a live served node
```

Each gate CLI: `conform | produce <route> | consume <route>` (piped across processes).

## What each layer proves

- **Round-trip** (run3.sh): an envelope produced in language A is validated in language B against the
  shared contract; a drifted envelope is rejected by all languages with an identical diagnosis.
- **External driver** (run_driver.sh): catches what a round-trip cannot — a node that passes its own
  in-language gate but lies on the wire (serialization/transport/policy). It found that
  `requireConfirm` routes weren't executable over HTTP (the node now plumbs `confirm`).

## Per-language friction (handled in the ports)

- **Go**: JSON numbers decode to `float64` → `int` token checks integrality; validate `map[string]any`
  (not a struct) so absent keys are distinguishable from zero-values (`?optional` survives).
- **JS**: `Number.isInteger` for the `int` token.
- **Cross-cutting**: JSON number fidelity (`1.0` arrives as `1`) → tokens are defined by JSON type +
  integrality, not language types.
