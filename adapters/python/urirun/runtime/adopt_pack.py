# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.

"""Least-invasive URI adoption for capability packs.

Many packages already describe their URI surface in a manifest (tellmesh-style
``manifest.yaml`` with ``scheme`` + ``uri_patterns`` + ``handlers``). This module
maps that manifest 1:1 onto ``urirun.bindings.v2`` so the package becomes a URI
connector with no code change — point urirun at the manifest:

```bash
python -m urirun.runtime.adopt_pack ../tellmesh/urikvm/urikvm/manifest.yaml --out kvm.bindings.v2.json
```

The mapping is structural:

    pattern  -> binding uri
    kind     -> meta.uriKind (query/command)
    operation + handlers.python[operation] (python://mod:func) -> local-function ref
    side_effects / approval -> policy

Unhydrated ``local-function`` refs run in simulated mode, so the registry
validates and dispatches before the pack's own dependencies are installed.
"""

from __future__ import annotations

import json
from pathlib import Path


def _load(path: str | Path) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    if str(path).endswith((".yaml", ".yml")):
        import yaml  # optional dependency; only needed for YAML manifests

        return yaml.safe_load(text)
    return json.loads(text)


def _policy(pattern: dict) -> dict:
    policy: dict = {}
    if pattern.get("approval") == "required":
        policy["approval"] = "required"
    if pattern.get("side_effects"):
        policy["sideEffects"] = True
    return policy


def manifest_bindings(manifest: dict) -> list[dict]:
    """Map a manifest dict (scheme/uri_patterns/handlers) to v2 binding dicts."""
    scheme = manifest.get("scheme")
    pack = manifest.get("id")
    handlers = (manifest.get("handlers") or {}).get("python") or {}
    bindings: list[dict] = []
    for pat in manifest.get("uri_patterns") or []:
        operation = pat.get("operation")
        raw = handlers.get(operation, "")  # e.g. python://urikvm.handlers:monitor_list
        ref = raw.split("://", 1)[-1] if raw else (operation or "")
        binding = {
            "uri": pat["pattern"],
            "kind": "function",
            "adapter": "local-function",
            "ref": ref,
            "meta": {
                "label": operation or pat["pattern"],
                "operation": operation,
                "uriKind": pat.get("kind"),
                "scheme": scheme,
                "standard": f"tellmesh pack '{pack}' manifest.yaml",
            },
            "source": {"type": "pack-manifest", "pack": pack, "scheme": scheme, "handler": raw},
        }
        policy = _policy(pat)
        if policy:
            binding["policy"] = policy
        bindings.append(binding)
    return bindings


def adopt_document(path: str | Path) -> dict:
    from urirun import v2

    bindings = manifest_bindings(_load(path))
    expanded = {b["uri"]: v2.expand_binding(b["uri"], b) for b in bindings}
    return {"version": v2.VERSION, "bindings": expanded}


# --------------------------------------------------------------------------- #
# Discovery: turn an *installed package name* or a *project dir* into bindings
# --------------------------------------------------------------------------- #
def _tool_urirun(pyproject: Path) -> dict:
    """Read the [tool.urirun] table from a pyproject.toml (source adoption)."""
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover - py<3.11
        import tomli as tomllib  # type: ignore
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    return (data.get("tool") or {}).get("urirun") or {}


def installed_manifest_path(package: str) -> Path | None:
    """Locate an installed package's manifest: a ``urirun.packs`` entry point
    first, then the conventional ``<importable>/manifest.yaml`` package data."""
    from importlib import metadata, resources

    try:
        eps = metadata.entry_points(group="urirun.packs")
    except TypeError:  # pragma: no cover - older API
        eps = metadata.entry_points().get("urirun.packs", [])  # type: ignore
    for ep in eps:
        if ep.name == package:
            module, _, rel = ep.value.partition(":")
            try:
                base = resources.files(module)
                target = base / (rel or "manifest.yaml")
                if target.is_file():
                    return Path(str(target))
            except (ModuleNotFoundError, FileNotFoundError):
                pass
    for module in (package, package.replace("-", "_")):
        try:
            target = resources.files(module) / "manifest.yaml"
            if target.is_file():
                return Path(str(target))
        except (ModuleNotFoundError, FileNotFoundError, TypeError):
            continue
    return None


def adopt(target: str | Path) -> dict:
    """Adopt a manifest file, a project dir ([tool.urirun] or manifest.yaml),
    or an installed package name — whichever ``target`` resolves to."""
    path = Path(target)
    if path.is_file():
        return adopt_document(path)
    if path.is_dir():
        pyproject = path / "pyproject.toml"
        if pyproject.exists():
            cfg = _tool_urirun(pyproject)
            if cfg.get("manifest"):
                return adopt_document(path / cfg["manifest"])
        for candidate in path.glob("*/manifest.yaml"):
            return adopt_document(candidate)
        raise FileNotFoundError(f"no [tool.urirun].manifest or */manifest.yaml under {path}")
    manifest = installed_manifest_path(str(target))
    if manifest is None:
        raise FileNotFoundError(f"no manifest for installed package {target!r} (urirun.packs entry point or <pkg>/manifest.yaml)")
    return adopt_document(manifest)


def main(argv: list[str] | None = None) -> int:
    import argparse

    from urirun import _registry as reglib

    parser = argparse.ArgumentParser(prog="urirun-adopt-pack")
    parser.add_argument("target", help="manifest file, project dir ([tool.urirun]), or installed package name")
    parser.add_argument("--out", default="-", help="bindings.v2 output (default: stdout)")
    args = parser.parse_args(argv)

    document = adopt(args.target)
    if args.out == "-":
        print(json.dumps(document, indent=2))
    else:
        reglib.write_json(args.out, document)
        print(f"{len(document['bindings'])} binding(s) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
