from __future__ import annotations

import ast
from pathlib import Path


def test_chat_orchestrator_does_not_define_env_enum_resolution_helpers():
    path = Path(__file__).resolve().parents[1] / "urirun" / "host" / "chat_orchestrator.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    defined = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert "_flow_route_domains" not in defined
    assert "_env_enum_inventories" not in defined
