# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# Experience-driven DIAGNOSTIC PLAYBOOK: failure-signature → named root cause → specific
# remediation (as URIs, some auto-applicable). Encodes the recurring NL→URI→desktop
# failure classes learned in the field so the recovery engine can DIAGNOSE and FIX instead
# of emitting a generic "inspect the route". Consulted by recovery.recovery_plan, which
# attaches the diagnosis to every failed step's timeline entry — so the same knowledge
# reaches a human, the dashboard, an auto-repair loop, or an LLM re-planner.
#
# A rule matches on the casefolded error message (regex), optionally gated by error category
# and/or URI scheme. ``remediation`` actions carry ``automatic: True`` when they are safe to
# apply unattended (idempotent provisioning / bounded retries) — the contract an auto-repair
# loop keys on. Add a rule whenever a new failure class is understood; nothing else changes.
from __future__ import annotations

import re
from typing import Any, Callable

from urirun.node.routing import route_target


def _target(step: dict | None) -> str:
    uri = str((step or {}).get("uri") or "")
    try:
        t = route_target(uri)
        if t:
            return t
    except Exception:  # noqa: BLE001
        pass
    if "://" in uri:
        return uri.split("://", 1)[1].split("/", 1)[0] or "host"
    return "host"


def _target_of(actions: list[dict]) -> str:
    """The node a diagnosis is about, read back from its remediation URIs — fit_to_environment
    has no step, only the actions. Falls back to ``host``."""
    for a in actions or []:
        u = str(a.get("uri") or "")
        if "://" in u:
            return u.split("://", 1)[1].split("/", 1)[0] or "host"
    return "host"


class _Rule:
    def __init__(self, rid: str, patterns: list[str], cause: str, remediation: Callable[[str], list[dict]],
                 *, categories: set[str] | None = None, schemes: set[str] | None = None,
                 confidence: float = 0.85) -> None:
        self.id = rid
        self.regexes = [re.compile(p) for p in patterns]
        self.cause = cause
        self.remediation = remediation
        self.categories = categories
        self.schemes = schemes
        self.confidence = confidence

    def matches(self, message: str, category: str, scheme: str) -> bool:
        if self.categories and category not in self.categories:
            return False
        if self.schemes and scheme not in self.schemes:
            return False
        return any(rx.search(message) for rx in self.regexes)


