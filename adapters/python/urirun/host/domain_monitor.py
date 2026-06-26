# Back-compat shim — domain monitor host service moved to urirun-connector-domain-monitor.
# Import from urirun_connector_domain_monitor.host_service in new code.
import sys as _sys
from urirun_connector_domain_monitor import host_service as _moved
_sys.modules[__name__] = _moved
