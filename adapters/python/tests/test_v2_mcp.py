# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.

from __future__ import annotations

from urirun import v2, v2_mcp


def test_v2_mcp_tool_names_are_unique_for_cqrs_uri_args():
    registry = v2.compile_registry({
        "version": "urirun.bindings.v2",
        "bindings": {
            "browser://desktop/page/command/open": {
                "kind": "command",
                "adapter": "argv-template",
                "argv": ["echo", "open"],
            },
            "browser://desktop/page/command/screenshot": {
                "kind": "command",
                "adapter": "argv-template",
                "argv": ["echo", "screenshot"],
            },
        },
    })

    tools = v2_mcp.to_mcp_tools(registry)
    names = [tool["name"] for tool in tools]

    assert len(names) == len(set(names))
    # the operation is part of the name (not dropped), so the two CQRS routes are
    # distinct and self-describing without disambiguation suffixes
    assert "browser_desktop_page_command_open" in names
    assert "browser_desktop_page_command_screenshot" in names


def test_v2_mcp_preserves_single_route_tool_name():
    registry = v2.compile_registry({
        "version": "urirun.bindings.v2",
        "bindings": {
            "httpcheck://host/http/query/status": {
                "kind": "command",
                "adapter": "argv-template",
                "argv": ["echo", "ok"],
            },
        },
    })

    assert v2_mcp.to_mcp_tools(registry)[0]["name"] == "httpcheck_host_http_query_status"
