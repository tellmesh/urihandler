# Back-compat shim — moved to urirun-connectors-toolkit (urirun_connectors_toolkit.connector_scaffold).
import sys as _sys
from urirun_connectors_toolkit import connector_scaffold as _moved
_sys.modules[__name__] = _moved
