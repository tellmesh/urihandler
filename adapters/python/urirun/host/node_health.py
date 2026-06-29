"""Host-side node health probes — classify each potential failure class for a target node.

``node_doctor`` is the host-side generalisation of ``capability.api_node_doctor``
(which handles API/device nodes) for urirun nodes.  It runs each probe independently
so the dashboard can render a per-class 🟢/🟡/🔴 with an actionable human instruction
rather than a wall of logs.

Reuses:
  • ``transport._probe_health`` concept (HTTP GET /health)
  • ``node_dispatch.classify_error`` taxonomy (RemediationClass)
  • ``NodeClient.schemes()`` for route presence
  • host token probe from ``host_dashboard._probe_node_token_impl`` (by reference, not import)

Extraction rule: only pure probes here; no HTTP server, no dashboard state.
"""
from __future__ import annotations

import json
import urllib.request
from typing import Any

from urirun_contracts import Remediation, RemediationClass

__all__ = ["node_doctor", "classify_node_error"]


# ──────────────────────────────────────────────────────────────────────────────
# Low-level probes
# ──────────────────────────────────────────────────────────────────────────────

def _http_get_json(url: str, timeout: float = 3.0) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8") or "{}")
    except Exception:
        return {}


def _probe_reachable(node_url: str) -> tuple[bool, dict]:
    """GET /health — returns (reachable, health_payload)."""
    health = _http_get_json(f"{node_url.rstrip('/')}/health")
    return bool(health.get("ok")), health


def _probe_auth(node_url: str, token: str | None, identity: str | None) -> str:
    """Return 'ok' | 'denied' | 'unknown'."""
    from urirun.host.fs_transfer import node_client
    client = node_client(node_url, token=token, identity=identity)
    try:
        env = client.run("node://host/health/query/ping", {}, timeout=3.0)
    except Exception as exc:
        msg = str(exc).lower()
        if any(k in msg for k in ("401", "403", "unauthorized", "forbidden")):
            return "denied"
        return "unknown"
    if env.get("ok"):
        return "ok"
    err_msg = str((env.get("error") or {}).get("message") or "").lower()
    if any(k in err_msg for k in ("401", "403", "unauthorized", "forbidden", "token")):
        return "denied"
    return "unknown"


def _probe_schemes(node_url: str, token: str | None, identity: str | None) -> list[str]:
    """Return sorted list of scheme names the node serves."""
    from urirun.host.fs_transfer import node_client
    client = node_client(node_url, token=token, identity=identity)
    try:
        return sorted(client.schemes())
    except Exception:
        return []


def _probe_version(health_data: dict) -> tuple[str, str]:
    """Return (version_str, status) where status is 'ok' | 'unknown'."""
    for key in ("version", "urirunVersion", "urirun_version"):
        v = str(health_data.get(key) or "")
        if v:
            return v, "ok"
    return "", "unknown"


# ──────────────────────────────────────────────────────────────────────────────
# Doctor
# ──────────────────────────────────────────────────────────────────────────────

def _webpage_reconnect_url(node_url: str) -> str:
    marker = "/api/webpage-node/relay/"
    idx = node_url.find(marker)
    return node_url[:idx + 1] if idx >= 0 else ""


def _build_reachable_check(node_url: str, node: str, reachable: bool) -> tuple[dict[str, Any], dict | None]:
    """Build the reachable check dict; return (check, early_result) where early_result is set
    only when the node is unreachable (callers should return it immediately)."""
    check: dict[str, Any] = {
        "class": RemediationClass.UNREACHABLE.value,
        "ok": reachable,
        "detail": f"GET {node_url}/health → {'ok' if reachable else 'no response'}",
    }
    if not reachable:
        reconnect_url = _webpage_reconnect_url(node_url)
        human_action = (
            f"Webpage node '{node}' offline albo relay utracił sesję. "
            f"Otwórz ponownie na telefonie: {reconnect_url}"
        ) if reconnect_url else f"Node '{node}' offline. Uruchom: urirun node serve --name {node}"
        r = Remediation(
            cls=RemediationClass.UNREACHABLE, node=node,
            human_action=human_action,
            command="" if reconnect_url else f"urirun node serve --name {node}",
            dashboard_url=f"?node={node}&fix=unreachable",
        )
        check["remediation"] = r.to_dict()
        return check, _result(node, node_url, ok=False, checks=[check],
                              summary=f"unreachable — {node_url}")
    return check, None


