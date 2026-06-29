from __future__ import annotations

import sys as _sys

from ._shim import load_connector_module as _load_connector_module

_moved = _load_connector_module("artifacts_admin")
globals().update(_moved.__dict__)
_sys.modules[__name__] = _moved
