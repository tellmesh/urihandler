from __future__ import annotations

import copy
from typing import Any


NODE_TYPE_PROFILES: tuple[dict[str, Any], ...] = (
    {
        "id": "server",
        "label": "Server",
        "description": "Headless machine controlled through shell or SSH.",
        "transport": "ssh+http",
        "runtime": "urirun-node",
        "integrationLevel": "system",
        "connectorCandidate": "shell, proc, fs, package",
        "serviceCandidate": "node daemon, optional service supervisor",
        "requiredFields": ["name", "host", "sshUser", "nodeUrl"],
        "optionalFields": ["sshPort", "nodePort", "tags"],
        "routesHint": ["shell://", "proc://", "fs://", "package://", "env://"],
    },
    {
        "id": "pc",
        "label": "PC",
        "description": "Desktop computer controlled through a local node plus optional KVM/screen routes.",
        "transport": "http+kvm",
        "runtime": "urirun-node",
        "integrationLevel": "desktop",
        "connectorCandidate": "screen, kvm, browser-control, fs",
        "serviceCandidate": "desktop helper or node daemon",
        "requiredFields": ["name", "nodeUrl"],
        "optionalFields": ["token", "display", "tags"],
        "routesHint": ["screen://", "kvm://", "browser://", "fs://", "env://"],
    },
    {
        "id": "rdp",
        "label": "RDP",
        "description": "Remote desktop surface where urirun controls the session through a node inside the desktop.",
        "transport": "rdp+http+kvm",
        "runtime": "remote-desktop-node",
        "integrationLevel": "desktop",
        "connectorCandidate": "screen, kvm, fs",
        "serviceCandidate": "RDP session helper",
        "requiredFields": ["name", "rdpHost", "rdpPort", "nodeUrl"],
        "optionalFields": ["rdpUser", "token", "tags"],
        "routesHint": ["screen://", "kvm://", "fs://", "env://"],
    },
    {
        "id": "smartphone",
        "label": "Smartphone",
        "description": "Phone that starts as a webpage node and can become a fuller mobile node through APK or Termux.",
        "transport": "https+js",
        "runtime": "mobile-web-or-node",
        "integrationLevel": "mobile",
        "connectorCandidate": "camera, sensor, file bridge",
        "serviceCandidate": "urirun-service-android-node",
        "requiredFields": ["setupUrl"],
        "optionalFields": ["nodeUrl", "apk", "termux", "tags"],
        "routesHint": ["camera://", "sensor://", "webnode://", "env://"],
    },
    {
        "id": "browser-debug",
        "label": "Browser debug mode",
        "description": "Whole browser controlled through DevTools/CDP debug mode.",
        "transport": "cdp",
        "runtime": "browser-cdp",
        "integrationLevel": "app",
        "connectorCandidate": "webnode, browser-control",
        "serviceCandidate": "optional browser launcher",
        "requiredFields": ["name", "debugUrl"],
        "optionalFields": ["profile", "tags"],
        "routesHint": ["webnode://browser", "webnode://page", "browser://"],
    },
    {
        "id": "browser-chrome-plugin",
        "label": "Chrome plugin",
        "description": "Chrome extension that controls the active tab and forwards URI calls to a urirun node.",
        "transport": "extension+http",
        "runtime": "chrome-extension",
        "integrationLevel": "browser-plugin",
        "connectorCandidate": "chrome-plugin, js-urirun-com",
        "serviceCandidate": "optional extension relay",
        "requiredFields": ["name", "extensionId", "nodeUrl"],
        "optionalFields": ["tabs", "permissions", "tags"],
        "routesHint": ["browser-plugin://chrome", "browser://", "webpage://"],
    },
    {
        "id": "browser-firefox-plugin",
        "label": "Firefox plugin",
        "description": "Firefox extension that controls the active tab and forwards URI calls to a urirun node.",
        "transport": "extension+http",
        "runtime": "firefox-extension",
        "integrationLevel": "browser-plugin",
        "connectorCandidate": "firefox-plugin, js-urirun-com",
        "serviceCandidate": "optional extension relay",
        "requiredFields": ["name", "extensionId", "nodeUrl"],
        "optionalFields": ["tabs", "permissions", "tags"],
        "routesHint": ["browser-plugin://firefox", "browser://", "webpage://"],
    },
    {
        "id": "webpage",
        "label": "Webpage node",
        "description": "Single page/tab controlled through page-scoped JavaScript and browser APIs.",
        "transport": "cdp+js",
        "runtime": "browser-page-js",
        "integrationLevel": "page",
        "connectorCandidate": "webnode, js-urirun-com",
        "serviceCandidate": "page bridge when the page must call back into urirun",
        "requiredFields": ["name", "debugUrl"],
        "optionalFields": ["targetId", "origin", "tags"],
        "routesHint": ["webnode://page", "webpage://", "browser-plugin://"],
    },
    {
        "id": "api",
        "label": "API node",
        "description": "External API endpoint or SaaS/local HTTP service controlled through configured URI interfaces.",
        "transport": "http+auth",
        "runtime": "external-api",
        "integrationLevel": "api",
        "connectorCandidate": "http-api, fetch, oauth, openapi",
        "serviceCandidate": "optional API proxy when auth/session refresh needs lifecycle",
        "requiredFields": ["name", "url"],
        "optionalFields": ["apis", "auth", "openapi", "tags"],
        "routesHint": ["api://", "http://", "fetch://"],
    },
    {
        "id": "device",
        "label": "Device node",
        "description": "Physical or embedded device with multiple APIs such as web UI, RTSP camera stream, SSH, SMB/NAS or GPIO control.",
        "transport": "multi-api",
        "runtime": "external-device",
        "integrationLevel": "device",
        "connectorCandidate": "camera, rtsp, ssh, smb, nas, gpio, mqtt",
        "serviceCandidate": "device bridge when protocols need polling or stream lifecycle",
        "requiredFields": ["name", "url"],
        "optionalFields": ["apis", "capabilities", "auth", "tags"],
        "routesHint": ["device://", "camera://", "media://", "ssh://", "fs://"],
    },
)

