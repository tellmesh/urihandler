"""Back-compat shim — moved to urirun.connectors.connect_catalog. Import from there in new code."""
import sys as _sys
from urirun.connectors import connect_catalog as _moved

_sys.modules[__name__] = _moved
