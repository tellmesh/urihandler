# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Route contracts for urirun connectors — the kernel piece (stable, shared, LLM-off-limits).

A connector's input schema is derived from each ``@conn.handler`` signature, but the OUTPUT
shape, the effect class (query/command), reversibility and the error taxonomy are today only
*convention* — emergent from scattered ``return`` statements that nothing pins. An LLM editing a
handler has nothing to anchor to and drifts.

This module makes the contract a declared entity, joined to the handler BY ROUTE KEY (the same key
``@conn.handler`` already uses — zero duplication):

* ``Contract``            — the canonical, versioned declaration (lives in the connector, LLM-edited).
* ``conform(contracts)``  — the conformance gate (CI oracle): effect↔verb agree, a reversible
                            command names an inverse that EXISTS, golden examples satisfy in/out, and
                            — the strongest check — an example's ``inverse.args`` satisfy the INPUT
                            schema of the inverse route (a broken rollback fails declaratively in CI,
                            not at runtime during the actual rollback).
* ``attach_contracts``    — joins contracts onto live bindings by route key so ``conn.bindings()``
                            carries output shape + examples (the model the LLM planner needs to chain
                            steps and to know a result may come back ``degraded``).
* ``validate_output``     — schema-check one envelope against ``out`` (for runtime/CI enforcement).

Schema dialect (a tiny JSON-schema subset that fits in an LLM context — the same dict used for
inputs): leaf tokens ``"str" | "int" | "bool" | "obj" | "list" | "any"``; ``"?T"`` optional/nullable;
``"const:X"`` exact value (``true``/``false``/ints parsed); ``"enum:a|b|c"``; nested ``dict`` = object
schema (extra keys allowed — additive/forward-compatible); ``{"oneOf": [schema, ...]}``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

try:  # the error taxonomy a contract may declare must be real RemediationClass values
    from urirun_contracts import RemediationClass
    _REMEDIATION_CLASSES = frozenset(m.value for m in RemediationClass)
except Exception:  # noqa: BLE001 - contracts pkg optional at import time
    _REMEDIATION_CLASSES = frozenset()


@dataclass(frozen=True)
class Contract:
    """One route's canonical contract. The URI is the stable identity; this is its versioned axis."""

    version: str = "v1"
    effect: str = "query"                       # "query" | "command"
    reversible: bool = False                    # commands only; if True, inverse_route MUST be declared
    inverse_route: str = ""                     # connector-local path, e.g. "window/command/restore"
    inp: dict = field(default_factory=dict)     # schema-subset of the payload (same dict as inputs)
    out: dict = field(default_factory=dict)     # schema-subset of the ok-envelope (oneOf allowed)
    errors: tuple[str, ...] = ()                # RemediationClass values this route may emit
    examples: tuple[dict, ...] = ()             # golden {payload, result} — conformance fixtures + few-shot


# ── schema-subset validator ──────────────────────────────────────────────────

def _parse_const(token: str) -> Any:
    if token == "true":
        return True
    if token == "false":
        return False
    if token.lstrip("-").isdigit():
        return int(token)
    return token


def _leaf_ok(token: str, value: Any) -> bool:
    if token.startswith("?"):
        return value is None or _leaf_ok(token[1:], value)
    if token.startswith("const:"):
        return value == _parse_const(token[6:])
    if token.startswith("enum:"):
        return value in token[5:].split("|")
    checkers = {
        "str": lambda v: isinstance(v, str),
        "int": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "bool": lambda v: isinstance(v, bool),
        "obj": lambda v: isinstance(v, dict),
        "list": lambda v: isinstance(v, list),
        "any": lambda v: True,
    }
    return checkers.get(token, lambda v: False)(value)


