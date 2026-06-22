# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# Built-in node self-management routes, addressable as URIs (the urirun way) instead of
# a shell script. A node served with `--manage` exposes, admin-gated:
#
#   node://<name>/package/command/install   {spec, upgrade?}   pip-install into the node's OWN venv
#   node://<name>/package/query/list        {match?}           list installed packages
#   node://<name>/runtime/query/info        {}                 interpreter / venv / platform
#   node://<name>/connector/command/install {id}               install a urirun-connector-<id>
#
# Handlers run in-process and shell out to THIS node's interpreter (sys.executable), so a
# host can provision a remote node — add the office connectors, cryptography, anything —
# over the mesh, no SSH. These are powerful (arbitrary install), so the node server gates
# every node:// route behind the admin token / enrolled key.

from __future__ import annotations

import subprocess
import sys
from typing import Any


def _pip(args: list[str], timeout: float = 900) -> dict:
    cmd = [sys.executable, "-m", "pip", *args]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "cmd": cmd}
    return {"ok": r.returncode == 0, "returncode": r.returncode,
            "stdout": r.stdout[-4000:], "stderr": r.stderr[-2000:]}


def package_install(**payload: Any) -> dict:
    """pip-install one or more specs into the node's venv. spec may be a PyPI name,
    a version spec, or a `git+https://…` / local path — anything pip accepts."""
    spec = payload.get("spec") or payload.get("package")
    if not spec:
        return {"ok": False, "error": "spec required (PyPI name, version spec, or git+url)"}
    specs = spec if isinstance(spec, list) else [str(spec)]
    args = ["install"]
    if payload.get("upgrade", True):
        args.append("--upgrade")
    args += specs
    res = _pip(args)
    res["installed"] = specs if res.get("ok") else []
    return res


def connector_install(**payload: Any) -> dict:
    """Install a urirun connector by id: tries `urirun-connector-<id>` then its GitHub repo."""
    cid = payload.get("id") or payload.get("connector")
    if not cid:
        return {"ok": False, "error": "id required"}
    res = _pip(["install", "--upgrade", f"urirun-connector-{cid}"])
    if not res.get("ok"):
        res = _pip(["install", "--upgrade", f"git+https://github.com/if-uri/urirun-connector-{cid}.git"])
    res["connector"] = cid
    return res


def package_list(**payload: Any) -> dict:
    res = _pip(["list", "--format=freeze"], timeout=120)
    if not res.get("ok"):
        return res
    lines = (res.get("stdout") or "").splitlines()
    match = str(payload.get("match") or "").lower()
    if match:
        lines = [ln for ln in lines if match in ln.lower()]
    return {"ok": True, "packages": lines}


def runtime_info(**payload: Any) -> dict:
    import platform

    info = {"ok": True, "python": sys.executable, "pythonVersion": platform.python_version(),
            "prefix": sys.prefix, "platform": platform.platform()}
    try:
        from importlib.metadata import version
        info["urirun"] = version("urirun")
    except Exception:
        pass
    return info


_ROUTES = [
    ("package/command/install", "command", "package_install",
     {"spec": {"type": ["string", "array"]}, "upgrade": {"type": "boolean"}}),
    ("connector/command/install", "command", "connector_install", {"id": {"type": "string"}}),
    ("package/query/list", "query", "package_list", {"match": {"type": "string"}}),
    ("runtime/query/info", "query", "runtime_info", {}),
]


def bindings(name: str) -> dict:
    """v2 bindings for this node's management surface, namespaced under its name."""
    out: dict[str, dict] = {}
    for path, kind, export, props in _ROUTES:
        out[f"node://{name}/{path}"] = {
            "kind": kind, "adapter": "local-function",
            "ref": f"urirun.node.manage:{export}",
            "python": {"type": "python", "module": "urirun.node.manage", "export": export},
            "inputSchema": {"type": "object", "additionalProperties": True, "properties": props},
            "policy": {"allowExecute": True},
            "meta": {"label": f"node management · {path}"},
        }
    return {"version": "urirun.bindings.v2", "bindings": out}
