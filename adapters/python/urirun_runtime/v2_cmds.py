"""CLI command implementations for urirun v2.

Extracted from v2.py to keep the core binding/registry module under 1800 lines.
Imported lazily from v2.main() to avoid circular imports.
"""

from __future__ import annotations

import importlib
import json
import re
import sys
from pathlib import Path

from urirun_runtime import _registry as reglib
from urirun_runtime import _runtime as runtime
from urirun_runtime import errors as uri_errors

# v2 imports at module level — safe because v2_cmds is only imported lazily
# from inside v2.main(), so v2.py is fully loaded before this runs.
import urirun_runtime.v2 as _v2

ENTRY_POINT_GROUP = _v2.ENTRY_POINT_GROUP
_CLI_BRIDGE = _v2._CLI_BRIDGE
_load_json_arg = _v2._load_json_arg
_load_many = _v2._load_many
build_binding_document = _v2.build_binding_document
command_binding_from_cli = _v2.command_binding_from_cli
compile_registry = _v2.compile_registry
connector_collisions = _v2.connector_collisions
connector_health = _v2.connector_health
decorated_bindings = _v2.decorated_bindings
entry_point_binding_document = _v2.entry_point_binding_document
entry_point_bindings = _v2.entry_point_bindings
expand_bindings = _v2.expand_bindings
list_routes = _v2.list_routes
load_registry_arg = _v2.load_registry_arg
pypi_binding = _v2.pypi_binding
run = _v2.run
scan_artifacts = _v2.scan_artifacts
validate_binding_document = _v2.validate_binding_document
write_or_emit_binding = _v2.write_or_emit_binding


# _is_pipx_env and _package_version are called through _v2 so that monkeypatching
# v2._is_pipx_env in tests propagates to v2_cmds callers.
def _is_pipx_env() -> bool:
    return _v2._is_pipx_env()


def _package_version() -> str:
    return _v2._package_version()


def _cmd_scan(args, parser) -> int:
    bindings = scan_artifacts(args.path)
    if args.entry_points:
        bindings.extend(entry_point_bindings(group=args.entry_point_group))
    doc = build_binding_document(bindings)
    reglib._emit_json(doc, args.out)
    if args.registry_out:
        reglib.write_json(args.registry_out, compile_registry(doc))
    return 0


def _cmd_compile(args, parser) -> int:
    if not args.sources and not args.entry_points:
        parser.error("compile requires at least one source or --entry-points")
    doc = build_binding_document(
        _load_many(args.sources, include_entry_points=args.entry_points, entry_point_group=args.entry_point_group),
        generated_at=args.generated_at,
    )
    reglib._emit_json(compile_registry(doc, generated_at=args.generated_at, on_conflict=args.on_conflict), args.out)
    return 0


def _cmd_discover(args, parser) -> int:
    doc = entry_point_binding_document(group=args.entry_point_group, generated_at=args.generated_at)
    reglib._emit_json(doc, args.out)
    if args.registry_out:
        reglib.write_json(args.registry_out, compile_registry(doc, generated_at=args.generated_at, on_conflict=args.on_conflict))
    return 0


def _cmd_adopt_pack(args, parser) -> int:
    from urirun_runtime import adopt_pack as _adopt_pack

    doc = _adopt_pack.adopt(args.target)
    reglib._emit_json(doc, args.out)
    if args.registry_out:
        reglib.write_json(args.registry_out, compile_registry(doc, generated_at=args.generated_at, on_conflict=args.on_conflict))
    return 0


def _cmd_tree(args, parser) -> int:
    from urirun_runtime import tree as _tree

    document = _tree.build(reglib.load_json(args.source))
    if args.format == "json":
        reglib._emit_json(document, "-")
        return 0
    try:
        import yaml
    except ModuleNotFoundError:
        sys.stderr.write("[urirun] PyYAML not installed — emitting JSON; `pip install pyyaml` for --format yaml.\n")
        reglib._emit_json(document, "-")
        return 0
    sys.stdout.write(yaml.safe_dump(document, sort_keys=False, allow_unicode=True, default_flow_style=False))
    return 0


