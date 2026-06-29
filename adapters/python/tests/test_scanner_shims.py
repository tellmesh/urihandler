from __future__ import annotations

import importlib
from pathlib import Path


_ADAPTER_ROOT = Path(__file__).resolve().parents[1] / "urirun_scanner"
_SHIM_MODULES = [
    "artifacts_admin",
    "document_metadata",
    "document_sync",
    "scanner_bridge",
    "scanner_net",
    "scanner_service",
]


def test_urirun_scanner_modules_are_thin_shims():
    for name in _SHIM_MODULES:
        path = _ADAPTER_ROOT / f"{name}.py"
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(lines) <= 10, f"{path} must stay a shim, not a bundled fallback"
        assert "except ImportError" not in path.read_text(encoding="utf-8")


def test_urirun_scanner_reexports_connector_modules():
    for name in _SHIM_MODULES:
        shim = importlib.import_module(f"urirun_scanner.{name}")
        moved = importlib.import_module(f"urirun_connector_scanner.{name}")
        assert Path(shim.__file__).resolve() == Path(moved.__file__).resolve()
        assert shim.__name__ == moved.__name__
