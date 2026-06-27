from __future__ import annotations

from .document_sync import needs_screen_document_capture as _needs_screen_document_capture

_SCREEN_WORDS = ("zrzut", "screenshot", "screen capture", "zrzuty ekranu", "screenshoot")


def _needs_screen_capture_any(prompt: str) -> bool:
    """True when the prompt requests ANY screen capture — document output is optional."""
    text = prompt.casefold()
    return any(w in text for w in _SCREEN_WORDS)


def _connector_hint_for_nodes(selected_nodes: list[str]) -> dict:
    """Return a connectorHint that tells the user exactly how to enable screen capture."""
    if selected_nodes:
        node = selected_nodes[0]
        return {
            "scheme": "kvm",
            "package": "urirun-connector-kvm",
            "startCommand": f"urirun node serve --name {node}",
            "installCommand": f"urirun host ensure {node} kvm",
            "deployCommand": f"urirun host deploy {node}",
            "description": f"KVM/Wayland screen-capture connector for node '{node}'",
        }
    return {
        "scheme": "kvm",
        "package": "urirun-connector-kvm",
        "installCommand": "urirun host ensure <node> kvm",
        "description": "KVM/Wayland screen-capture connector",
    }


def selected_nodes_from_targets(selected_nodes: list[str], selected_targets: list[str]) -> list[str]:
    """Keep API callers and the browser form consistent: node targets imply selected nodes."""
    out: list[str] = []
    seen: set[str] = set()
    for node in selected_nodes:
        clean = str(node).strip()
        if clean and clean not in seen:
            out.append(clean)
            seen.add(clean)
    for target in selected_targets:
        clean = str(target).strip()
        if not clean.startswith("node:"):
            continue
        node = clean.split(":", 1)[1].strip()
        if node and node not in seen:
            out.append(node)
            seen.add(node)
    return out


def route_in_selected_targets(route: dict, selected_nodes: list[str], selected_targets: list[str]) -> bool:
    if not selected_nodes and not selected_targets:
        return True
    route_node = str(route.get("node") or "")
    uri = str(route.get("uri") or "")
    target_names = set(selected_nodes)
    for target in selected_targets:
        if target.startswith("node:"):
            target_names.add(target.split(":", 1)[1])
        elif target == "host":
            target_names.add("host")
    if route_node and route_node in target_names:
        return True
    if "host" in target_names and "://host/" in uri:
        return True
    return any(f"://{name}/" in uri for name in target_names if name)


def has_screen_capture_route(routes: list[dict], selected_nodes: list[str], selected_targets: list[str]) -> bool:
    for route in routes:
        if not route_in_selected_targets(route, selected_nodes, selected_targets):
            continue
        uri = str(route.get("uri") or "").casefold()
        if uri.startswith(("screen://", "kvm://")):
            return True
        if "screenshot" in uri:
            return True
        if uri.startswith("browser://") and "/capture" in uri:
            return True
    return False


def _offline_selected_nodes(discovered: dict, nodes: list[str]) -> list[str]:
    """Return names of selected nodes that are unreachable in the last discovery."""
    target_set = set(nodes)
    return [
        n["name"] for n in (discovered.get("nodes") or [])
        if not n.get("reachable") and n.get("name") in target_set
    ]


def screen_document_capability_gap(prompt: str, discovered: dict, selected_nodes: list[str], selected_targets: list[str]) -> dict | None:
    """Return a CapabilityGap when the prompt needs screen capture but no route is available.

    Triggers for ANY screenshot prompt (not just screenshot+document) so the caller can
    surface an actionable connectorHint instead of falling through to an LLM that logs a
    limitation message with no fix guidance."""
    if not _needs_screen_capture_any(prompt) and not _needs_screen_document_capture(prompt):
        return None
    routes = discovered.get("routes") or []
    if has_screen_capture_route(routes, selected_nodes, selected_targets):
        return None
    related = [
        route.get("uri") for route in routes
        if any(token in str(route.get("uri") or "") for token in ("camera://", "ocr://", "fs://", "browser://", "screen://", "kvm://"))
    ][:20]
    nodes = selected_nodes or [t.removeprefix("node:") for t in selected_targets if t.startswith("node:")]
    offline = _offline_selected_nodes(discovered, nodes)
    if offline:
        node = offline[0]
        message = (
            f"Node '{node}' jest offline. Uruchom: urirun node serve --name {node} "
            f"(a następnie: urirun host ensure {node} kvm)"
        )
        missing = "node-offline"
    elif nodes:
        node = nodes[0]
        message = (
            f"Node '{node}' nie ma trasy zrzutu ekranu (kvm://, screen://, browser://). "
            f"Zainstaluj connector: urirun host ensure {node} kvm"
        )
        missing = "screen-capture"
    else:
        message = "Brakuje trasy URI do zrzutow ekranu. Zainstaluj connector kvm: urirun host ensure <node> kvm"
        missing = "screen-capture"
    return {
        "type": "CapabilityGap",
        "missing": missing,
        "offline": offline,
        "message": message,
        "selectedNodes": selected_nodes,
        "selectedTargets": selected_targets,
        "requiredAnyOf": [
            "screen://<node>/.../screenshot",
            "kvm://<node>/.../screenshot",
            "browser://<node>/page/command/screenshot",
        ],
        "availableRelatedRoutes": related,
        "connectorHint": _connector_hint_for_nodes(nodes),
    }
