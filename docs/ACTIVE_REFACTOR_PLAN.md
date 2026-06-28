# Active refactor plan

Status: 2026-06-28

This is the active execution plan after the `urirun-contract` and
`urirun-connector-router` extractions. Older roadmap sections remain useful as
history, but this file is the current order of work.

## Verified State

Checked against the repo on 2026-06-28:

- Contract single-source is closed in `urirun-contract`: `make check` runs
  `ci/pre_commit.sh`, and that runs `check_single_source`, fleet coverage,
  `windowpair` conform, regen-check and additive-only compatibility.
- The old `urirun_connectors_toolkit.contract_*` paths are compatibility
  facades. The real implementation lives in `urirun_contract/*`.
- Reversibility is no longer a parallel declaration: `urirun_twin.reversible`
  exposes `schema_from_contracts` and `schema_from_bindings`, both delegating to
  `urirun_contract.contract_reversible`.
- Fleet coverage is ratcheted, not strict: `24/38` connectors have a contract,
  there are no mutating connectors without any contract, but `1` connector is
  still partial with mutating routes missing route-level contract entries:
  `twin`. The baseline is tightened to that single known partial.
- `urirun-connector-kvm` is route-complete for mutating routes: `27` contracts,
  `3` wires, full xlang proof active under `URIRUN_CONTRACT_CHECK=1`.
- `urirun-contract` JSON Schema export now preserves `?T` as optional and
  nullable, matching the Python gate and the JS/Go/Rust xlang readers.
- `urirun-connector-router` is a real-source package with install/test/smoke,
  single-source, build checks and package CI.
- `project.toon.yaml` in `urirun` still points at large owner modules
  (`host/dashboard.js`, `host/host_dashboard.py`, `host/chat_orchestrator.py`,
  `host/object_registry.py`, `urirun_node/server.py`). Those are extraction
  targets, not contract-kernel problems.

## Target

`urirun` becomes a small URI runtime and CLI:

- compile/validate/list/run URI registries,
- hold envelope, error taxonomy, policy and minimal adapters,
- discover connector/service entry points,
- expose compatibility shims only where needed.

Everything else moves to an owner package:

- contracts and contract gates: `urirun-contract`,
- route planning and pre-dispatch diagnostics: `urirun-connector-router`,
- flow model, recovery, rollback, thin driver: `urirun-flow`,
- node server, mesh, deploy, keyauth, transport: future `urirun-node`,
- host chat/dashboard/scanner processes: `urirun-service-*`,
- artifacts/widgets/object surfaces: `urirun-artifacts`, `urirun-widgets`,
- domain capabilities: `urirun-connector-*`.

## Non-negotiable Invariants

1. One implementation, many shims. A moved kernel has exactly one real source;
   old import paths re-export it.
2. A mutating route ships a contract before it becomes autonomous.
3. NL execution is routed before dispatch. Every step must have `runsOn` or a
   typed `ROUTING_BLOCKED` result.
4. `urirun` must not import host app, node service, scanner, dashboard, digital
   twin or connector implementations at top level.
5. Examples are acceptance tests. Every `examples/*` flow must run through the
   same `urirun-contract-*` and `urirun-connector-*` path as production.

## Phase 0 - Stabilize Current Extraction (Closed)

Goal: give router the same anti-drift discipline that contract already has.

Closed:

- Keep `urirun_node.routing` and `urirun.node.routing` as shims to
  `urirun-connector-router`.
- Route diagnosis now comes from `execute_flow(..., router_guard=True)` and the
  chat preview is inserted before dispatch.
- `urirun-connector-router` has a routing single-source gate.
- `urirun-connector-router make check` runs install, tests, bindings smoke,
  single-source and build metadata checks.
- `urirun-connector-router` has package CI for the same path.
- Pin `urirun-connector-router>=0.2.0` in the hub package and sibling dev install
  scripts.

Acceptance:

```bash
PYTHONPATH=urirun-connector-router:urirun-connector-twin:urirun-contract:urirun/adapters/python \
  python -m pytest -q \
  urirun-connector-router/tests \
  urirun/adapters/python/tests/test_chat*.py \
  urirun/adapters/python/tests/test_flow_rollup.py

cd urirun-connector-router
python -m pip install -e ".[connector,test]"
python -m pytest tests/ -q
python - <<'PY'
from urirun_connector_router import urirun_bindings
assert "router://host/plan/query/diagnose" in urirun_bindings()["bindings"]
PY
```

## Phase 1 - Make Fleet Contracts Route-Complete

Goal: move from ratchet coverage to strict route-level coverage for every
mutating connector route.

Tasks:

- Keep `urirun-contract make check` as the default contract gate; it is already
  the proof point for single-source, regen-check and compatibility.
- Burn down known partials in `ci/fleet_coverage.baseline.json`:
  `twin`.
- Keep fleet coverage strict about route identity: full URI and `route_key`
  match, but not bare `command/<verb>` suffixes.
- Generate skeleton route contracts from `connector.manifest.json`,
  decorators and `urirun_bindings()`; humans/LLM fill effect, examples and
  reversibility.
- Turn `python ci/fleet_coverage.py .. --baseline ... --strict` green and then
  make strict the default.
