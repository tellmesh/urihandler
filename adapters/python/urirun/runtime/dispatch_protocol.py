# Shim: dispatch_protocol is part of urirun-runtime (Phase 5 kernel extraction).
# urirun.runtime.dispatch_protocol resolves to the real module in urirun_runtime.
import sys as _sys
from urirun_runtime import dispatch_protocol as _moved
_sys.modules[__name__] = _moved
