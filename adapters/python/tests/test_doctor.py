from __future__ import annotations

import pytest
from urirun.node.doctor import (
    _api_id, _api_protocol, _auth_configured, _connector_installed,
    check_api_node, check_urirun_node, diagnose_mesh, format_doctor_report,
)


def test_api_id_normalizes():
    assert _api_id({"id": "My Camera"}, 1) == "my-camera"
    assert _api_id({}, 3) == "api-3"


def test_api_protocol_defaults_http():
    assert _api_protocol({}) == "http"
    assert _api_protocol({"kind": "rtsp"}) == "rtsp"
    assert _api_protocol({"protocol": "SSH"}) == "ssh"


def test_auth_configured_detects_secretref():
    assert _auth_configured({"auth": {"secretRef": "MY_KEY"}}) is True
    assert _auth_configured({"apiKey": "abc"}) is True
    assert _auth_configured({}) is False


def test_connector_installed_unknown_returns_none():
    assert _connector_installed("unknownprotocol99") is None


def test_connector_installed_missing_package():
    assert _connector_installed("rtsp") is False


def test_check_api_node_http_no_connector_required():
    node_cfg = {
        "name": "myapi",
        "apis": [{"id": "v1", "kind": "http", "url": "http://localhost:9999/api"}],
    }
    checks = check_api_node(node_cfg, timeout=0.1)
    assert len(checks) == 1
    c = checks[0]
    assert c["node"] == "myapi"
    assert c["protocol"] == "http"
    assert c["needsConnector"] is False
    assert c["connectorInstalled"] is None


def test_check_api_node_rtsp_needs_connector():
    node_cfg = {
        "name": "cam",
        "apis": [{"id": "cam1", "kind": "rtsp", "url": "rtsp://192.168.1.50:554/stream"}],
    }
    checks = check_api_node(node_cfg, timeout=0.1)
    assert len(checks) == 1
    c = checks[0]
    assert c["needsConnector"] is True
    assert c["connectorInstalled"] is False
    assert c["connectorModule"] == "urirun_connector_rtsp"


def test_check_urirun_node_up():
    result = {"name": "laptop", "url": "http://laptop:8766", "reachable": True}
    c = check_urirun_node(result)
    assert c["apiId"] == "(urirun)"
    assert c["needsConnector"] is False
    assert c["ok"] is True


def test_check_urirun_node_down():
    result = {"name": "laptop", "url": "http://laptop:8766", "reachable": False, "error": "connection refused"}
    c = check_urirun_node(result)
    assert c["ok"] is False
    assert c["reachDetail"] == "connection refused"


def test_diagnose_mesh_api_and_urirun():
    config = {
        "nodes": [
            {"name": "cam-node", "apis": [{"id": "cam", "kind": "rtsp", "url": "rtsp://127.0.0.1:9999/s"}]},
            {"name": "urirun-node", "url": "http://localhost:8766"},
        ]
    }
    mesh = {
        "nodes": [
            {"name": "urirun-node", "url": "http://localhost:8766", "reachable": False, "error": "refused"},
        ]
    }
    checks = diagnose_mesh(config, mesh, timeout=0.1)
    assert len(checks) == 2
    assert checks[0]["node"] == "cam-node"
    assert checks[0]["protocol"] == "rtsp"
    assert checks[1]["node"] == "urirun-node"
    assert checks[1]["protocol"] == "urirun"


def test_format_doctor_report_columns():
    checks = [
        {"node": "n", "apiId": "a", "protocol": "http", "reachable": True,
         "reachDetail": "HTTP 200", "authConfigured": True, "needsConnector": False,
         "connectorInstalled": None, "connectorModule": None, "ok": True},
        {"node": "n", "apiId": "b", "protocol": "rtsp", "reachable": False,
         "reachDetail": "refused", "authConfigured": False, "needsConnector": True,
         "connectorInstalled": False, "connectorModule": "urirun_connector_rtsp", "ok": False},
    ]
    report = format_doctor_report(checks)
    assert "NODE" in report
    assert "CONNECTOR" in report
    assert "MISSING" in report
    assert "built-in" in report
    assert "pip install urirun-connector-rtsp" in report


def test_format_doctor_report_empty():
    assert format_doctor_report([]) == "(no nodes configured)"
