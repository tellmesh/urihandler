"""Back-compat shim — moved to urirun.connectors.connector_sdk. Import from there in new code."""
import sys as _sys
from urirun.connectors import connector_sdk as _moved

_sys.modules[__name__] = _moved
