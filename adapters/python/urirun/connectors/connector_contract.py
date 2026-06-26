# Back-compat shim — moved to urirun-connectors-toolkit (urirun_connectors_toolkit.connector_contract).
import sys as _sys
from urirun_connectors_toolkit import connector_contract as _moved
_sys.modules[__name__] = _moved
