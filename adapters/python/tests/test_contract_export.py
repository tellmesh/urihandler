# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""The generic exporter must work for ANY connector's contracts, not just one.

This is what makes "every connector gets the polyglot/schema/compile-time gate for free" true:
the translation is a pure function of the dialect, proven here on a SYNTHETIC contract set unrelated
to any real connector. If this holds, each connector's emitter is a one-call wrapper.
"""
from __future__ import annotations

from urirun_connectors_toolkit.contract_gate import Contract, Wire
from urirun_connectors_toolkit.contract_export import (
    neutral_document,
    schema_document,
    write_artifacts,
)
from urirun_connectors_toolkit.contract_typescript import to_typescript

# A second, made-up connector — different routes/shapes than kvm, to prove genericity.
CONTRACTS = {
    "db/query/get": Contract(
        version="v1", effect="query",
        inp={"id": "str", "fields": "?list"},
        out={"oneOf": [
            {"kind": "const:row", "id": "str", "cols": ["str"]},
            {"kind": "const:row", "missing": "const:true"},
        ]},
        errors=("not-found",),
        examples=(
            {"payload": {"id": "u1"},
             "result": {"ok": True, "kind": "row", "id": "u1", "cols": ["a", "b"]}},
        ),
    ),
    "db/command/put": Contract(
        version="v1", effect="command", reversible=True, inverse_route="db/command/put",
        inp={"id": "str", "value": "str"},
        out={"action": "const:put", "inverse": "?obj"},
        examples=(
            {"payload": {"id": "u1", "value": "x"},
             "result": {"ok": True, "action": "put",
                        "inverse": {"path": "db/command/put", "args": {"id": "u1", "value": "old"}}}},
        ),
    ),
}
WIRES = [Wire("db/query/get", "db/command/put", {"id": "id"}, note="row id → put id")]


def test_neutral_document_shape():
    doc = neutral_document(CONTRACTS, WIRES)
    assert doc["schemaVersion"] == 1
    assert set(doc["contracts"]) == {"db/query/get", "db/command/put"}
    # inverseRoute is always present (null when not reversible) — polyglot peers rely on this
    assert doc["contracts"]["db/query/get"]["inverseRoute"] is None
    assert doc["contracts"]["db/command/put"]["inverseRoute"] == "db/command/put"
    assert doc["contracts"]["db/query/get"]["inp"] == {"id": "str", "fields": "?list"}
    assert doc["wires"] == [{"producer": "db/query/get", "consumer": "db/command/put",
                             "mapping": {"id": "id"}, "note": "row id → put id"}]


def test_json_schema_export():
    doc = schema_document(CONTRACTS)
    put_in = doc["routes"]["db/command/put"]["input"]
    assert put_in["type"] == "object"
    assert put_in["properties"]["value"] == {"type": "string"}
    assert set(put_in["required"]) == {"id", "value"}
    # union output projects to a JSON-Schema combinator with both branches
    get_out = doc["routes"]["db/query/get"]["output"]
    assert "oneOf" in get_out and len(get_out["oneOf"]) == 2


def test_typescript_export():
    ts = to_typescript(CONTRACTS)
    assert "export type In_db_command_put = {" in ts
    assert '"value": string;' in ts
    assert "[k: string]: unknown;" in ts          # extra envelope keys allowed
    assert "export interface Contracts {" in ts
    assert '"db/query/get": { input: In_db_query_get; output: Out_db_query_get };' in ts


def test_write_artifacts(tmp_path):
    written = write_artifacts(CONTRACTS, WIRES, str(tmp_path))
    names = {p.rsplit("/", 1)[-1] for p in written}
    assert names == {"contracts.json", "contracts.schema.json", "contracts.d.ts"}
    assert (tmp_path / "ts" / "contracts.d.ts").exists()
