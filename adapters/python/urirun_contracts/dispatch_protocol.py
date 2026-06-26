# Shim: dispatch_protocol moved to the urirun-runtime package (Phase 5 kernel extraction).
# urirun.runtime.dispatch_protocol and `from urirun.runtime import dispatch_protocol` resolve to the real module (every symbol,
# public + private); `python -m urirun.runtime.dispatch_protocol` delegates to the real module's CLI.
import sys as _sys
if __name__ == "__main__":
    import runpy as _rp
    _rp.run_module("urirun_runtime.dispatch_protocol", run_name="__main__")
else:
    import urirun_runtime.dispatch_protocol as _m
    _sys.modules[__name__] = _m
