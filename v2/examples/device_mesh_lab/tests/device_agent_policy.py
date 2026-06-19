#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import tempfile

import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from device_agent import DeviceAgent  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="urirun-agent-policy-") as tmp:
        agent = DeviceAgent(name="desktop", role="test", root=pathlib.Path(tmp), allow_browser=False)
        result = agent.dispatch("browser://desktop/page/command/open", {"url": "https://example.com/"})
        assert result["ok"] is False
        assert result["error"]["type"] == "policy"
        assert result["result"]["executed"] is False
        assert result["result"]["allowBrowser"] is False

        routes = {route["uri"]: route for route in agent.routes()}
        browser_route = routes["browser://desktop/page/command/open"]
        assert browser_route["enabled"] is False
        assert browser_route["policy"]["allowBrowser"] is False

    print("PASS device_agent_policy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
