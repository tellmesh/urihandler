#!/usr/bin/env bash
# One command to get a WORKING dev environment after a kernel extraction.
#
# The monorepo shims to several real-source sibling packages (contract, routing, twin,
# declarative, widgets, artifacts). When a kernel is freshly extracted, the dev venv and CI
# break with `ModuleNotFoundError: No module named 'urirun_connector_router'` (etc.) until the
# new sibling is installed editable — this bit the test baseline repeatedly. Run this after any
# extraction (or to bootstrap a fresh checkout) to install every extracted sibling in dep order.
#
#   bash scripts/dev-install.sh           # editable-install the extracted siblings + urirun
#   bash scripts/dev-install.sh --check   # only verify each `urirun_*` shim imports (exit 1 if not)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SIB="$(cd "$ROOT/.." && pwd)"
CHECK="${1:-}"

# Real-source extracted packages the monorepo imports/shims to, in dependency order
# (leaf kernels first; widgets/artifacts depend on the routing+contract kernels).
SIBLINGS=(
  urirun-contract
  urirun-flow
  urirun-declarative
  urirun-connector-router
  urirun-connector-twin
  urirun-widgets
  urirun-artifacts
)
# --check verifies only the CORE kernels whose absence breaks urirun's own import chain
# (and the routing shim that re-exports the extracted routing kernel). twin/widgets/artifacts
# are leaf consumers with import-time connector registration — they are verified by their own
# test-CI, not by a bare top-level import here (which can trip their registration side-effects).
CORE_IMPORTS=(urirun_contract urirun_flow urirun_declarative urirun_connector_router)

if [ "$CHECK" = "--check" ]; then
  fail=0
  for m in "${CORE_IMPORTS[@]}"; do
    if python -c "import $m" 2>/dev/null; then echo "  ok   import $m"; else echo "  MISS import $m"; fail=1; fi
  done
  python -c "import urirun.node.routing" 2>/dev/null && echo "  ok   urirun.node.routing (extracted-routing shim resolves)" || { echo "  MISS urirun.node.routing"; fail=1; }
  [ "$fail" -eq 0 ] && echo "OK: core extracted-kernel shims import — dev env healthy" || { echo "FAIL: run 'bash scripts/dev-install.sh' to repair the dev env"; exit 1; }
  exit 0
fi

for s in "${SIBLINGS[@]}"; do
  d="$SIB/$s"
  [ -f "$d/pyproject.toml" ] || { echo "  skip $s (not present)"; continue; }
  echo "== pip install -e $s =="
  python -m pip install -e "$d" -q
done
echo "== pip install -e urirun (adapters/python) =="
python -m pip install -e "$ROOT/adapters/python" -q || true
echo "dev env ready — verifying shims:"
exec "$0" --check