def _cmd_validate(args, parser) -> int:
    if args.source == "-":
        doc = _load_json_arg("-")
    else:
        path = Path(args.source)
        doc = build_binding_document(scan_artifacts(path)) if path.is_dir() else reglib.load_json(path)
    result = validate_binding_document(doc)
    if args.json:
        reglib._emit_json(result, "-")
    else:
        print("OK" if result["ok"] else "FAILED")
        for error in result["errors"]:
            print(f"{error.get('uri')}: {error['error']}")
    return 0 if result["ok"] else 1


def _cmd_add_command(args, parser) -> int:
    try:
        binding = command_binding_from_cli(args.uri, argv=args.argv, shell=args.shell, params=args.param, label=args.label)
    except ValueError as exc:
        parser.error(str(exc))
    write_or_emit_binding(args.out, binding)
    return 0


def _cmd_add_pypi(args, parser) -> int:
    write_or_emit_binding(args.out, pypi_binding(args.name, version=args.version, uri=args.uri))
    return 0


def _cmd_add_openapi(args, parser) -> int:
    fn = _CLI_BRIDGE.get("add_openapi")
    if fn is None:
        reglib._emit_json({"ok": False, "error": "openapi connector not available (import urirun.connectors.openapi_import to activate)"}, "-")
        return 1
    return fn(args)


def _cmd_gen(args, parser) -> int:
    from urirun_runtime import codegen

    return codegen.gen_command(args)


def _cmd_doctor(args, parser) -> int:
    """Report the resolved urirun binary, version and interpreter, plus connector
    health — the fastest way to diagnose a version split (stale binary on PATH)."""
    try:
        connectors = connector_health(ENTRY_POINT_GROUP)
    except Exception as exc:  # noqa: BLE001 - never let a broken connector crash diagnostics
        connectors = []
        connector_error = f"{type(exc).__name__}: {exc}"
    else:
        connector_error = None
    unhealthy = [c for c in connectors if not c.get("ok")]
    info = {
        "ok": not unhealthy and connector_error is None,
        "version": _package_version(),
        "binary": sys.argv[0],
        "interpreter": sys.executable,
        "managedBy": "pipx" if _is_pipx_env() else "pip",
        "entryPointGroup": ENTRY_POINT_GROUP,
        "connectors": connectors,
        "connectorError": connector_error,
    }
    if getattr(args, "json", False):
        reglib._emit_json(info, "-")
        return 0 if info["ok"] else 1
    print(f"urirun {info['version']}")
    print(f"  binary       {info['binary']}")
    print(f"  interpreter  {info['interpreter']}")
    print(f"  managed by   {info['managedBy']}")
    if connector_error:
        print(f"  connectors   ERROR: {connector_error}")
    else:
        print(f"  connectors   {len(connectors)} installed, {len(unhealthy)} unhealthy")
        for c in unhealthy:
            print(f"    [FAIL] {c.get('name', '?')}: {c.get('error', '')}")
    return 0 if info["ok"] else 1


def _pip_command(pip_args: list[str]) -> tuple[list[str], str]:
    """Build a pip invocation, honoring pipx-managed installs."""
    if _is_pipx_env():
        return (["pipx", "runpip", "urirun", *pip_args], "pipx")
    return ([sys.executable, "-m", "pip", *pip_args], "pip")


def _resolve_pip_targets(ids, source, catalog_url, *, org="if-uri", ref=None):
    """Map connector ids to ``(targets, editable, detail)`` for the chosen source."""
    if source == "pypi":
        return list(ids), False, {"fromCatalog": [], "direct": list(ids)}
    if source == "local":
        return list(ids), True, {"fromCatalog": [], "direct": list(ids)}
    if source == "github":
        suffix = f"@{ref}" if ref else ""
        targets = [f"{i} @ git+https://github.com/{org}/{i}.git{suffix}" for i in ids]
        return targets, False, {"fromCatalog": [], "direct": targets}
    fn = _CLI_BRIDGE.get("catalog_resolve_install")
    if fn is not None:
        try:
            specs, unknown = fn(catalog_url, ids)
        except Exception:  # noqa: BLE001 - catalog offline / unreachable -> treat all as raw packages
            specs, unknown = [], list(ids)
        return list(specs) + unknown, False, {"fromCatalog": specs, "direct": unknown}
    return list(ids), False, {"fromCatalog": [], "direct": list(ids)}