def _build_auth_check(node: str, node_url: str, auth_status: str) -> dict[str, Any]:
    """Build the authentication check dict, attaching remediation when denied."""
    check: dict[str, Any] = {
        "class": RemediationClass.UNAUTHENTICATED.value,
        "ok": auth_status != "denied",
        "detail": auth_status,
    }
    if auth_status == "denied":
        r = Remediation(
            cls=RemediationClass.UNAUTHENTICATED, node=node,
            human_action=(
                f"Node '{node}' odrzucił token. Enroll: "
                f"uri-copy-id {node_url} -i ~/.ssh/id_ed25519 --enroll-token <PIN>"
            ),
            command=f"uri-copy-id {node_url} -i ~/.ssh/id_ed25519 --enroll-token <PIN>",
            dashboard_url=f"?node={node}&fix=unauthenticated",
        )
        check["remediation"] = r.to_dict()
    return check


def _build_routes_check(node: str, node_url: str, schemes: list[str]) -> dict[str, Any]:
    """Build the route-presence check dict, attaching remediation when no schemes are found."""
    detail = (
        f"{len(schemes)} scheme(s): {', '.join(schemes[:8])}"
        f"{'…' if len(schemes) > 8 else ''}"
    )
    check: dict[str, Any] = {
        "class": RemediationClass.ROUTE_MISSING.value,
        "ok": bool(schemes),
        "detail": detail,
        "schemes": schemes,
    }
    if not schemes:
        r = Remediation(
            cls=RemediationClass.ROUTE_MISSING, node=node,
            human_action=f"Node '{node}' ma 0 tras. Zainstaluj connectors i zrestartuj node.",
            command="pip install urirun-connector-fs urirun-connector-browser-control",
            dashboard_url=f"?node={node}&fix=route-missing",
        )
        check["remediation"] = r.to_dict()
    return check


def _build_version_check(health_data: dict) -> tuple[dict[str, Any], str]:
    """Build the version check dict; return (check, version_str) for use in the summary."""
    version_str, version_status = _probe_version(health_data)
    check: dict[str, Any] = {
        "class": RemediationClass.VERSION_SKEW.value,
        "ok": version_status == "ok",
        "detail": version_str or "no version info in /health",
    }
    return check, version_str


def _build_doctor_summary(auth_status: str, version_str: str, schemes: list[str], failed: list[dict]) -> str:
    """Format the one-line summary for ``node_doctor``."""
    issues = f", issues: {[c['class'] for c in failed]}" if failed else ""
    return (
        f"reachable=yes, auth={auth_status}, version={version_str or '?'}, "
        f"schemes={len(schemes)}{issues}"
    )


def node_doctor(
    node_url: str,
    *,
    node_name: str = "",
    token: str | None = None,
    identity: str | None = None,
    timeout: float = 5.0,
) -> dict:
    """Run all health probes for a urirun node; return a structured per-class report.

    Result shape::

        {
          ok: bool,            # True only when every probe passes
          node: str,
          nodeUrl: str,
          summary: str,        # one-line human description
          checks: [
            {class, ok, detail, remediation?: {...}}
          ],
          health: {...},       # raw /health payload
          schemes: [...],      # available scheme names
        }

    The ``checks`` list is ordered by diagnostic priority
    (reachable first — if unreachable, subsequent probes are skipped).
    """
    node = node_name or _node_from_url(node_url)

    # 1 ── Reachable ──────────────────────────────────────────────────────────
    reachable, health_data = _probe_reachable(node_url)
    c1, early = _build_reachable_check(node_url, node, reachable)
    if early is not None:
        return early

    # 2 ── Authenticated ───────────────────────────────────────────────────────
    auth_status = _probe_auth(node_url, token, identity)
    c2 = _build_auth_check(node, node_url, auth_status)

    # 3 ── Version ─────────────────────────────────────────────────────────────
    c3, version_str = _build_version_check(health_data)

    # 4 ── Routes ──────────────────────────────────────────────────────────────
    schemes = _probe_schemes(node_url, token, identity)
    c4 = _build_routes_check(node, node_url, schemes)

    # ── Summary ───────────────────────────────────────────────────────────────
    checks = [c1, c2, c3, c4]
    failed = [c for c in checks if not c["ok"]]
    summary = _build_doctor_summary(auth_status, version_str, schemes, failed)
    return _result(node, node_url, ok=not failed, checks=checks, summary=summary,
                   health=health_data, schemes=schemes)


# ──────────────────────────────────────────────────────────────────────────────
# Convenience: classify a node error without running probes
# ──────────────────────────────────────────────────────────────────────────────

def classify_node_error(error: Any, *, node: str, uri: str = "") -> dict:
    """Thin alias around ``node_dispatch.classify_error`` for callers that import from here."""
    from urirun.host.node_dispatch import classify_error
    return classify_error(error, node=node, uri=uri).to_dict()


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _node_from_url(node_url: str) -> str:
    host = node_url.split("://", 1)[-1].split("/")[0]
    return host.split(":")[0]


def _result(
    node: str, node_url: str, *, ok: bool, checks: list, summary: str, **extra: Any
) -> dict:
    return {"ok": ok, "node": node, "nodeUrl": node_url,
            "checks": checks, "summary": summary, **extra}
