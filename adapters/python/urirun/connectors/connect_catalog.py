# Back-compat shim — moved to urirun-connectors-toolkit (urirun_connectors_toolkit.connect_catalog).
import sys as _sys
from urirun_connectors_toolkit import connect_catalog as _moved
_sys.modules[__name__] = _moved