def _pip_install_args(targets, *, upgrade, editable):
    pip_args = ["install"]
    if upgrade:
        pip_args.append("--upgrade")
    if editable:
        for target in targets:
            pip_args += ["-e", target]
    else:
        pip_args += list(targets)
    return pip_args


def _cmd_install(args, parser) -> int:
    """Install (or, with ``--upgrade``, update) a connector."""
    import subprocess

    upgrade = getattr(args, "upgrade", False)
    source = getattr(args, "source_from", "catalog")
    targets, editable, detail = _resolve_pip_targets(
        args.ids, source, args.catalog,
        org=getattr(args, "org", "if-uri"), ref=getattr(args, "ref", None))
    cmd, manager = _pip_command(_pip_install_args(targets, upgrade=upgrade, editable=editable))
    if args.dry_run:
        reglib._emit_json({"ok": True, "dryRun": True, "source": source, "upgrade": upgrade,
                           "manager": manager, "catalog": args.catalog, **detail, "pip": cmd}, "-")
        return 0
    print(json.dumps({"installing": targets, "via": manager, "upgrade": upgrade}), flush=True)
    return subprocess.run(cmd).returncode


def _upgrade_check_report(args) -> int:
    connectors = connector_health(ENTRY_POINT_GROUP)
    reglib._emit_json({"ok": True, "version": _package_version(),
                       "installed": [{"name": c.get("name"), "bindings": c.get("bindingCount"),
                                      "ok": c.get("ok")} for c in connectors]}, "-")
    return 0


def _upgrade_core(args, source: str, org: str, ref) -> int:
    """Upgrade the urirun package itself (no connector ids given)."""
    import subprocess
    if _is_pipx_env():
        cmd, manager = ["pipx", "upgrade", "urirun"], "pipx"
    else:
        if source == "github":
            suffix = f"@{ref}" if ref else ""
            target = f"urirun @ git+https://github.com/{org}/urirun.git{suffix}#subdirectory=adapters/python"
        else:
            target = "urirun"
        cmd, manager = _pip_command(["install", "--upgrade", target])
    if args.dry_run:
        reglib._emit_json({"ok": True, "dryRun": True, "target": "urirun", "manager": manager, "cmd": cmd}, "-")
        return 0
    print(json.dumps({"upgrading": "urirun", "via": manager}), flush=True)
    return subprocess.run(cmd).returncode


def _upgrade_connector_ids(args) -> list[str] | None:
    """Resolve connector ids to upgrade; emits result and returns None when nothing to do."""
    if not args.all:
        return list(args.ids)
    ids = [c.get("name") for c in connector_health(ENTRY_POINT_GROUP) if c.get("name")]
    if not ids:
        reglib._emit_json({"ok": True, "upgraded": [], "note": "no connectors installed"}, "-")
        return None
    return ids


def _cmd_upgrade(args, parser) -> int:
    """Upgrade urirun itself (no ids) or installed connectors (``install --upgrade``)."""
    import subprocess

    source = getattr(args, "source_from", "catalog")
    org = getattr(args, "org", "if-uri")
    ref = getattr(args, "ref", None)

    if getattr(args, "check", False):
        return _upgrade_check_report(args)

    if not args.ids and not args.all:
        return _upgrade_core(args, source, org, ref)

    ids = _upgrade_connector_ids(args)
    if ids is None:
        return 0
    targets, editable, detail = _resolve_pip_targets(ids, source, args.catalog, org=org, ref=ref)
    cmd, manager = _pip_command(_pip_install_args(targets, upgrade=True, editable=editable))
    if args.dry_run:
        reglib._emit_json({"ok": True, "dryRun": True, "source": source, "manager": manager, **detail, "cmd": cmd}, "-")
        return 0
    print(json.dumps({"upgrading": targets, "via": manager}), flush=True)
    return subprocess.run(cmd).returncode