def check(schema: Any, value: Any, where: str) -> None:
    """Assert ``value`` satisfies ``schema`` (raises AssertionError with a located message)."""
    if isinstance(schema, dict):
        if "oneOf" in schema:
            errs = []
            for i, alt in enumerate(schema["oneOf"]):
                try:
                    check(alt, value, f"{where}|oneOf[{i}]")
                    return
                except AssertionError as exc:
                    errs.append(str(exc))
            raise AssertionError(f"{where}: matched none of oneOf -> {errs}")
        assert isinstance(value, dict), f"{where}: expected object, got {type(value).__name__}"
        for key, spec in schema.items():
            if key not in value:
                if isinstance(spec, str) and spec.startswith("?"):
                    continue
                raise AssertionError(f"{where}: missing required key {key!r}")
            check(spec, value[key], f"{where}.{key}")
        return
    assert _leaf_ok(schema, value), f"{where}: {value!r} does not satisfy {schema!r}"


def validate_output(contract: Contract, env: dict, *, where: str = "output") -> None:
    """Validate an ok-envelope against the contract's ``out`` (no-op when out is empty)."""
    if contract.out:
        check(contract.out, env, where)


# ── conformance gate ──────────────────────────────────────────────────────────

def conform(contracts: dict[str, Contract]) -> None:
    """The CI oracle. Raises AssertionError on the first violation; returns None when all pass."""
    for route, c in contracts.items():
        assert c.effect in ("query", "command"), f"{route}: bad effect {c.effect!r}"
        # 1) effect class agrees with the URI verb — convention becomes ENFORCED
        assert ("/query/" in route) == (c.effect == "query"), \
            f"{route}: effect {c.effect!r} contradicts the URI verb"
        # 2) a reversible command must name an inverse that EXISTS
        if c.reversible:
            assert c.effect == "command", f"{route}: only commands can be reversible"
            assert c.inverse_route in contracts, \
                f"{route}: inverse_route {c.inverse_route!r} is not a declared contract"
        # 3) declared errors must be real RemediationClass values (when the taxonomy is importable)
        for cls in c.errors:
            assert (not _REMEDIATION_CLASSES) or cls in _REMEDIATION_CLASSES, \
                f"{route}: error {cls!r} is not a RemediationClass value"
        # 4) golden examples actually satisfy in/out
        for i, ex in enumerate(c.examples):
            check(c.inp, ex.get("payload", {}), f"{route} examples[{i}].payload")
            check(c.out, ex.get("result", {}), f"{route} examples[{i}].result")
        # 5) STRONGEST: an example's inverse.args satisfy the INPUT schema of the inverse route —
        #    a broken rollback fails here in CI, declaratively, instead of at runtime mid-rollback.
        if c.reversible:
            inv = contracts[c.inverse_route]
            for i, ex in enumerate(c.examples):
                args = (ex.get("result", {}).get("inverse") or {}).get("args", {})
                check(inv.inp, args, f"{route} examples[{i}].inverse.args -> {c.inverse_route} input")


# ── join contracts onto live bindings (the AI registry) ───────────────────────

def contract_to_dict(c: Contract) -> dict:
    d: dict[str, Any] = {
        "version": c.version, "effect": c.effect, "reversible": c.reversible,
        "input": c.inp, "output": c.out, "errors": list(c.errors), "examples": list(c.examples),
    }
    if c.reversible:
        d["inverseRoute"] = c.inverse_route
    return d


def attach_contracts(conn, contracts: dict[str, Contract]):
    """Join contracts onto the connector's live bindings BY ROUTE KEY (zero duplication).

    Mutates each matched binding's ``meta["contract"]`` so ``conn.bindings()`` / the manifest carry
    the output shape + examples — the model an LLM planner needs. Returns ``conn`` for chaining::

        conn = attach_contracts(urirun.connector("kvm", scheme="kvm"), CONTRACTS)
    """
    from urirun.v2 import decorated_bindings

    store = decorated_bindings().get("bindings", {})
    for route, c in contracts.items():
        binding = store.get(conn.uri(route))
        if binding is not None:
            binding.setdefault("meta", {})["contract"] = contract_to_dict(c)
    return conn
