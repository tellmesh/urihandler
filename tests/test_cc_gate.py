"""Run the cyclomatic-complexity gate inside the default test lane.

`scripts/cc_gate.py` already enforces CC<=15 on the Python adapter, but it was only reachable
via the standalone `make complexity` target — separate from `make test`. Nothing in the default
test run stopped new code (whoever or whatever writes it) from merging a function over the limit,
and it repeatedly regressed when concurrent work added CC>15 helpers. Running the same gate here
keeps the analysis HEALTH clean by default; it skips gracefully where radon is not installed so
minimal environments (and the gate's own `pip install radon` hint) still apply elsewhere.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("radon", reason="radon not installed; CC gate runs via `make complexity` / CI")

_REPO_ROOT = Path(__file__).resolve().parent.parent  # urirun/
_GATE_PATH = _REPO_ROOT / "scripts" / "cc_gate.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("cc_gate", _GATE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_python_adapter_has_no_cc_offenders() -> None:
    gate = _load_gate()
    paths = [str(_REPO_ROOT / "adapters" / "python" / "urirun"), str(_REPO_ROOT / "scripts")]
    offenders = gate.find_offenders(paths, gate.DEFAULT_LIMIT)
    detail = "\n".join(f"  CC={cc} {path}:{line}  {name}" for cc, path, line, name in offenders)
    assert not offenders, (
        f"{len(offenders)} function(s) over CC={gate.DEFAULT_LIMIT} "
        f"(extract helpers / a dispatch table):\n{detail}"
    )