def _pipspec_version(pipspec: str | None) -> str | None:
    """Best-effort version from a catalog pipSpec — a git tag or ``==`` pin."""
    if not pipspec:
        return None
    match = re.search(r"\.git@([^#\s]+)", pipspec)
    if match:
        return match.group(1).lstrip("v")
    match = re.search(r"==\s*([^\s,;]+)", pipspec)
    if match:
        return match.group(1)
    return None


def _outdated_rows(catalog, catalog_find=None) -> list[dict]:
    """One row per installed connector: id/package/installed/available/status."""
    seen: set[str] = set()
    rows = []
    for entry_point in _v2._select_entry_points(ENTRY_POINT_GROUP):
        dist = getattr(entry_point, "dist", None)
        package = getattr(dist, "name", None)
        key = package or entry_point.name
        if key in seen:
            continue
        seen.add(key)
        installed = getattr(dist, "version", None)
        connector = (catalog_find(catalog, entry_point.name) if catalog_find else None) or {}
        install = connector.get("install") if isinstance(connector.get("install"), dict) else {}
        available = _pipspec_version(install.get("pipSpec"))
        if installed and available:
            status = "up-to-date" if installed == available else "outdated"
        else:
            status = "unknown"
        rows.append({"id": entry_point.name, "package": package, "installed": installed,
                     "available": available, "status": status})
    rows.sort(key=lambda row: row["id"])
    return rows


def _cmd_outdated(args, parser) -> int:
    """Report installed connectors whose catalog version differs from what is installed."""
    fn = _CLI_BRIDGE.get("catalog_fetch")
    catalog = {}
    if fn is not None:
        try:
            catalog = fn(args.catalog)
        except Exception:  # noqa: BLE001 - offline/unreachable -> no available versions
            pass
    rows = _outdated_rows(catalog, _CLI_BRIDGE.get("catalog_find"))
    outdated = [r for r in rows if r["status"] == "outdated"]
    if getattr(args, "json", False):
        reglib._emit_json({"ok": True, "outdated": len(outdated), "connectors": rows}, "-")
        return 0
    marks = {"outdated": "↑", "up-to-date": " ", "unknown": "?"}
    for row in rows:
        print(f"  {marks[row['status']]} {row['id']:24s} {str(row['installed'] or '-'):12s} -> {row['available'] or '?'}")
    print(f"\n{len(outdated)} outdated, {len(rows)} installed")
    return 0


def _cmd_agent(args, parser) -> int:
    from urirun_runtime import agent as agent_mod

    return agent_mod.agent_command(args)


_CONNECTOR_SUBCOMMANDS = {
    "lint": ("urirun.connectors.connector_lint", "lint_command"),
    "sync-manifest": ("urirun.connectors.connector_lint", "sync_manifest_command"),
    "verify": ("urirun.connectors.connector_lint", "verify_command"),
    "new": ("urirun.connector_scaffold", "new_command"),
    "smoke": ("urirun.connector_smoke", "smoke_command"),
    "from-spec": ("urirun.connectors.declarative", "from_spec_command"),
    "index": ("urirun.connectors.resolver", "index_command"),
    "resolve": ("urirun.connectors.resolver", "resolve_command"),
}


def _print_doctor_report(report, unhealthy, dup, shared) -> None:
    for r in report:
        if not r["ok"]:
            print(f"  [FAIL] {r['name']:22s} {r.get('error', '')}")
        elif r.get("scriptIssues"):
            issue = r["scriptIssues"][0]
            print(f"  [WARN] {r['name']:22s} {r['bindingCount']} bindings · console-script {issue['name']!r} broken: {issue['error']}")
        else:
            print(f"  [ok  ] {r['name']:22s} {r['bindingCount']} bindings")
    print(f"\n{len(report) - len(unhealthy)}/{len(report)} connectors healthy")
    for c in dup:
        print(f"  [DUPLICATE-URI] {c['uri']} claimed by {', '.join(c['connectors'])} — registry shadows all but one")
    for c in shared:
        owners = ", ".join(f"{o['connector']}({o['uri']})" for o in c["owners"])
        print(f"  [shared-path]   {c['route']} — distinct URIs resolve via index; collide only on tree-fallback: {owners}")


