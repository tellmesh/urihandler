from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path
from types import ModuleType


def _add_monorepo_connector_path() -> None:
    root = Path(__file__).resolve().parents[4]
    candidate = root / "urirun-connector-scanner"
    if not (candidate / "urirun_connector_scanner").is_dir():
        return
    raw = str(candidate)
    if raw not in sys.path:
        sys.path.insert(0, raw)


def load_connector_module(name: str) -> ModuleType:
    module_name = f"urirun_connector_scanner.{name}"
    try:
        return import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name != "urirun_connector_scanner":
            raise
    _add_monorepo_connector_path()
    try:
        return import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name != "urirun_connector_scanner":
            raise
        raise ModuleNotFoundError(
            "urirun_scanner is a compatibility shim; install "
            "`urirun-connector-scanner` or use the if-uri monorepo checkout."
        ) from exc