NODE_TYPE_ALIASES = {
    "desktop": "pc",
    "laptop": "pc",
    "notebook": "pc",
    "mobile": "smartphone",
    "phone": "smartphone",
    "android": "smartphone",
    "ios": "smartphone",
    "browser": "browser-debug",
    "debug": "browser-debug",
    "devtools": "browser-debug",
    "cdp": "browser-debug",
    "chrome": "browser-chrome-plugin",
    "chrome-plugin": "browser-chrome-plugin",
    "chromium-plugin": "browser-chrome-plugin",
    "firefox": "browser-firefox-plugin",
    "firefox-plugin": "browser-firefox-plugin",
    "web": "webpage",
    "webnode": "webpage",
    "page": "webpage",
    "tab": "webpage",
    "http-api": "api",
    "rest": "api",
    "openapi": "api",
    "saas": "api",
    "camera": "device",
    "cam": "device",
    "rpi": "device",
    "raspberry-pi": "device",
    "raspberry": "device",
    "nas": "device",
    "iot": "device",
    "ip-camera": "device",
}

DEFAULT_NODE_TYPE = "pc"


def node_type_profiles() -> list[dict[str, Any]]:
    return [copy.deepcopy(item) for item in NODE_TYPE_PROFILES]


def normalize_node_type(value: Any) -> str:
    raw = str(value or "").strip().casefold()
    if not raw:
        return ""
    raw = raw.replace("_", "-")
    ids = {item["id"] for item in NODE_TYPE_PROFILES}
    if raw in ids:
        return raw
    return NODE_TYPE_ALIASES.get(raw, "")


def node_type_profile(value: Any) -> dict[str, Any]:
    node_type = normalize_node_type(value) or DEFAULT_NODE_TYPE
    for profile in NODE_TYPE_PROFILES:
        if profile["id"] == node_type:
            return copy.deepcopy(profile)
    return copy.deepcopy(NODE_TYPE_PROFILES[1])


def node_type_from_tags(tags: Any) -> str:
    if not isinstance(tags, list):
        return ""
    for item in tags:
        raw = str(item or "").strip()
        lowered = raw.casefold()
        for prefix in ("kind:", "type:", "node-type:", "node_type:"):
            if lowered.startswith(prefix):
                return normalize_node_type(raw.split(":", 1)[1])
        node_type = normalize_node_type(raw)
        if node_type:
            return node_type
    return ""


def node_type_from_node(node: dict[str, Any]) -> str:
    for key in ("nodeType", "type", "kind"):
        node_type = normalize_node_type(node.get(key))
        if node_type:
            return node_type
    return node_type_from_tags(node.get("tags"))


def node_type_tags(node_type: Any, existing: Any = None) -> list[str]:
    normalized = normalize_node_type(node_type)
    tags = [str(item) for item in (existing if isinstance(existing, list) else []) if str(item or "").strip()]
    tags = [
        tag for tag in tags
        if not tag.casefold().startswith(("kind:", "type:", "node-type:", "node_type:"))
    ]
    if normalized:
        tags.append(f"kind:{normalized}")
    return tags


def annotate_node_type(node: dict[str, Any]) -> dict[str, Any]:
    out = dict(node)
    explicit_type = node_type_from_node(out)
    if not explicit_type:
        out.setdefault("kind", "")
        out.setdefault("nodeType", "")
        out.setdefault("type", "")
        out.setdefault("typeLabel", "")
        out.setdefault("integrationLevel", "")
        out.setdefault("transport", "")
        out.setdefault("runtime", "")
        out.setdefault("routesHint", [])
        return out
    profile = node_type_profile(explicit_type)
    node_type = str(profile["id"])
    out["nodeType"] = node_type
    out["type"] = node_type
    out["kind"] = node_type
    out["typeLabel"] = profile["label"]
    out["transport"] = out.get("transport") or profile["transport"]
    out["runtime"] = out.get("runtime") or profile["runtime"]
    out["integrationLevel"] = profile["integrationLevel"]
    out["routesHint"] = profile["routesHint"]
    return out


def annotate_node_types(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for idx, node in enumerate(nodes):
        nodes[idx] = annotate_node_type(node)
    return nodes