def _cmd_connectors_doctor(args, parser) -> int:
    group = getattr(args, "entry_point_group", ENTRY_POINT_GROUP)
    report = connector_health(group)
    collisions = connector_collisions(group)
    dup = [c for c in collisions if c["kind"] == "duplicate-uri"]
    shared = [c for c in collisions if c["kind"] == "shared-path"]
    unhealthy = [r for r in report if not r["ok"] or r.get("scriptIssues")]
    failing = bool(unhealthy or dup)
    if getattr(args, "json", False):
        reglib._emit_json({"ok": not failing, "total": len(report), "unhealthy": len(unhealthy),
                           "connectors": report, "collisions": collisions}, "-")
    else:
        _print_doctor_report(report, unhealthy, dup, shared)
    return 1 if failing else 0


def _cmd_connectors(args, parser) -> int:
    sub = getattr(args, "connectors_command", None)
    if sub == "doctor":
        return _cmd_connectors_doctor(args, parser)
    target = _CONNECTOR_SUBCOMMANDS.get(sub)
    if target is not None:
        module, func = target
        return getattr(importlib.import_module(module), func)(args)
    fn = _CLI_BRIDGE.get("connectors_command")
    if fn is not None:
        return fn(args)
    reglib._emit_json({"ok": False, "error": f"unknown connectors sub-command: {sub!r}"}, "-")
    return 1


def _cmd_errors(args, parser) -> int:
    return uri_errors.main(args.errors_args)


def _cmd_compat(args, parser) -> int:
    from urirun_runtime import compat

    return compat.main(args.compat_args)


def _ensure_cli_bridge(name: str):
    """Return the CLI bridge fn for ``name``; lazy-import node layer if absent."""
    fn = _CLI_BRIDGE.get(name)
    if fn is None:
        try:
            import urirun.node.mesh  # noqa: F401,PLC0415 - registers host/node_command into _CLI_BRIDGE
        except Exception:  # noqa: BLE001 - node layer absent (kernel-only install): stay graceful
            pass
        fn = _CLI_BRIDGE.get(name)
    return fn


def _cmd_host(args, parser) -> int:
    fn = _ensure_cli_bridge("host_command")
    if fn is None:
        reglib._emit_json({"ok": False, "error": "mesh not available"}, "-")
        return 1
    return fn(args)


def _cmd_node(args, parser) -> int:
    fn = _ensure_cli_bridge("node_command")
    if fn is None:
        reglib._emit_json({"ok": False, "error": "mesh not available"}, "-")
        return 1
    return fn(args)


def _builtin_binding_items(target: str = "local") -> list[dict]:
    """Always-mounted introspection/observability routes."""
    from urirun_runtime.errors import bindings as _error_bindings  # noqa: PLC0415
    from urirun_runtime.introspect import registry_introspect_bindings

    items: list[dict] = []
    for document in (_error_bindings(target), registry_introspect_bindings(target)):
        items.extend(expand_bindings(document)["bindings"])
    return items


def _registry_from_module(path: str):
    """Import a single Python file and compile a runnable registry from its routes."""
    import importlib.util

    file = Path(path)
    if not file.exists():
        raise SystemExit(f"--module file not found: {path}")
    canonical = importlib.import_module("urirun.runtime.v2")
    before = set(canonical.decorated_bindings()["bindings"])
    spec = importlib.util.spec_from_file_location("_urirun_run_module", str(file.resolve()))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    bindings = canonical.decorated_bindings()["bindings"]
    added = {uri: binding for uri, binding in bindings.items() if uri not in before}
    if not added:
        raise SystemExit(f"no urirun routes in {path} (decorate with @connector.handler / @command)")
    return canonical.compile_registry({"version": canonical.VERSION, "bindings": added})


