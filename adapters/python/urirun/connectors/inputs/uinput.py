# Back-compat shim — the uinput surface moved to the standalone `urirun-uinput` package (urirun_uinput.uinput).
# Import from there in new code; this re-export keeps `urirun.connectors.inputs.uinput` working.
import sys as _sys
from urirun_uinput import uinput as _moved

_sys.modules[__name__] = _moved
