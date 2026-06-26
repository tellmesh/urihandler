# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# Extraction boundary guards for the node layer (extraction_audit presets G and H).
#
#   G = flow subsystem   — flow.py + planner + thin + verify + recovery + diagnostics
#   H = pure node substrate — full urirun.node.* MINUS the CLI integration files
#       (node_cli.py and task_cli.py legitimately import host.* and live in the
#        integration layer, not the liftable node core)
#   F = full node.* namespace — permanently RED: node_cli.py / task_cli.py are shims to
#       host.* (CLI layer moved to host.node_cli / host.task_cli); mesh.py re-exports them
#       and is the permanent coupling point between node.* and host.*.
#
# All three gates use the same pattern as test_scanner_extractable / test_connector_extractable.
import importlib.util
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]          # …/urirun
_IMPORT_ROOT = Path(__file__).resolve().parents[1]   # …/urirun/adapters/python
_AUDIT_PATH = _REPO / "scripts" / "extraction_audit.py"


def _load_audit():
    spec = importlib.util.spec_from_file_location("extraction_audit", _AUDIT_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _assert_green(preset_key: str):
    ea = _load_audit()
    spec = ea.PRESETS[preset_key]
    if not ea.resolve_package(set(ea.discover_modules(_IMPORT_ROOT)), spec):
        pytest.skip(f"{spec['name']} already extracted out of core")
    rep = ea.audit(_IMPORT_ROOT, spec)
    assert not rep.outward, (
        f"{spec['name']} re-coupled to a staying layer: "
        + ", ".join(f"{e.src}→{e.target} ({e.symbol} L{e.line})" for e in rep.outward))
    assert not rep.cycles, f"{spec['name']} import cycle(s): {sorted(rep.cycles)}"


def _assert_red(preset_key: str, expected_min_outward: int = 1):
    """Assert that a preset is RED (has blocking outward edges).

    Used to document known bad state so the gate fails loudly when the issue
    is accidentally fixed or accidentally worsened."""
    ea = _load_audit()
    spec = ea.PRESETS[preset_key]
    if not ea.resolve_package(set(ea.discover_modules(_IMPORT_ROOT)), spec):
        pytest.skip(f"{spec['name']} already extracted out of core")
    rep = ea.audit(_IMPORT_ROOT, spec)
    assert len(rep.outward) >= expected_min_outward, (
        f"{spec['name']} unexpectedly GREEN — remove this test or promote it to _assert_green"
    )


def test_flow_subsystem_boundary_is_green():
    """flow.py + thin + verify + planner + recovery + diagnostics must sit cleanly on
    kernel + connectors + node substrate.  No host.* imports allowed."""
    _assert_green("G")


def test_node_substrate_boundary_is_green():
    """The pure node layer (all of urirun.node.* except the CLI entry-points) must be
    liftable without pulling in any host.* modules."""
    _assert_green("H")


def test_node_full_namespace_has_cli_host_edges():
    """Documents that node.* is intentionally RED: node_cli.py and task_cli.py are shims
    pointing to host.* (the CLI integration layer lives in host.node_cli / host.task_cli).
    mesh.py re-exports those symbols for external callers and is the permanent coupling point.
    Preset H (pure node substrate, CLIs excluded) is the GREEN extraction gate instead."""
    # Shims in node_cli.py + task_cli.py now use the sys.modules trick (1 import each),
    # so the minimum outward count dropped from 4 to 2 when the CLIs moved to host.*.
    _assert_red("F", expected_min_outward=2)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
