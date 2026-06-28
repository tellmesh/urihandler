# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# SLIM-CORE GATE. The whole slim-core program rests on one invariant: a bare `import urirun` is the
# public-API facade ONLY (urirun.ok / connector / run) and must NOT pull in host / node / scanner /
# connectors / flow / twin. That invariant was an ASPIRATION (extraction_audit ratchets the import
# graph; this is the cheaper, sharper, top-level form). Without it as an executable gate, every
# future extraction can silently leave a reverse import and the core re-fattens — exactly the
# failure mode the contract `check_single_source` gate prevents on its own axis.
#
# Runs in a CLEAN subprocess because the pytest process itself imports the whole tree.
import subprocess
import sys

# The forbidden upper-layer surface. `import urirun` must load NONE of these.
_FORBIDDEN = (
    "urirun.host", "urirun_node", "urirun.node", "urirun_scanner",
    "urirun.connectors", "urirun_connector_", "urirun_flow", "urirun_twin",
)

_PROBE = (
    "import urirun, sys\n"
    f"bad = {_FORBIDDEN!r}\n"
    "leaks = sorted(m for m in sys.modules if m.startswith(bad))\n"
    "print('\\n'.join(leaks))\n"
    "raise SystemExit(1 if leaks else 0)\n"
)


def test_bare_import_urirun_stays_slim():
    """`import urirun` must stay the minimal facade — no upper-layer module loaded. A failure means
    an extraction left a reverse import into the core; fix it (lazy-import the surface, or move the
    symbol down) so `urirun` stays liftable and the slim-core split holds."""
    r = subprocess.run([sys.executable, "-c", _PROBE], capture_output=True, text=True)
    leaked = [m for m in r.stdout.split() if m]
    assert r.returncode == 0, (
        "bare `import urirun` loaded upper-layer module(s) — slim-core violation:\n  "
        + "\n  ".join(leaked or [r.stderr.strip()])
        + "\nThe core must not import host/node/scanner/connectors/flow/twin at import time."
    )
