"""urihandler v8 service adapter - dispatch a URI to a remote worker over HTTP.

In a polyglot deployment each worker implements its own URI resources natively
(Python, Node.js, shell, ...). From a coordinator's point of view those URIs are
*services*: it validates the input against the registry and POSTs to the worker.

This adapter makes that the library's job instead of bespoke orchestrator code:

```python
from urihandler import v8_service
env = v8_service.call("python://python-worker/text/normalize",
                      {"text": "Hello"}, registry)   # validates + POSTs /run
```

The target host resolves to ``http://<target>:8080`` by default, overridable
with ``URI_SERVICE_MAP`` (the same env the docker_uri_flow orchestrator uses), so
the same registry drives Docker DNS, localhost ports, or any topology.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from urihandler import v8

DEFAULT_PORT = 8080


def service_base(target: str) -> str:
    mapping = os.getenv("URI_SERVICE_MAP")
    if mapping:
        table = json.loads(mapping)
        if target in table:
            return str(table[target]).rstrip("/")
    return f"http://{target}:{DEFAULT_PORT}"


def run_service(ctx: dict, policy: dict, execute: bool) -> dict:
    descriptor = ctx["descriptor"]
    uri = descriptor["normalized"]
    payload = ctx.get("payload") or {}
    url = f"{service_base(descriptor['target'])}/run"
    if not execute:
        return {"simulated": True, "type": "service", "url": url, "request": {"uri": uri, "payload": payload}}

    body = json.dumps({"uri": uri, "payload": payload}).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=policy.get("timeout", 30)) as response:
            data = json.loads(response.read().decode("utf-8"))
            status = response.status
    except urllib.error.HTTPError as err:
        data = json.loads(err.read().decode("utf-8") or "{}")
        status = err.code
    ok = bool(data.get("ok", status < 400))
    return {"type": "service", "url": url, "status": status, "response": data,
            "result": data.get("result"), "exitCode": 0 if ok else 1}


EXECUTORS = {**v8.EXECUTORS, "service": run_service}


def run(uri: str, registry: dict, payload=None, mode: str = "dry-run", policy: dict | None = None,
        confirm: bool = False) -> dict:
    """Like ``v8.run`` but with the ``service`` adapter available.

    Schema validation still happens in ``v8.run`` before the call, so a bad
    payload is rejected at the coordinator, not the worker.
    """
    return v8.run(uri, registry, payload=payload, mode=mode, policy=policy, confirm=confirm, executors=EXECUTORS)


def call(uri: str, payload: dict, registry: dict, mode: str = "execute", policy: dict | None = None) -> dict:
    if policy is None and mode == "execute":
        policy = {"execute": {"allow": [uri]}}
    return run(uri, registry, payload=payload, mode=mode, policy=policy)
