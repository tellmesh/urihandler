from __future__ import annotations

import ast
from pathlib import Path


def test_chat_orchestrator_does_not_define_screen_capability_helpers():
    path = Path(__file__).resolve().parents[1] / "urirun" / "host" / "chat_orchestrator.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    defined = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    for moved in (
        "_collect_target_names",
        "_try_ensure_kvm_for_node",
    ):
        assert moved not in defined
    # These wrappers may stay because they bind host-local dependencies for the chat path.
    assert "_try_auto_ensure_screen_capture" in defined
    assert "_is_host_only_with_local_kvm" in defined
