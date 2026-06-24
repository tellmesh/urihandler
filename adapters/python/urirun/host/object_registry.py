from __future__ import annotations

from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse


PHONE_SCANNER_ROUTES = [
    "dashboard://host/phone-scanner/command/start",
    "dashboard://host/service/phone-scanner/command/restart",
    "service://host/phone-scanner/command/restart",
    "service://phone-scanner/command/restart",
    "scanner://page/camera/command/scan",
    "scanner://page/camera/command/best-pdf",
    "scanner://page/camera/command/autonomous",
]


def host_registry_routes(actions: list[dict]) -> list[dict]:
    routes = []
    for action in actions:
        if action.get("layer") not in {"host", "dashboard", "connector"}:
            continue
        routes.append({
            "uri": action.get("uri"),
            "kind": action.get("kind"),
            "title": action.get("label"),
            "source": action.get("where"),
            "safe": not bool(action.get("sideEffects")),
            "layer": action.get("layer"),
        })
    return routes


def host_object(project: str, routes: list[dict]) -> dict:
    return {
        "id": "host",
        "kind": "host",
        "label": "urirun host",
        "status": "local",
        "reachable": True,
        "url": str(Path(project).expanduser().resolve()),
        "routes": routes,
    }


def phone_scanner_contact(scanner_state: dict) -> dict:
    return {
        "id": "service:phone-scanner",
        "kind": "service",
        "name": "phone-scanner",
        "label": "urirun service: photo scanner",
        "url": scanner_state["url"],
        "status": scanner_state["status"],
        "reachable": scanner_state["reachable"],
        "routes": list(PHONE_SCANNER_ROUTES),
    }


def service_contacts(
    *,
    scanner_port: int,
    scanner_state: dict,
    service_entries: list[dict],
    phone_scanner_url: Callable[[int], str],
    phone_scanner_status: Callable[[int], dict],
) -> list[dict]:
    phone_scanner = phone_scanner_contact(scanner_state)
    contacts = [phone_scanner]
    for entry in service_entries:
        service_id = str(entry.get("service_id") or "")
        parsed = urlparse(service_id)
        port = int(parsed.port or scanner_port)
        service_url = phone_scanner_url(port)
        name = "phone-scanner" if port == scanner_port else f"service-{port}"
        alive = bool(entry.get("alive"))
        external = (
            {"status": "stopped", "reachable": False, "url": service_url}
            if alive
            else phone_scanner_status(port)
        )
        item = {
            **phone_scanner,
            "id": f"service:{name}",
            "name": name,
            "label": f"urirun service: {name}",
            "url": service_url if alive else external["url"],
            "bindUrl": service_id,
            "status": "running" if alive else external["status"],
            "reachable": alive or bool(external["reachable"]),
            "serverName": str(entry.get("server_name") or ""),
        }
        contacts = [contact for contact in contacts if contact.get("id") != item["id"]]
        contacts.append(item)
    return contacts


def annotate_node_tokens(nodes: list[dict], node_token_for: Callable[[str], Any]) -> list[dict]:
    for node in nodes:
        node_name = node.get("name")
        if not node_name:
            continue
        try:
            node["hasToken"] = bool(node_token_for(str(node_name)))
        except Exception:  # noqa: BLE001
            node["hasToken"] = False
    return nodes
