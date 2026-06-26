# Back-compat shim — moved to urirun_twin.reversible (Phase 5 twin extraction).
import sys as _sys
from urirun_twin import reversible as _moved
_sys.modules[__name__] = _moved
