from urirun.host import node_types
from urirun.node import transport


def test_normalize_node_type_aliases() -> None:
    assert node_types.normalize_node_type("webnode") == "webpage"
    assert node_types.normalize_node_type("web") == "webpage"
    assert node_types.normalize_node_type("browser") == "browser-debug"
    assert node_types.normalize_node_type("chrome") == "browser-chrome-plugin"
    assert node_types.normalize_node_type("firefox") == "browser-firefox-plugin"
    assert node_types.normalize_node_type("laptop") == "pc"
    assert node_types.normalize_node_type("android") == "smartphone"
    assert node_types.normalize_node_type("openapi") == "api"
    assert node_types.normalize_node_type("rpi") == "device"


def test_annotate_node_type_from_tags() -> None:
    item = node_types.annotate_node_type({
        "name": "phone",
        "url": "https://phone.local",
        "tags": ["lab", "kind:smartphone"],
    })

    assert item["kind"] == "smartphone"
    assert item["nodeType"] == "smartphone"
    assert item["runtime"] == "mobile-web-or-node"
    assert item["integrationLevel"] == "mobile"


def test_annotate_node_type_does_not_guess_unknown_nodes() -> None:
    item = node_types.annotate_node_type({"name": "plain", "url": "http://plain.local:8765"})

    assert item["kind"] == ""
    assert item["nodeType"] == ""
    assert item["transport"] == ""


def test_node_type_tags_replaces_existing_type_tags() -> None:
    assert node_types.node_type_tags("browser", ["office", "kind:pc", "type:server"]) == [
        "office",
        "kind:browser-debug",
    ]


def test_configured_device_node_exposes_api_routes_without_urirun_health() -> None:
    item = transport.discover_node({
        "name": "cam-rpi",
        "url": "http://cam.local",
        "tags": ["kind:device"],
        "apis": [
            {"id": "panel", "kind": "web", "url": "http://cam.local"},
            {"id": "stream", "kind": "rtsp", "role": "camera", "url": "rtsp://cam.local/live"},
            {"id": "ssh", "kind": "ssh", "url": "ssh://pi@cam.local"},
            {"id": "nas", "kind": "smb", "url": "smb://cam.local/share"},
        ],
    })

    uris = {route["uri"] for route in item["routes"]}
    assert item["reachable"] is True
    assert item["health"]["external"] is True
    assert "device://cam-rpi/panel/query/status" in uris
    assert "api://cam-rpi/panel/command/request" in uris
    assert "media://cam-rpi/stream/query/stream" in uris
    assert "camera://cam-rpi/stream/query/snapshot" in uris
    assert "ssh://cam-rpi/ssh/command/run" in uris
    assert "fs://cam-rpi/nas/query/list" in uris
