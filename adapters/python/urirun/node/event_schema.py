# Back-compat shim — moved to urirun_contracts.event_schema (Phase 5).
import sys as _sys
from urirun_contracts import event_schema as _moved
_sys.modules[__name__] = _moved
