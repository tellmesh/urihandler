# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Project the contract schema-subset dialect to TypeScript types (compile-time enforcement).

Companion to ``contract_jsonschema`` (runtime, JSON Schema) and ``contract_to_dict`` (MCP/A2A).
Where those enforce a contract while a program runs, this lets a TS consumer get the contract
checked by ``tsc`` BEFORE it runs: a mistyped envelope field fails to compile. Pure function of the
dialect, so EVERY connector can emit `.d.ts` from its ``CONTRACTS`` with no per-connector code.

Dialect → TypeScript:
  str→string  int/num→number  bool→boolean  obj→Record<string,unknown>  list→unknown[]  any→unknown
  "?T"            optional property  "key"?: T
  "const:X"      literal "X" (true/false → boolean literal; digits → numeric literal)
  "enum:a|b"     "a" | "b"
  {...}          object type + index signature `[k: string]: unknown` (envelope carries extra keys)
  ["T"]          T[]      {"oneOf":[...]}  A | B
"""
from __future__ import annotations

import json
from typing import Any

_LEAF = {"str": "string", "int": "number", "num": "number", "bool": "boolean",
         "obj": "Record<string, unknown>", "list": "unknown[]", "any": "unknown"}


def _const(token: str) -> str:
    if token in ("true", "false"):
        return token
    if token.lstrip("-").isdigit():
        return token  # numeric literal
    return json.dumps(token)  # quoted string literal


def _ts_object(node: dict, indent: int) -> str:
    pad = "  " * (indent + 1)
    lines = []
    for key, sub in node.items():
        optional = isinstance(sub, str) and sub.startswith("?")
        sub_t = sub[1:] if optional else sub
        q = "?" if optional else ""
        lines.append(f'{pad}{json.dumps(key)}{q}: {ts_type(sub_t, indent + 1)};')
    lines.append(f'{pad}[k: string]: unknown;')  # extra envelope keys (ok/connector/action) allowed
    return "{\n" + "\n".join(lines) + "\n" + ("  " * indent) + "}"


def _ts_token(tok: str) -> str:
    if tok.startswith("const:"):
        return _const(tok[len("const:"):])
    if tok.startswith("enum:"):
        return " | ".join(json.dumps(v) for v in tok[len("enum:"):].split("|"))
    if tok in _LEAF:
        return _LEAF[tok]
    return "unknown"


def ts_type(node: Any, indent: int = 0) -> str:
    """Map one dialect node to a TypeScript type expression."""
    if isinstance(node, dict) and set(node) == {"oneOf"}:
        return " | ".join(ts_type(b, indent) for b in node["oneOf"])
    if isinstance(node, dict):
        return _ts_object(node, indent)
    if isinstance(node, list):
        return (ts_type(node[0], indent) + "[]") if node else "unknown[]"
    tok = node[1:] if isinstance(node, str) and node.startswith("?") else node
    return _ts_token(tok) if isinstance(tok, str) else "unknown"  # "any" / unknown token


def _sanitize(route: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in route)


def to_typescript(contracts: dict) -> str:
    """Render a `.d.ts` module: ``In_<route>`` / ``Out_<route>`` types + a ``Contracts`` interface.

    ``contracts`` is ``{route: Contract}`` (the same dict a connector declares). Reads only
    ``.inp``/``.out`` so it is agnostic to where the contract came from (dataclass/JSON/proto)."""
    out = [
        "// GENERATED from a connector's CONTRACTS (dataclass) — do not hand-edit.",
        "// Same contracts as contracts.json / contracts.schema.json, as compile-time types.",
        "",
    ]
    entries = []
    for route, c in contracts.items():
        s = _sanitize(route)
        out.append(f"export type In_{s} = {ts_type(c.inp)};")
        out.append(f"export type Out_{s} = {ts_type(c.out)};")
        out.append("")
        entries.append(f'  {json.dumps(route)}: {{ input: In_{s}; output: Out_{s} }};')
    out.append("export interface Contracts {")
    out.extend(entries)
    out.append("}")
    out.append("")
    return "\n".join(out)
