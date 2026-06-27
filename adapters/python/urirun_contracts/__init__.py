"""Common error taxonomy, remediation contract, and envelope helpers for urirun host↔node.

The ``RemediationClass`` enum + ``Remediation`` dataclass are the shared vocabulary that
recovery.py, node_dispatch.py, fs_transfer, node_api, decision_loop and the dashboard
all use to classify and communicate failures.  Previously this taxonomy was scattered
across recovery.normalize_error, fs_transfer.envelope_error_message, and
node_api.connector_required_response with no shared schema.

Event shapes (StepEvent, FlowCompletedEvent) live in event_schema and are re-exported
here so importers only need ``from urirun_contracts import ...``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from urirun_contracts.event_schema import FlowCompletedEvent, StepEvent  # noqa: F401 — re-export

__all__ = [
    "RemediationClass",
    "Remediation",
    "StepEvent",
    "FlowCompletedEvent",
]


class RemediationClass(str, Enum):
    """Wyliczalny zbiór klas awarii host↔node.

    Every failure in host↔node communication belongs to one of these classes.
    Each class has a known auto-fix path and a human instruction so that callers
    don't need to parse error strings differently.
    """
    UNREACHABLE = "unreachable"
    NO_NODE_URL = "no-node-url"
    UNAUTHENTICATED = "unauthenticated"
    ROUTE_MISSING = "route-missing"
    VERSION_SKEW = "version-skew"
    DEGRADED_BACKEND = "degraded-backend"
    PRECONDITION_UNMET = "precondition-unmet"
    UNKNOWN = "unknown"


@dataclass
class Remediation:
    """Sklasyfikowana naprawa: co poszło nie tak, jak naprawić automatycznie, co powiedzieć user.

    Produced by ``node_dispatch.classify_error`` and attached to every failed
    host→node envelope as ``env["remediation"]``.  Callers that only want the
    dict shape should call ``.to_dict()``.
    """
    cls: RemediationClass
    node: str = ""
    auto_fix_uri: str = ""
    auto_fix_payload: dict = field(default_factory=dict)
    human_action: str = ""
    command: str = ""
    retry_uri: str = ""
    retry_payload: dict = field(default_factory=dict)
    dashboard_url: str = ""
    raw_error: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "class": self.cls.value,
            "node": self.node,
            "autoFixUri": self.auto_fix_uri,
            "autoFixPayload": self.auto_fix_payload,
            "humanAction": self.human_action,
            "command": self.command,
            "retryUri": self.retry_uri,
            "retryPayload": self.retry_payload,
            "dashboardUrl": self.dashboard_url,
            "rawError": self.raw_error,
        }
