# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# Single-source guard for the widget-render extraction (urirun-widgets). `urirun-widgets` is the
# sole owner of server-side widget rendering (HTML/SVG, service-view selection + summary); the host
# dashboard CONSUMES those helpers (thin HTTP handlers that import + delegate) but must never define
# its OWN COPY of them. docs/ARCHITECTURE.md: "Host ... Nie powinien definiować własnych kopii
# service_widget_html, service_widget_svg, select_service_view, service_widget_summary ani rodziny
# render*ServiceView / renderWidget*." Without this gate the third copy regrows on the first
# "quick fix in the dashboard". Same shape as check_single_source / test_routing_extractable —
# cheap, because it deletes a boundary rather than creating one.
import ast
import re
from pathlib import Path

_HOST = Path(__file__).resolve().parents[1] / "urirun" / "host"

# Owner names that belong to urirun-widgets. The host may import them, never (re)define them.
_FORBIDDEN_EXACT = {
    "service_widget_html", "service_widget_svg",
    "select_service_view", "service_widget_summary",
}
_FORBIDDEN_RE = re.compile(r"render[A-Za-z0-9_]*ServiceView$|renderWidget[A-Za-z0-9_]*$")


def _offending_defs(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in _FORBIDDEN_EXACT or _FORBIDDEN_RE.match(node.name):
                bad.append(node.name)
    return bad


def test_host_does_not_define_its_own_widget_render():
    offenders = {}
    for path in sorted(_HOST.glob("*.py")):
        defs = _offending_defs(path)
        if defs:
            offenders[path.name] = defs
    assert not offenders, (
        "host/ defines its OWN copy of widget-render owner symbols — these belong to "
        "urirun-widgets; import + delegate instead (the host keeps only thin HTTP handlers):\n  "
        + "\n  ".join(f"{f}: {names}" for f, names in offenders.items())
    )
