# Back-compat shim — moved to urirun_twin.twin_store (Phase 5 twin extraction).
import sys as _sys
from urirun_twin import twin_store as _moved
_sys.modules[__name__] = _moved