# The accumulated field experience, as rules. Order = priority (first match wins).
PLAYBOOK: list[_Rule] = [
    _Rule(
        "ui-target-not-located",
        [r"target not located", r"no on-screen text matches", r"no control strategy could",
         r"vision: target not located",
         # browser-control / CDP-DOM phrasings (cdp/page/command/click|fill -> element not found)
         r"element not found", r"no element (matching|found)", r"could not find element",
         r"no (dom )?node (found|matching)"],
        "The UI target was not found by the active control strategy — typically OCR on a dark / "
        "late-rendered page, a role/label-language mismatch (e.g. Polish vs English labels), the page "
        "not loaded yet, OR (on a browser/CDP step) a login/authwall where the target simply doesn't "
        "exist. Targeting by DOM role/name via CDP is OCR-immune and language-agnostic; if a surface "
        "probe shows a login page this upgrades to not-logged-in (auth re-launch, human-gated).",
        lambda t: [
            {"id": "ensure-cdp-dom", "kind": "provision", "automatic": True,
             "uri": f"kvm://{t}/cdp/session/command/ensure",
             "label": "Bring up a CDP session so the router targets by DOM role/name (OCR-immune)."},
            {"id": "wait-page-ready", "kind": "precondition", "automatic": True,
             "uri": f"kvm://{t}/cdp/page/query/ready",
             "label": "Wait for the page to finish loading before locating the target."},
            {"id": "retry-via-act", "kind": "retry", "automatic": True,
             "uri": f"kvm://{t}/ui/command/act",
             "label": "Re-run via the self-orchestrating ui/command/act (cdp→atspi→vision, retried, verified)."},
        ],
        confidence=0.9,
    ),
    _Rule(
        "cdp-debugger-down",
        [r"debugger did not come up", r"no cdp page", r"remote-debugging-port"],
        "Chrome's debug port never bound: a bare --remote-debugging-port is silently dropped when a "
        "Chrome on the default profile already runs (the launch just forwards the URL). A dedicated "
        "user-data-dir forces a separate instance that actually opens the port.",
        lambda t: [
            {"id": "ensure-cdp-dedicated-profile", "kind": "provision", "automatic": True,
             "uri": f"kvm://{t}/cdp/session/command/ensure",
             "label": "Launch/reuse a dedicated-profile CDP Chrome that actually binds the debug port."},
        ],
        confidence=0.95,
    ),
    _Rule(
        "node-exec-timeout",
        [r"timeoutexpired", r"timed out after \d+\s*second"],
        "A single op exceeded the node's subprocess cap (~30s) — heavy OCR/portal capture, a hung CDP "
        "eval, or node contention (concurrent agents). Bound the work and keep OCR off the polling path.",
        lambda t: [
            {"id": "retry-bounded", "kind": "retry", "automatic": True,
             "uri": f"kvm://{t}/ui/command/act",
             "label": "Retry via ui/command/act (time-budgeted; cheap DOM/a11y presence, OCR only on the act)."},
            {"id": "check-node-load", "kind": "diagnostic", "automatic": False,
             "uri": f"proc://{t}/process/query/list",
             "label": "Check node load — concurrent captures/CDP can starve the portal; one agent per node."},
        ],
        confidence=0.85,
    ),
    _Rule(
        "empty-ui-target",
        [r"a target \(text/name/role\) is required", r"^text is required", r"value is required"],
        "A UI action was invoked with no locator — the planner likely emitted a textbox step with only "
        "role/name that did not map to a query, or omitted the value for a fill.",
        lambda t: [
            {"id": "repair-target", "kind": "payload", "automatic": False,
             "label": "Supply a concrete text/role/name locator (role=textbox targets the active field)."},
        ],
        confidence=0.8,
    ),
    _Rule(
        "environment-drift",
        [r"display reconfigured", r"resolution (changed|fluctuat)", r"screen size changed",
         r"monitor (added|removed|changed)", r"device.?scale.?factor"],
        "The environment changed under the flow — display reconfigured / resolution fluctuated "
        "(the 3200x1800<->1440x900 class). Cached coordinates and the chosen surface are stale; "
        "re-capture the environment profile (and re-establish the surface) before retrying, rather "
        "than acting on a moved target.",
        lambda t: [
            {"id": "recapture-environment", "kind": "discovery", "automatic": True,
             "uri": f"kvm://{t}/env/query/profile",
             "label": "Re-capture the environment profile (display/surface drifted from known-good)."},
            {"id": "resurface", "kind": "provision", "automatic": True,
             "uri": f"kvm://{t}/surface/query/current",
             "label": "Re-read the foreground surface so the router re-picks cdp/atspi/vision for the new env."},
        ],
        confidence=0.8,
    ),
    _Rule(
        "not-logged-in",
        [r"authwall", r"login required", r"sign ?in", r"not logged in", r"zaloguj", r"\b401\b"],
        "The browser session is not authenticated — a fresh CDP profile lands on the login / "
        "authwall, so the target controls (compose / post / account UI) aren't present. Re-launch "
        "the CDP Chrome on a COPY of the user's logged-in profile (the persistent-context trick).",
        lambda t: [
            {"id": "relaunch-cdp-with-auth", "kind": "provision", "automatic": False,
             "uri": f"kvm://{t}/cdp/session/command/ensure",
             "label": "Re-launch CDP Chrome with copy_from=<user chrome profile> so it's logged in (needs consent)."},
        ],
        confidence=0.8,
    ),
    _Rule(
        "stale-node-urirun",
        [r"route not found.*(capability|env[./]query[./]profile|ui[./]command[./]act|cdp[./]session|registry[./]command[./]adopt)",
         r"(capability|env[./]query[./]profile|ui[./]command[./]act|cdp[./]session).*route not found"],
        "A route from a NEWER urirun / connector is absent on the node — the node runs an older "
        "urirun, or the connector was not (re)deployed. Update urirun on the node and/or re-deploy "
        "the connector with --merge.",
        lambda t: [
            {"id": "check-node-runtime", "kind": "diagnostic", "automatic": False,
             "uri": f"node://{t}/runtime/query/info", "label": "Check the node's urirun version."},
            {"id": "check-capability", "kind": "diagnostic", "automatic": False,
             "uri": f"node://{t}/capability/query/check",
             "label": "Probe whether the scheme/route is served by an installed connector here."},
            {"id": "update-or-redeploy", "kind": "provision", "automatic": False,
             "label": "Update urirun on the node (node://…/package/command/install urirun) or re-deploy the connector."},
        ],
        categories={"NOT_FOUND"},
        confidence=0.75,
    ),
    _Rule(
        "route-not-served",
        [r"route not found", r"no available backend for"],
        "The URI's route is not live on the node — bindings were deployed without handler code, or the "
        "scheme's connector is installed but not adopted/served (or the node runs an older urirun).",
        lambda t: [
            {"id": "check-capability", "kind": "diagnostic", "automatic": False,
             "uri": f"node://{t}/capability/query/check",
             "label": "Probe whether the scheme/route is served by an installed connector here."},
            {"id": "adopt-scheme", "kind": "provision", "automatic": True,
             "uri": f"node://{t}/registry/command/adopt",
             "label": "Adopt the installed connector so its routes go live (or host deploy --merge)."},
        ],
        categories={"NOT_FOUND"},
        confidence=0.8,
    ),
]


