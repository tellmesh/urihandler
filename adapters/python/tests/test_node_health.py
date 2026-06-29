from __future__ import annotations

from urirun.host import node_health


def test_webpage_relay_unreachable_remediation_asks_to_reopen_page():
    check, early = node_health._build_reachable_check(
        "http://192.168.188.212:8195/api/webpage-node/relay/web1",
        "android-web1",
        False,
    )

    assert early is not None
    remediation = check["remediation"]
    assert remediation["class"] == "unreachable"
    assert remediation["command"] == ""
    assert "Otwórz ponownie na telefonie" in remediation["humanAction"]
    assert "http://192.168.188.212:8195/" in remediation["humanAction"]


def test_regular_node_unreachable_remediation_keeps_node_serve_command():
    check, early = node_health._build_reachable_check(
        "http://192.168.188.201:8765",
        "lenovo",
        False,
    )

    assert early is not None
    remediation = check["remediation"]
    assert remediation["command"] == "urirun node serve --name lenovo"
