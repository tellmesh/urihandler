# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.

"""One shared out-of-process runner for ``local-function`` handlers.

``python -m urirun.exec <module>:<export>`` imports the connector's handler,
reads a JSON payload from **stdin**, calls ``handler(**payload)`` (filtered to its
signature), and writes the result as JSON to **stdout**. It is the single,
in-core replacement for every connector's hand-written ``_exec.py``: a route that
wants process isolation (untrusted code, crash containment, a heavy import kept
out of the host) uses the ``local-function-subprocess`` adapter, which spawns this
runner — the connector still declares the route once as a ``@handler`` and ships
no argv shim of its own.
"""

from __future__ import annotations

import contextlib
import importlib
import importlib.util
import inspect
import json
import os
import pkgutil
import sys


def _connector_module_candidates(module_name: str, export: str) -> list[str]:
    """Return canonical package modules for a legacy flat ref.

    Older/deployed nodes may advertise isolated handlers as ``core:capture``
    because the route was originally generated from a flat deploy. Installed
    connector packages expose the same handler at
    ``urirun_connector_<id>.core:capture``. Keep this fallback generic and
    deterministic: prefer ``URIRUN_EXEC_CONNECTOR`` when present, otherwise use
    exactly one installed connector package that has the requested export.
    """
    if "." in module_name or module_name != "core":
        return []
    connector = os.environ.get("URIRUN_EXEC_CONNECTOR", "").strip().replace("-", "_")
    if connector:
        pkg = connector if connector.startswith("urirun_connector_") else f"urirun_connector_{connector}"
        return [f"{pkg}.core"]
    matches: list[str] = []
    for mod in pkgutil.iter_modules():
        name = mod.name
        if not name.startswith("urirun_connector_"):
            continue
        candidate = f"{name}.core"
        if importlib.util.find_spec(candidate) is None:
            continue
        try:
            module = importlib.import_module(candidate)
        except Exception:  # noqa: BLE001 - a broken connector is not a candidate
            continue
        if hasattr(module, export):
            matches.append(candidate)
    return matches if len(matches) == 1 else []


def _resolve(ref: str):
    module_name, _, export = ref.partition(":")
    if not module_name or not export:
        raise ValueError(f"expected '<module>:<export>', got {ref!r}")
    try:
        return getattr(importlib.import_module(module_name), export)
    except ModuleNotFoundError as exc:
        if exc.name != module_name:
            raise
        for candidate in _connector_module_candidates(module_name, export):
            return getattr(importlib.import_module(candidate), export)
        raise


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("usage: python -m urirun.exec <module>:<export>  (payload JSON on stdin)", file=sys.stderr)
        return 2
    fn = _resolve(argv[0])
    raw = sys.stdin.read()
    payload = json.loads(raw) if raw.strip() else {}
    if not isinstance(payload, dict):
        payload = {}
    try:                                  # drop keys the handler doesn't accept
        params = inspect.signature(fn).parameters
        if not any(p.kind == p.VAR_KEYWORD for p in params.values()):
            payload = {k: v for k, v in payload.items() if k in params}
    except (TypeError, ValueError):
        pass
    # STDOUT is the result channel — its only content must be the JSON below, so the
    # subprocess adapter can `json.loads` it. A handler (or a library it imports, e.g.
    # litellm's "Provider List" banner) that prints to stdout would otherwise corrupt the
    # contract. Send any such chatter to stderr while the handler runs; restore stdout for
    # the one authoritative result write.
    with contextlib.redirect_stdout(sys.stderr):
        result = fn(**payload)
    sys.stdout.write(json.dumps(result))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
