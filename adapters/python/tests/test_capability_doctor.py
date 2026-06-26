# Author: Tom Sapletta · https://tom.sapletta.com
# Tests for urirun.host.capability — proactive capability doctor for API/device nodes.
from __future__ import annotations

import unittest.mock as mock

from urirun.host.capability import (
    api_node_doctor,
    _check_auth,
    _check_connector,
    _check_reachability,
    _protocol_owner,
)


# ─── _check_auth ─────────────────────────────────────────────────────────────


def test_auth_no_secret_ref_is_ok():
    result = _check_auth({"kind": "http", "url": "http://api.example.com"})
    assert result["ok"] is True
    assert "public" in result["detail"]


def test_auth_inline_credential_is_ok():
    result = _check_auth({"apiKey": "sk-plain-key", "kind": "http"})
    assert result["ok"] is True
    assert "inline" in result["detail"]


def test_auth_secret_ref_resolved_is_ok():
    with mock.patch("urirun.host.capability.resolve_secret", return_value="real-key"):
        result = _check_auth({"secretRef": "secret://env:MY_API_KEY"})
    assert result["ok"] is True
    assert "resolved" in result["detail"]


def test_auth_secret_ref_empty_is_fail():
    with mock.patch("urirun.host.capability.resolve_secret", return_value=""):
        result = _check_auth({"secretRef": "secret://env:MISSING_KEY"})
    assert result["ok"] is False
    assert "empty" in result["detail"]


def test_auth_secret_ref_exception_is_fail():
    with mock.patch("urirun.host.capability.resolve_secret",
                   side_effect=RuntimeError("keyring locked")):
        result = _check_auth({"secretRef": "secret://keyring:my-key"})
    assert result["ok"] is False
    assert "unresolvable" in result["detail"]


# ─── _check_reachability ─────────────────────────────────────────────────────


def test_reachability_no_url_is_indeterminate():
    result = _check_reachability({})
    assert result["ok"] is None


def test_reachability_tcp_success():
    with mock.patch("urirun.host.capability.socket.create_connection"):
        result = _check_reachability({"url": "http://api.example.com:80"})
    assert result["ok"] is True
    assert "reachable" in result["detail"]


def test_reachability_tcp_failure():
    import socket as _socket
    with mock.patch("urirun.host.capability.socket.create_connection",
                   side_effect=_socket.timeout("timed out")):
        result = _check_reachability({"url": "http://unreachable.local:9999"})
    assert result["ok"] is False
    assert "failed" in result["detail"]


def test_reachability_defaults_port_443_for_https():
    calls = []
    def _fake_connect(addr, timeout):
        calls.append(addr)
        return mock.MagicMock().__enter__.return_value

    with mock.patch("urirun.host.capability.socket.create_connection", side_effect=_fake_connect):
        _check_reachability({"url": "https://secure.api.com/v1"})
    assert calls and calls[0][1] == 443


# ─── _check_connector ────────────────────────────────────────────────────────


def test_connector_built_in_adapter_is_ok():
    result = _check_connector("http")
    assert result["ok"] is True
    assert "built-in" in result["detail"]


def test_connector_installed_package_is_ok():
    with mock.patch("urirun.host.capability.importlib.util.find_spec", return_value=object()):
        result = _check_connector("rtsp")
    assert result["ok"] is True
    assert "installed" in result["detail"]
    assert result["package"] == "urirun-connector-rtsp"


def test_connector_missing_package_is_fail():
    with mock.patch("urirun.host.capability.importlib.util.find_spec", return_value=None):
        result = _check_connector("ssh")
    assert result["ok"] is False
    assert "NOT installed" in result["detail"]
    assert "installCommand" in result
    assert "pip install" in result["installCommand"]


# ─── _protocol_owner ─────────────────────────────────────────────────────────


def test_protocol_owner_known():
    assert "built-in" in _protocol_owner("http")
    assert "urirun-connector-ssh" in _protocol_owner("ssh")
    assert "urirun-connector-rtsp" in _protocol_owner("rtsp")


def test_protocol_owner_unknown_is_speculative():
    result = _protocol_owner("myprotocol")
    assert "speculative" in result


# ─── api_node_doctor ─────────────────────────────────────────────────────────


def _http_api(url="http://api.example.com"):
    return {"id": "api1", "kind": "http", "label": "My API", "url": url}


def _rtsp_api():
    return {"id": "cam1", "kind": "rtsp", "label": "IP Camera",
            "url": "rtsp://cam.local:554/stream"}


def test_doctor_all_pass_returns_ok():
    node = {"name": "hub", "apis": [_http_api()]}
    with mock.patch("urirun.host.capability.socket.create_connection"):
        result = api_node_doctor(node)
    assert result["ok"] is True
    assert result["nodeId"] == "hub"
    assert len(result["apis"]) == 1
    assert result["apis"][0]["apiKind"] == "http"


def test_doctor_missing_connector_returns_not_ok():
    node = {"name": "hub", "apis": [_rtsp_api()]}
    with (mock.patch("urirun.host.capability.socket.create_connection"),
          mock.patch("urirun.host.capability.importlib.util.find_spec", return_value=None)):
        result = api_node_doctor(node)
    assert result["ok"] is False
    connector_check = next(c for c in result["apis"][0]["checks"] if c["name"] == "connector")
    assert connector_check["ok"] is False


def test_doctor_empty_apis_returns_not_ok():
    result = api_node_doctor({"name": "empty", "apis": []})
    assert result["ok"] is False
    assert result["apis"] == []


def test_doctor_no_url_is_degraded_not_failed():
    node = {"name": "hub", "apis": [{"id": "api1", "kind": "http", "label": "No URL"}]}
    result = api_node_doctor(node)
    reachability = next(c for c in result["apis"][0]["checks"]
                        if c["name"] == "reachability")
    assert reachability["ok"] is None
    assert result["degraded"] is True


def test_doctor_protocol_owner_set_per_api():
    node = {"name": "hub", "apis": [_http_api(), _rtsp_api()]}
    with (mock.patch("urirun.host.capability.socket.create_connection"),
          mock.patch("urirun.host.capability.importlib.util.find_spec", return_value=object())):
        result = api_node_doctor(node)
    owners = {a["apiId"]: a["protocolOwner"] for a in result["apis"]}
    assert "built-in" in owners["api1"]
    assert "rtsp" in owners["cam1"]


def test_doctor_secret_ref_fail_propagates():
    node = {"name": "hub", "apis": [
        {"id": "llm1", "kind": "http", "url": "https://api.openai.com",
         "secretRef": "secret://env:MISSING_KEY"}
    ]}
    with (mock.patch("urirun.host.capability.socket.create_connection"),
          mock.patch("urirun.host.capability.resolve_secret", return_value="")):
        result = api_node_doctor(node)
    assert result["ok"] is False
    auth_check = next(c for c in result["apis"][0]["checks"] if c["name"] == "auth")
    assert auth_check["ok"] is False
