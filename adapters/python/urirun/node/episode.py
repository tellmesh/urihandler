# Back-compat shim — moved to urirun_twin.episode (Phase 5 twin extraction).
import sys as _sys
from urirun_twin import episode as _moved
_sys.modules[__name__] = _moved
