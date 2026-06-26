# Back-compat shim — moved to urirun-connectors-toolkit (urirun_connectors_toolkit.resolver).
import sys as _sys
from urirun_connectors_toolkit import resolver as _moved
_sys.modules[__name__] = _moved
