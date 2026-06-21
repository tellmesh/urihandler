"""Back-compat shim — moved to urirun.runtime.v2_adopt. Import from there in new code."""
import sys as _sys
from urirun.runtime import v2_adopt as _moved

if __name__ == "__main__":
    _sys.exit(_moved.main() if hasattr(_moved, "main") else 0)
else:
    _sys.modules[__name__] = _moved