def _registry_file_from_args(args) -> str | None:
    """Return the registry file path from args if it exists on disk, else None."""
    if getattr(args, "registry", None) and Path(args.registry).exists():
        return args.registry
    return None


def _discover_registry(args, group: str):
    """Build a registry via entry-point discovery for the ``list``/``run`` commands."""
    if getattr(args, "command", None) == "run" and getattr(args, "uri", None):
        from urirun_runtime import discovery
        return discovery.registry_for_uri(args.uri, group)
    registry_file = _registry_file_from_args(args)
    sources = [args.source] if args.source else ([registry_file] if registry_file else [])
    if not sources:
        from urirun_runtime import discovery
        return discovery.full_registry(group)
    bindings = _load_many(sources, include_entry_points=True, entry_point_group=group)
    bindings.extend(_builtin_binding_items())
    return compile_registry(build_binding_document(bindings))


def _resolve_list_registry(args):
    """Build the registry for list/run."""
    module_path = getattr(args, "module", None)
    if module_path:
        return _registry_from_module(module_path)
    registry_file = _registry_file_from_args(args)
    discover = getattr(args, "entry_points", False) or (not args.source and not registry_file)
    if discover:
        group = getattr(args, "entry_point_group", ENTRY_POINT_GROUP)
        return _discover_registry(args, group)
    return load_registry_arg(args.source or args.registry)


def _cmd_run_or_list(args, parser) -> int:
    registry = _resolve_list_registry(args)
    policy = runtime.build_policy(getattr(args, "policy", None), args.allow, args.deny, getattr(args, "secret_allow", None))

    if args.command == "run":
        result = run(args.uri, registry, json.loads(args.payload), mode="execute" if args.execute else "dry-run", policy=policy, confirm=args.confirm)
        reglib._emit_json(result, "-")
        return 0 if result.get("ok") else 1

    items = list_routes(registry, policy)
    if args.json:
        reglib._emit_json(items, "-")
    else:
        print(runtime.format_route_table(items, show_decision=policy is not None))
    return 0


def _cmd_version(args, parser) -> int:
    fn_status = _CLI_BRIDGE.get("version_status")
    fn_line = _CLI_BRIDGE.get("version_line")
    check = not getattr(args, "no_check", False)
    if fn_status is None:
        print(_package_version())
        return 0
    info = fn_status(check_latest=check)
    if getattr(args, "json", False):
        print(json.dumps(info))
    else:
        print(fn_line(check_latest=check) if fn_line else _package_version())
    return 0


_COMMANDS = {
    "version": _cmd_version,
    "scan": _cmd_scan,
    "compile": _cmd_compile,
    "discover": _cmd_discover,
    "adopt-pack": _cmd_adopt_pack,
    "tree": _cmd_tree,
    "validate": _cmd_validate,
    "add-command": _cmd_add_command,
    "add-pypi": _cmd_add_pypi,
    "add-openapi": _cmd_add_openapi,
    "gen": _cmd_gen,
    "doctor": _cmd_doctor,
    "install": _cmd_install,
    "upgrade": _cmd_upgrade,
    "outdated": _cmd_outdated,
    "agent": _cmd_agent,
    "connectors": _cmd_connectors,
    "errors": _cmd_errors,
    "compat": _cmd_compat,
    "host": _cmd_host,
    "node": _cmd_node,
    "run": _cmd_run_or_list,
    "list": _cmd_run_or_list,
}


def _main_impl(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    executable = Path(sys.argv[0]).name
    prog = executable if executable in {"urirun", "urirun-v2"} else "urirun"
    from urirun_runtime.cli import _build_parser  # lazy: avoids v2<->cli import cycle
    parser = _build_parser(prog)
    args = parser.parse_args(argv)
    handler = _COMMANDS.get(args.command)
    if handler is None:
        return 1
    return handler(args, parser)
