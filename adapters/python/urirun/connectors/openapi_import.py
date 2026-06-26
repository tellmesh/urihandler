# Back-compat shim — moved to urirun-connectors-toolkit (urirun_connectors_toolkit.openapi_import).
import sys as _sys
from urirun_connectors_toolkit import openapi_import as _moved
_sys.modules[__name__] = _moved
