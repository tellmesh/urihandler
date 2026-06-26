from __future__ import annotations

from typing import Any


def try_urifix_repair(
    prompt: str,
    request: dict,
    result: dict,
    *,
    node_urls: "list[str] | None" = None,
    host_config: "dict | None" = None,
    known_nodes: "list[str] | dict | None" = None,
    apply: bool = False,
    registry: Any = None,
) -> "dict | None":
    """Diagnose (and, when apply=True + a registry are given, resolve) a failed URI chain via the
    urifix connector. `known_nodes` lets urifix resolve a missing node URL from the host's known
    set; urifix also reads ~/.urirun/nodes.json on its own. apply is left False here: callers that
    want automatic recovery must validate the returned retry contract before doing side effects."""
    try:
        from urirun_connector_urifix.core import repair_chain  # type: ignore  # noqa: PLC0415
    except Exception:  # noqa: BLE001 - urifix is optional.
        return None
    kwargs: dict[str, Any] = {
        "prompt": prompt,
        "request": request,
        "result": result,
        "node_urls": node_urls or [],
        "host_config": host_config or {},
    }
    # Forward the newer args only when supported, so the host stays compatible with an older urifix.
    import inspect  # noqa: PLC0415
    params = inspect.signature(repair_chain).parameters
    if "known_nodes" in params and known_nodes is not None:
        kwargs["known_nodes"] = known_nodes
    if "apply" in params and apply:
        kwargs["apply"] = True
    if "registry" in params and registry is not None:
        kwargs["registry"] = registry
    try:
        fixed = repair_chain(**kwargs)
    except Exception as exc:  # noqa: BLE001 - never mask the original URI failure.
        return {"ok": False, "error": str(exc)}
    return fixed if isinstance(fixed, dict) else None
