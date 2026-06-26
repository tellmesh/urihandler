# Integration-layer CLI moved to urirun.host.node_cli (Phase 5).
# This shim forwards the module identity so monkeypatches on urirun.node.node_cli
# land on the actual implementation (same sys.modules trick as v2_service.py).
import sys as _sys
from urirun.host import node_cli as _moved

if __name__ != "__main__":
    _sys.modules[__name__] = _moved
