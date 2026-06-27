#!/usr/bin/env python3
"""External conformance driver — what a cross-language round-trip CANNOT prove on its own.

A node may pass its OWN in-language gate yet still lie on the wire (serialization/transport bug).
This driver calls a REAL served node over HTTP by its true URI, unwraps the transported envelope
(``result.value``), and validates it against the SAME neutral contracts.json the language gates use.
"Implementation conforms" then means: the node's real wire response satisfies the shared contract.

Usage: driver.py <port> <workdir>
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request

from urirun_connectors_toolkit.contract_gate import check

DOC = json.load(open(os.path.join(os.path.dirname(__file__), "contracts.json")))
OUT = {r: c["out"] for r, c in DOC["contracts"].items()}


def call(port: int, uri: str, payload: dict) -> dict:
    # confirm=True satisfies the node's HITL gate on destructive routes (e.g. delete sets
    # requireConfirm) — a transport/policy reality the in-language gate never sees.
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/run",
        data=json.dumps({"uri": uri, "payload": payload, "mode": "execute", "confirm": True}).encode(),
        headers={"Content-Type": "application/json"})
    try:
        env = json.loads(urllib.request.urlopen(req, timeout=15).read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        try:
            env = json.loads(body)
        except Exception:  # noqa: BLE001
            return {"ok": False, "httpStatus": exc.code, "body": body[:200]}
    return (env.get("result") or {}).get("value") or env  # unwrap the transported handler value


def conforms(uri: str, value: dict) -> str | None:
    try:
        check(OUT[uri], value, "wire")
        return None
    except AssertionError as exc:
        return str(exc)


def main() -> int:
    port, work = int(sys.argv[1]), sys.argv[2]
    a, b = os.path.join(work, "a.txt"), os.path.join(work, "b.txt")
    b64 = base64.b64encode(b"hello world").decode()

    # real over-the-wire calls, validated against the shared contract
    plan = [
        ("fs://host/file/command/write-b64", {"path": a, "bytes_b64": b64}),
        ("fs://host/file/query/read-b64", {"path": a}),
        ("fs://host/file/command/write-b64", {"path": b, "bytes_b64": b64}),  # a duplicate for dedup
        ("fs://host/duplicates/query/find", {"root": work, "mode": "sha256"}),
        ("fs://host/duplicates/command/move", {"root": work, "mode": "sha256", "dry_run": True}),
        ("fs://host/file/command/delete", {"path": a}),
    ]
    failures = 0
    last_value = None
    for uri, payload in plan:
        value = call(port, uri, payload)
        bad = conforms(uri, value)
        if uri == "fs://host/file/query/read-b64":
            last_value = value
        print(f"  [{'OK ' if bad is None else 'FAIL'}] wire {uri.split('://',1)[1]:32} -> "
              f"{'conforms' if bad is None else bad}")
        failures += bad is not None

    # negative: a node that LIED on the wire (bytes int -> string) must be rejected by the driver
    if last_value is not None:
        lied = dict(last_value, bytes="oops")
        bad = conforms("fs://host/file/query/read-b64", lied)
        ok = bad is not None
        print(f"\n  lying-node guard: a corrupted wire response is "
              f"{'REJECTED' if ok else 'WRONGLY ACCEPTED'} -> {bad}")
        failures += not ok

    print(f"\n  {len(plan)} real wire calls validated; {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