_RULE_BY_ID = {r.id: r for r in PLAYBOOK}
_LOGIN_HINTS = ("authwall", "login", "log in", "sign in", "signin", "sign-in",
                "zaloguj", "logowanie", "/uas/", "/login")


def _is_login_surface(surface: dict | None) -> bool:
    """The foreground surface (kvm ``surface/query/current``) is a login / authwall page."""
    if not isinstance(surface, dict):
        return False
    b = surface.get("browser") or {}
    win = surface.get("window") or {}
    blob = f"{b.get('url', '')} {b.get('title', '')} {win.get('title', '')}".lower()
    return any(h in blob for h in _LOGIN_HINTS)


def _build(rule: _Rule, step: dict | None) -> dict:
    actions = rule.remediation(_target(step))
    return {"rule": rule.id, "cause": rule.cause, "confidence": rule.confidence,
            "remediation": actions,
            "autoApplicable": [a["id"] for a in actions if a.get("automatic")]}


def diagnose(error: dict, *, step: dict | None = None, routes: list[dict] | None = None,
             environment: dict | None = None, surface: dict | None = None) -> dict | None:
    """Match an error against the playbook → a structured diagnosis, or None if no rule fits.

    Returns ``{rule, cause, confidence, remediation, autoApplicable}`` where ``remediation`` is
    the list of fix actions (URIs) and ``autoApplicable`` lists the ids safe to apply unattended.
    ``environment`` (node ``env/query/profile``) FITS the remediation to the machine. ``surface``
    (node ``surface/query/current``) lets a login/authwall page UPGRADE a generic "target not
    located" to the real cause — ``not-logged-in`` — so the self-heal recommends an auth re-launch
    (human-gated) instead of futilely ensuring CDP and retrying against a login wall."""
    message = str((error or {}).get("message") or "").casefold()
    category = str((error or {}).get("category") or "")
    uri = str((step or {}).get("uri") or "")
    scheme = uri.split("://", 1)[0] if "://" in uri else ""
    login = _is_login_surface(surface)

    matched = _match_rule(message, category, scheme)
    matched = _surface_upgrade(matched, login, scheme)
    if matched is None:
        return None
    diag = _build(matched, step)
    if surface is not None:
        diag["surface"] = {"kind": surface.get("kind"), "loginDetected": login}
    return fit_to_environment(diag, environment) if environment else diag


def _match_rule(message: str, category: str, scheme: str) -> _Rule | None:
    """First playbook rule whose signature matches (or None) — first match wins by order."""
    if not message:
        return None
    return next((r for r in PLAYBOOK if r.matches(message, category, scheme)), None)


