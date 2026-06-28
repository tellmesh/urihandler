# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# Single-source guard for the routing-kernel extraction (urirun-connector-router). The routing
# kernel moved OUT of the monorepo into the urirun-connector-router package; urirun_node.routing
# (and the urirun.node.routing alias) must stay a THIN re-export shim — never a second, parallel
# routing implementation that drifts from the package. Same shape as urirun-contract's
# "toolkit is a re-export, not a copy" gate and test_runtime_extractable's core-creep ratchet.
import ast
from pathlib import Path

import pytest

_IMPORT_ROOT = Path(__file__).resolve().parents[1]   # …/urirun/adapters/python
_SHIMS = [
    _IMPORT_ROOT / "urirun_node" / "routing.py",
    _IMPORT_ROOT / "urirun" / "node" / "routing.py",
]


def _own_definitions(path: Path) -> list[str]:
    """Top-level function/class defs the shim declares ITSELF (a re-export must declare none —
    `from urirun_connector_router.routing import *` brings the real symbols in)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]


def test_routing_shim_is_a_thin_reexport_not_a_parallel_impl():
    for shim in _SHIMS:
        if not shim.exists():
            continue
        defs = _own_definitions(shim)
        assert not defs, (
            f"{shim} declares its own {defs} — the routing kernel lives in "
            "urirun-connector-router; this file must stay a re-export shim "
            "(`from urirun_connector_router.routing import *`), not a parallel implementation.")


def test_routing_shim_reexports_from_the_extracted_package():
    present = [s for s in _SHIMS if s.exists()]
    if not present:
        pytest.skip("routing shim not present (routing kernel not extracted in this checkout)")
    # The chain must ROOT at the extracted package: urirun_node.routing re-exports straight from
    # urirun_connector_router; the urirun.node.routing alias may chain through urirun_node.routing.
    blob = "\n".join(s.read_text(encoding="utf-8") for s in present)
    assert "urirun_connector_router" in blob, (
        "no routing shim re-exports from urirun_connector_router — the kernel's single source is "
        "the extracted package")
    for shim in present:
        src = shim.read_text(encoding="utf-8")
        assert ("urirun_connector_router" in src) or ("urirun_node" in src), (
            f"{shim} neither re-exports the package nor chains to the canonical routing shim")
