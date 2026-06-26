# Back-compat shim — the CDP surface moved to the standalone `urirun-cdp` package (urirun_cdp.cdp).
# Import from there in new code; this re-export keeps `urirun.connectors.surfaces.cdp` working.
# When `urirun_cdp` is not installed the module stays importable but reports CDP as unavailable.
import sys as _sys

try:
    from urirun_cdp import cdp as _moved
    _sys.modules[__name__] = _moved
except ImportError:
    # urirun_cdp not installed — provide a minimal stub so the kvm connector can still load
    # and fall back to non-CDP capture backends (portal, grim, mss, scrot, …).
    class CdpError(RuntimeError):
        pass

    def configure(**_kw: object) -> None:
        pass

    def endpoint() -> str:
        return "http://127.0.0.1:9222"

    def reachable() -> bool:
        return False

    def navigate(url: str, **_kw: object) -> dict:
        raise CdpError("urirun-cdp not installed")

    def page_ready(**_kw: object) -> dict:
        raise CdpError("urirun-cdp not installed")

    def evaluate(js: str, **_kw: object) -> object:
        raise CdpError("urirun-cdp not installed")
