from __future__ import annotations

from .document_sync import needs_screen_document_capture as _needs_screen_document_capture


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


def screen_document_capability_gap(prompt: str, discovered: dict, selected_nodes: list[str], selected_targets: list[str]) -> dict | None:
    if not _needs_screen_document_capture(prompt):
        return None
    routes = discovered.get("routes") or []
    if has_screen_capture_route(routes, selected_nodes, selected_targets):
        return None
    related = [
        route.get("uri") for route in routes
        if any(token in str(route.get("uri") or "") for token in ("camera://", "ocr://", "fs://", "browser://", "screen://", "kvm://"))
    ][:20]
    return {
        "type": "CapabilityGap",
        "missing": "screen-capture",
        "message": "Brakuje route'u URI do zrzutow ekranu node'a. Dostepne sa camera/ocr/fs, ale nie screen/kvm/browser screenshot.",
        "selectedNodes": selected_nodes,
        "selectedTargets": selected_targets,
        "requiredAnyOf": [
            "screen://<node>/.../screenshot",
            "kvm://<node>/.../screenshot",
            "browser://<node>/page/command/screenshot",
        ],
        "availableRelatedRoutes": related,
    }
