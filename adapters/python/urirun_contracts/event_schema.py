# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# Event contract for the twin EventHub — the shared schema that both engines
# (_thin_driver via append_twin_widget, and any connector-side flow_execute)
# MUST conform to so that a single subscriber in node/server.py can reconstruct
# Episode atoms from the stream without knowing which engine emitted the event.
#
# Two event shapes:
#   StepEvent        — one per non-infra step, emitted as it completes
#   FlowCompletedEvent — one per flow, after the last step
#
# Required fields at each emission point:
#
#   step_uri        — the concrete URI that ran (already in transition.forward)
#   status          — "applied" | "degraded" | "blocked"
#   category        — "observational" | "reversible" | "irreversible"
#                     derivable from _step_inverse(); must be explicit in the event
#                     so subscribers don't re-derive it independently
#   proof_key       — pf-xxx | None; set by preflight_step, None for unproven steps
#   episode_id      — ep-xxx; ties this step to its Episode atom list
#   experience_id   — corpus / chat-session ID
#   intent_sig      — intent-xxx; for recall matching at Episode level
#
# The contract is ADDITIVE: existing subscribers reading only uri/status/transition
# continue to work. New subscribers (Episode recorder, recall, twin panel) read the
# new fields. Fields not yet wired default to "".
#
# Canonical emission point (both engines converge here):
#   twin_bridge._publish_step_event  — takes the step dict + new optional kwargs
#
# Subscriber injection point:
#   TWIN_EVENT_HUB.replay_since(seq) / subscribe() in node/server.py
from __future__ import annotations

from typing import TypedDict


class _StepTransition(TypedDict):
    before: dict            # env snapshot before the step (may be placeholder)
    forward: str            # the step URI
    inverse: str | None     # inverse URI or None
    after: dict             # env snapshot after the step (may be placeholder)
    reversible: bool


class StepEvent(TypedDict):
    """Emitted by _publish_step_event for every non-infra step."""
    uri: str                # "twin://monitor/event"  (routing key, not the step URI)
    step_uri: str           # the concrete step URI — equals transition.forward
    status: str             # "applied" | "degraded" | "blocked"
    degraded: bool
    degradedReason: str | None
    category: str           # "observational" | "reversible" | "irreversible"
    proof_key: str | None   # pf-xxx if preflighted; None for unproven steps
    episode_id: str         # ep-xxx — atom list reference
    experience_id: str      # corpus / chat-session ID
    intent_sig: str         # intent-xxx — for Episode recall
    narration: str          # human-readable step description
    transition: _StepTransition


class FlowCompletedEvent(TypedDict):
    """Emitted once at the end of a flow run."""
    flowCompleted: bool     # always True
    prompt: str
    episode_id: str
    outcome_status: str     # "ok" | "degraded" | "blocked" | "failed"
    next_intent: str


# ────────────────────────────────────── category derivation ──── #

_STEP_INVERSE_TABLE: "list[tuple[tuple[str, ...], str | None, bool]]" = [
    # (uri fragments to match, inverse_uri, reversible)
    (("/query/", "/screen/query/capture"),                    None,                                          True),
    (("/command/wait", "/query/ready", "/query/verify"),      None,                                          True),
    (("/session/command/ensure", "/session/command/launch"),  "kvm://host/cdp/session/command/close",        True),
    (("/page/command/navigate", "/command/navigate"),         "browser://cdp/page/command/back",             True),
    (("/command/reload",),                                    "browser://cdp/page/command/back",             True),
    (("/command/scroll",),                                    "kvm://host/input/command/scroll-inverse",     True),
    (("/command/click", "/command/fill", "/command/type",
      "/command/submit", "/command/send", "/command/press"),  None,                                          False),
    (("/command/",),                                          None,                                          False),
]


def _step_inverse(step_uri: str) -> "tuple[str | None, bool]":
    """Return (inverse_uri_or_description, reversible) for a URI step.

    Reversibility rules:
    - Read-only / query steps: reversible, no inverse needed (no state change)
    - Navigation: reversible via history_back
    - Session lifecycle: reversible via close
    - Input / click / fill / submit / send: irreversible (no undo)
    - Unknown command: conservative → irreversible

    Lives here (the node-level event contract) so both the contract (step_category) and the
    host StepEvent builder (twin_bridge) derive reversibility from ONE place, without
    twin_bridge living above event_schema (which formed a node→host cycle)."""
    u = step_uri or ""
    for fragments, inverse, reversible in _STEP_INVERSE_TABLE:
        if any(p in u for p in fragments):
            return inverse, reversible
    return None, True


def step_category(step_uri: str) -> str:
    """Derive the step category from its URI — one place, no re-derivation in subscribers.

    observational  — /query/ steps; no state change; degraded is acceptable
    reversible     — mutation that carries a registered inverse URI
    irreversible   — mutation with no registered inverse (click, fill, submit, …)

    The rule is derived from _step_inverse() so the two stay in sync:
    reversible=True + no inverse  → observational
    reversible=True + inverse uri → reversible
    reversible=False              → irreversible
    """
    inverse, reversible = _step_inverse(step_uri)
    if not reversible:
        return "irreversible"
    if inverse is None:
        return "observational"
    return "reversible"
