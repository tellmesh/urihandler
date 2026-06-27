#!/usr/bin/env bash
# Verify a fresh pip install of urirun==VERSION from PyPI delivers all 8 bundled
# sub-namespaces and that the host↔bundle shims resolve to the same classes.
#
# Run AFTER make publish, not before (needs the version to be on PyPI).
# Usage:
#   scripts/test_pypi_install.sh              # uses root VERSION
#   scripts/test_pypi_install.sh 0.4.183      # explicit version
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${1:-$(cat "$ROOT/VERSION")}"
VENV="/tmp/_urirun_pypi_gate"

echo "==> test-published: pip install urirun==$VERSION (clean venv, no editable, no URIRUN_KERNEL_SRC)"
rm -rf "$VENV"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet "urirun==$VERSION"

"$VENV/bin/python3" - "$VERSION" <<'PY'
import importlib, sys

version = sys.argv[1]

# ── 8 bundled sub-namespaces: module + sentinel symbol ────────────────────────
BUNDLE_CHECKS = [
    # (import_path,                      sentinel_symbol)
    ("urirun_runtime._runtime",          "DEFAULT_TIMEOUT"),
    ("urirun_connectors_toolkit.connector_sdk", "load_manifest"),
    ("urirun_cdp.cdp",                   "CdpError"),
    ("urirun_contracts.event_schema",    "StepEvent"),
    ("urirun_twin.twin_store",           "TwinMemory"),
    ("urirun_flow.flow",                 "make_flow"),
    ("urirun_node.server",               "serve_node"),
    # urirun_scanner shims to external urirun_connector_scanner — test namespace only
    ("urirun_scanner",                   None),
]

# ── Shim compatibility: host/node paths must resolve to bundle classes ─────────
SHIM_CHECKS = [
    # (shim_import_path,                 bundle_import_path,           symbol)
    ("urirun.node.event_schema",         "urirun_contracts.event_schema",  "StepEvent"),
    ("urirun.node.twin_store",           "urirun_twin.twin_store",          "TwinMemory"),
    ("urirun.node.flow",                 "urirun_flow.flow",                "make_flow"),
    ("urirun.runtime._runtime",          "urirun_runtime._runtime",         "DEFAULT_TIMEOUT"),
]

failures = []

for mod_path, symbol in BUNDLE_CHECKS:
    try:
        m = importlib.import_module(mod_path)
        if symbol and not hasattr(m, symbol):
            failures.append(f"MISSING  {mod_path}.{symbol}")
        else:
            tag = f"{mod_path}.{symbol}" if symbol else f"{mod_path} (namespace)"
            print(f"  ok  {tag}")
    except Exception as e:
        failures.append(f"IMPORT   {mod_path}: {e}")

for shim_path, bundle_path, symbol in SHIM_CHECKS:
    try:
        shim_mod = importlib.import_module(shim_path)
        bundle_mod = importlib.import_module(bundle_path)
        shim_obj = getattr(shim_mod, symbol, None)
        bundle_obj = getattr(bundle_mod, symbol, None)
        if shim_obj is None:
            failures.append(f"SHIM MISSING  {shim_path}.{symbol}")
        elif shim_obj is not bundle_obj:
            failures.append(f"SHIM DIVERGED {shim_path}.{symbol} is not {bundle_path}.{symbol}")
        else:
            print(f"  ok  shim:{shim_path}.{symbol} is bundle:{bundle_path}.{symbol}")
    except Exception as e:
        failures.append(f"SHIM ERROR {shim_path}: {e}")

if failures:
    print(f"\nFAILED ({len(failures)} issues):", file=sys.stderr)
    for f in failures:
        print(f"  {f}", file=sys.stderr)
    sys.exit(1)

print(f"\nall {len(BUNDLE_CHECKS)} bundles + {len(SHIM_CHECKS)} shims ok  (urirun=={version})")
PY

echo "==> test-published: PASSED for urirun==$VERSION"
rm -rf "$VENV"
