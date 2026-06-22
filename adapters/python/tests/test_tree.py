"""urirun.runtime.tree: render a registry/bindings as a scheme->host->path->{uri} tree."""
from urirun import v2
from urirun.runtime import tree

URIS = ["task://host/tickets/query/list", "task://host/ticket/command/create",
        "planfile://host/dsl/command/run"]
DOC = {"version": v2.VERSION, "bindings": {u: {"uri": u} for u in URIS}}


def test_tree_from_bindings_shape():
    t = tree.build(DOC)["uri_tree"]
    assert t["task"]["host"]["tickets"]["query"]["list"] == {"uri": "task://host/tickets/query/list"}
    assert t["planfile"]["host"]["dsl"]["command"]["run"]["uri"] == "planfile://host/dsl/command/run"


def test_tree_from_registry_equals_bindings():
    assert tree.build(DOC) == tree.build(v2.compile_registry(DOC))


def test_collect_uris_handles_list_and_dict():
    assert set(tree.collect_uris(DOC)) == set(URIS)
    assert set(tree.collect_uris({"bindings": [{"uri": u} for u in URIS]})) == set(URIS)


def test_singular_and_plural_stay_distinct():
    t = tree.build({"bindings": {"task://host/ticket/query/show": {}, "task://host/tickets/query/list": {}}})["uri_tree"]
    assert "ticket" in t["task"]["host"] and "tickets" in t["task"]["host"]
