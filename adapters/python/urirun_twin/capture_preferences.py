# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.

"""Fingerprint-scoped capture preferences owned by the Digital Twin layer."""

from __future__ import annotations

from typing import Any


def capture_preference_from_payload(payload: dict | None) -> dict[str, Any]:
    scope = str((payload or {}).get("scope") or "").strip().lower()
    if scope in {"all", "all-monitors", "desktop"}:
        return {"scope": "all", "monitor": -1}
    try:
        monitor = int((payload or {}).get("monitor") or 0)
    except (TypeError, ValueError):
        monitor = 0
    if monitor > 0:
        return {"monitor": monitor}
    return {}


def capture_payload_has_result_reference(payload: dict | None) -> bool:
    """True when capture target is produced by a prior flow step.

    Fingerprint preferences are defaults; they must not override explicit
    runtime bindings such as ``monitor_from``.
    """
    data = payload or {}
    return any(
        key in data and isinstance(data.get(key), str)
        for key in ("monitor_from", "scope_from")
    )


def capture_step_node(step: dict | None) -> str:
    uri = str((step or {}).get("uri") or "")
    if "://" not in uri:
        return "host"
    return uri.split("://", 1)[1].split("/", 1)[0] or "host"


def capture_preference_fingerprint(memory: object | None, node: str) -> str:
    if memory is None or not hasattr(memory, "known_good"):
        return ""
    rec = memory.known_good(node) or memory.known_good("host")
    return str((rec or {}).get("fingerprint") or "")


def _apply_pref_to_step(step: dict, memory: object) -> tuple[dict, bool]:
    new_step = dict(step)
    uri = str(new_step.get("uri") or "")
    payload = dict(new_step.get("payload") or {})
    if (
        "/screen/query/capture" not in uri
        or capture_payload_has_result_reference(payload)
        or capture_preference_from_payload(payload)
    ):
        return new_step, False
    node = capture_step_node(new_step)
    fingerprint = capture_preference_fingerprint(memory, node)
    if not fingerprint:
        return new_step, False
    pref = memory.recall_preference(node, "screen.capture.default", fingerprint)
    value = (pref or {}).get("value") if isinstance(pref, dict) else None
    if isinstance(value, dict) and capture_preference_from_payload(value):
        payload.update(value)
        new_step["payload"] = payload
        return new_step, True
    return new_step, False


def apply_capture_preferences(flow: dict, memory: object | None) -> dict:
    if memory is None or not hasattr(memory, "recall_preference"):
        return flow
    out = []
    changed = False
    for step in flow.get("steps") or []:
        new_step, step_changed = _apply_pref_to_step(step, memory)
        out.append(new_step)
        changed = changed or step_changed
    return {**flow, "steps": out} if changed else flow


def remember_capture_preferences(flow: dict, execution: dict, memory: object | None) -> None:
    if memory is None or not hasattr(memory, "remember_preference") or not execution.get("ok"):
        return
    for step in flow.get("steps") or []:
        uri = str(step.get("uri") or "")
        if "/screen/query/capture" not in uri:
            continue
        pref = capture_preference_from_payload(step.get("payload") or {})
        if pref:
            node = capture_step_node(step)
            fingerprint = capture_preference_fingerprint(memory, node)
            if fingerprint:
                memory.remember_preference(node, "screen.capture.default", pref, fingerprint)


__all__ = [
    "apply_capture_preferences",
    "capture_payload_has_result_reference",
    "capture_preference_fingerprint",
    "capture_preference_from_payload",
    "capture_step_node",
    "remember_capture_preferences",
]
