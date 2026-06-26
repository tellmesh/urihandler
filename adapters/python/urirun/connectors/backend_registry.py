# Back-compat shim — moved to urirun-connectors-toolkit (urirun_connectors_toolkit.backend_registry).
import sys as _sys
from urirun_connectors_toolkit import backend_registry as _moved
_sys.modules[__name__] = _moved
