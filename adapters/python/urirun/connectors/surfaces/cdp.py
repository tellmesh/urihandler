# Back-compat shim — the CDP surface moved to the standalone `urirun-cdp` package (urirun_cdp.cdp).
# Import from there in new code; this re-export keeps `urirun.connectors.surfaces.cdp` working.
import sys as _sys
from urirun_cdp import cdp as _moved

_sys.modules[__name__] = _moved