- Export JSON Schema and TypeScript artifacts beside each package
  `contracts.json`; validate them in package CI.
- Add shared golden examples for Python and Go consumers where a connector has a
  transport/service peer.

Acceptance:

```bash
cd urirun-contract
make check
python ci/fleet_coverage.py .. --baseline ci/fleet_coverage.baseline.json --strict
```

## Phase 2 - Move Flow Out of the Hub

Goal: `urirun-flow` owns flow documents, thin driver, recovery, reversible
ledger, rollback and verification integration.

Tasks:

- Turn `urirun-flow` from meta-wrapper into real-source package or explicitly
  keep it meta and document why.
- Move `urirun_flow/*` source to `urirun-flow` if choosing real-source.
- Keep `urirun.node.flow` and historical paths as shims.
- Move flow tests that do not need host/dashboard into `urirun-flow/tests`.
- Keep host chat as a consumer: it builds flow, asks router, calls flow engine.

Acceptance:

```bash
PYTHONPATH=urirun-flow:urirun-connector-router:urirun-contract:urirun/adapters/python \
  python -m pytest -q \
  urirun/adapters/python/tests/test_flow.py \
  urirun/adapters/python/tests/test_flow_reversible.py \
  urirun/adapters/python/tests/test_flow_twin.py \
  urirun/adapters/python/tests/test_flow_scheme.py
```

## Phase 3 - Split Host App and Node Service

Goal: `urirun host ...` and `urirun node ...` become shims to service packages,
not core implementation.

Tasks:

- Create or finalize `urirun-node` as owner of node server, mesh, transport,
  deploy, config and keyauth.
- Create or finalize `urirun-service-chat` as owner of dashboard chat,
  orchestration, DB log and operator UI API.
- Move scanner runtime into `urirun-service-scanner`; keep document processing
  in connectors.
- Keep only CLI forwarding commands in `urirun`.
- Add top-level import smoke: `python -c "import urirun"` must not import host,
  node, dashboard, scanner or connector implementation modules.

Acceptance:

```bash
python - <<'PY'
import sys
import urirun
loaded = [m for m in sys.modules if m.startswith(("urirun.host", "urirun_node", "urirun_scanner"))]
assert not loaded, loaded
PY
```

## Phase 4 - Connector Fleet Conformance

Goal: every connector has the same install, contract, route and example shape.

Tasks:

- Require `connector.manifest.json` or `urirun_bindings()` for every connector.
- Require `contracts.json` for side-effect routes.
- Run `router://host/plan/query/diagnose` against every example flow.
- Run dry-run and execute-smoke where the connector can operate locally.
- Mark hardware/network/browser tests with explicit environment requirements.
- Add fleet report grouped by scheme, package, route count, contract count and
  example count.
- Once Phase 1 is strict-green, require every connector CI to run its local
  contract conformance or explicitly declare that it has no URI surface.

Acceptance:

```bash
cd urirun-contract
python ci/fleet_coverage.py .. --strict
PYTHONPATH=../urirun-connector-router:../urirun-contract:../urirun/adapters/python \
  python -m pytest -q tests/test_fleet_coverage.py
```

## Phase 5 - Documentation Cleanup

Goal: docs describe the architecture that actually runs.

Tasks:

- Mark historical sections in `REFACTOR_ROADMAP.md` as landed/history.
- Make `ACTIVE_REFACTOR_PLAN.md` the first link for current refactor work.
- Update `COMPONENTS.md` to show real-source vs meta-wrapper packages.
- Update examples README files to mention contract/router acceptance tests.
- Remove docs that instruct editing old vendored contract/router copies.

Acceptance:

- No doc says routing lives in `urirun.node.routing` except as a compatibility
  shim.
- No doc says contract gate/codegen should be copied into connectors.
- Every new package has README, pyproject, test command and ownership statement.

## Immediate Next Tasks

1. Add an examples test that diagnoses all `examples/*/flow*.json|yaml` through
   `urirun-connector-router`.
2. Reduce fleet partial coverage by finishing the remaining mutating gaps in
   `twin`: plan/mock/sandbox/proof/flow command routes.
3. Wire `urirun-contract` JSON Schema validation into connector/example CI,
   using the KVM xlang proof as the reference shape.
4. Audit `project/map.toon.yaml` for remaining large owners inside `urirun`:
   `host/chat_orchestrator.py`, `host/dashboard.js`, `host/host_dashboard.py`,
   `host/object_registry.py`, `urirun_node/server.py`.
5. Choose whether `urirun-flow`, `urirun-runtime`, `urirun-cdp` stay
   meta-wrappers or become real-source packages; document one decision per
   package.
6. Create a top-level smoke suite for host/node/local/remote scenarios:
   host-only, explicit node, inferred node, stale URL target, route.node override,
   missing route, unreachable node, unsafe command.

## Stop Conditions

Do not move another package before these are true:

- current router/chat/flow tests are green,
- contract single-source gate is green,
- routing single-source gate exists,
- router package check runs install-smoke and tests,
- fresh install path can import `urirun` without sibling checkout assumptions,
- examples still validate through `urirun-contract` and diagnose through
  `urirun-connector-router`,
- fleet strict coverage has a deliberate burn-down plan for every known partial.
