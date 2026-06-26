# Back-compat shim — moved to urirun-connectors-toolkit (urirun_connectors_toolkit.declarative).
import sys as _sys
from urirun_connectors_toolkit import declarative as _moved
_sys.modules[__name__] = _moved
