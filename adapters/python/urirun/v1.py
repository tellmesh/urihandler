"""Back-compat shim — moved to urirun.runtime.v1. Import from there in new code."""
import sys as _sys
from urirun.runtime import v1 as _moved

if __name__ == "__main__":
    _sys.exit(_moved.main() if hasattr(_moved, "main") else 0)
else:
    _sys.modules[__name__] = _moved
