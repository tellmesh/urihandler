# Back-compat shim — moved to urirun-connectors-toolkit (urirun_connectors_toolkit.connector_smoke).
import sys as _sys
from urirun_connectors_toolkit import connector_smoke as _moved
_sys.modules[__name__] = _moved
