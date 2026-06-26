from __future__ import annotations

from typing import Any

_DEFAULT_MISSING_LIMIT = 50
_SIDE_EFFECT_MARKER = "/command/"


def verification_check(name: str, *, ok: bool, expected: int, actual: int, **meta: Any) -> dict[str, Any]:
    """Build one normalized verification check row for URI side-effect contracts."""
    row: dict[str, Any] = {
        "check": name,
        "ok": bool(ok),
        "expected": int(expected),
        "actual": int(actual),
    }
    row.update({key: value for key, value in meta.items() if value is not None})
    return row


def file_transfer_verification(
    *,
    contract: str,
    expected: list[str],
    uploaded: list[str],
    verified: list[str],
    mode: str,
    missing_limit: int = _DEFAULT_MISSING_LIMIT,
) -> dict[str, Any]:
    """Return the standard verification contract for file-copy style URI flows.

    `uploaded` means the remote write acknowledged the file. `verified` means the
    final contract check passed, usually a read-back sha256 or a trusted write sha.
    """
    expected_set = list(expected)
    uploaded_set = set(uploaded)
    verified_set = set(verified)
    missing = [rel for rel in expected_set if rel not in verified_set]
    checks = [
        verification_check(
            "write_ack_for_every_expected_file",
            ok=len(uploaded_set) == len(expected_set),
            expected=len(expected_set),
            actual=len(uploaded_set),
        ),
        verification_check(
            "sha256_verified_for_every_expected_file",
            ok=len(verified_set) == len(expected_set),
            expected=len(expected_set),
            actual=len(verified_set),
            mode=mode,
        ),
    ]
    return {
        "contract": contract,
        "ok": all(check["ok"] for check in checks),
        "mode": mode,
        "expectedFiles": len(expected_set),
        "uploadedFiles": len(uploaded_set),
        "verifiedFiles": len(verified_set),
        "failedFiles": len(missing),
        "missing": missing[:missing_limit],
        "truncatedMissing": max(0, len(missing) - missing_limit),
        "checks": checks,
    }


def _ok_step_ids(timeline: list) -> set:
    return {e.get("id") for e in timeline if isinstance(e, dict) and e.get("ok")}


def _plan_steps(steps: list) -> list:
    return [s for s in steps if isinstance(s, dict)]


def _side_effect_steps(plan_steps: list) -> list:
    return [s for s in plan_steps if _SIDE_EFFECT_MARKER in str(s.get("uri") or "")]


def _completed_count(steps: list, ok_ids: set) -> int:
    return sum(1 for s in steps if s.get("id") in ok_ids)


def _flow_checks(expected_n: int, completed_n: int, side_steps: list, side_ok_n: int) -> list:
    checks = [verification_check("steps_completed",
                                 ok=completed_n == expected_n,
                                 expected=expected_n, actual=completed_n)]
    if side_steps:
        checks.append(verification_check("side_effects_ok",
                                         ok=side_ok_n == len(side_steps),
                                         expected=len(side_steps), actual=side_ok_n))
    return checks


def flow_execution_verification(flow: dict, execution: dict) -> dict:
    """Auto-generated verification block for any executed flow (no explicit spec required).

    Returns named checks with expected/actual counts so operators and the urifix re-planner
    can see at a glance whether the flow completed its steps and whether side-effecting steps
    succeeded.  Used in the dashboard NL chat path where flows are generated dynamically and
    don't carry an explicit ``verification`` spec.
    """
    plan_steps = _plan_steps(flow.get("steps") or [])
    ok_ids = _ok_step_ids(execution.get("timeline") or [])
    side_steps = _side_effect_steps(plan_steps)
    expected_n = len(plan_steps)
    completed_n = _completed_count(plan_steps, ok_ids)
    side_ok_n = _completed_count(side_steps, ok_ids)
    checks = _flow_checks(expected_n, completed_n, side_steps, side_ok_n)
    overall_ok = bool(execution.get("ok")) and all(c["ok"] for c in checks)
    return {
        "contract": "flow-execution.auto",
        "ok": overall_ok,
        "expectedSteps": expected_n,
        "completedSteps": completed_n,
        "sideEffectSteps": len(side_steps),
        "sideEffectsOk": side_ok_n,
        "checks": checks,
    }