def _surface_upgrade(matched: _Rule | None, login: bool, scheme: str) -> _Rule | None:
    """On a login page, a UI failure (or no rule, on a browser/kvm step) is an AUTH problem,
    not a missing element — upgrade to not-logged-in (the more specific cause)."""
    if not login:
        return matched
    no_rule_ui_step = matched is None and scheme in ("kvm", "browser")
    weak_ui_rule = matched is not None and matched.id == "ui-target-not-located"
    return _RULE_BY_ID["not-logged-in"] if (no_rule_ui_step or weak_ui_rule) else matched


def _cdp_feasible(env: dict) -> bool:
    cs = env.get("controlStrategies") or {}
    return bool(cs.get("cdp")) or bool(env.get("cdpFeasible"))


def _controllable(env: dict) -> bool:
    cs = env.get("controlStrategies") or {}
    return bool(env.get("controllable", any(cs.values()) if cs else True))


def _mark_feasibility(remediation: list, cdp_feasible: bool, controllable: bool) -> None:
    """Tag each remediation action with whether THIS environment can support it."""
    for a in remediation:
        aid = str(a.get("id") or "")
        if "/cdp/" in str(a.get("uri") or "") or aid.startswith("ensure-cdp"):
            a["feasible"] = cdp_feasible
        elif aid in ("retry-via-act", "retry-bounded", "wait-page-ready"):
            a["feasible"] = controllable
        else:
            a["feasible"] = True


def _os_level_unreliable(env: dict) -> bool:
    """Prefer the Mutter ground-truth flag (surface_report -> env.osLevelReliable); fall back
    to the wayland+best heuristic only when reliability is unknown."""
    reliable = env.get("osLevelReliable")
    if reliable is False:
        return True
    return reliable is None and bool(env.get("wayland")) and env.get("best") in (None, "atspi", "vision")


def _maybe_escalate_surface(diagnosis: dict, env: dict, cdp_feasible: bool) -> None:
    """The three-sessions lesson as a recovery INPUT: on an unreliable Wayland os-level surface,
    a UI/input failure that has no CDP fix yet gets the WHOLE surface escalated to coordinate-free
    DOM control instead of retrying mis-mapped pixels."""
    rem = diagnosis.get("remediation") or []
    ui_failure = any(s in str(a.get("uri") or "") for a in rem for s in ("/ui/", "/cdp/", "/input/"))
    already_cdp = any(str(a.get("id") or "").startswith("ensure-cdp")
                      or ("/cdp/" in str(a.get("uri") or "") and a.get("automatic")) for a in rem)
    if ui_failure and cdp_feasible and not already_cdp and _os_level_unreliable(env):
        rem.insert(0, {"id": "escalate-surface-cdp", "kind": "provision", "automatic": True,
                       "feasible": True, "uri": f"kvm://{_target_of(rem)}/cdp/session/command/ensure",
                       "label": "OS-level pixel input is unreliable on this Wayland surface — escalate to "
                                "CDP (coordinate-free DOM control) instead of retrying os-level pixels."})
        diagnosis["surfaceEscalation"] = "os-level->cdp"


def fit_to_environment(diagnosis: dict, environment: dict) -> dict:
    """Fit a diagnosis to what the machine can ACTUALLY do: mark each remediation ``feasible``,
    escalate the surface when os-level is unreliable, recompute ``autoApplicable`` to feasible
    auto actions, and — when nothing can drive the UI — prepend an honest install/grant action."""
    cdp_feasible, controllable = _cdp_feasible(environment), _controllable(environment)
    _mark_feasibility(diagnosis.get("remediation") or [], cdp_feasible, controllable)
    _maybe_escalate_surface(diagnosis, environment, cdp_feasible)
    diagnosis["autoApplicable"] = [a["id"] for a in (diagnosis.get("remediation") or [])
                                   if a.get("automatic") and a.get("feasible", True)]
    diagnosis["environmentFit"] = {"controllable": controllable,
                                   "best": environment.get("best"), "cdpFeasible": cdp_feasible}
    if not controllable:
        diagnosis.setdefault("remediation", []).insert(0, {
            "id": "enable-ui-control", "kind": "provision", "automatic": False, "feasible": True,
            "label": "This environment cannot drive a UI: install tesseract / grant /dev/uinput, "
                     "or launch a CDP Chrome (env/query/profile shows what's missing)."})
    return diagnosis
