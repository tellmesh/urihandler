# Author: Tom Sapletta · https://tom.sapletta.com
# Integration proof + onboarding template: a brand-new desktop connector ADOPTS all three shared
# kernels (backend_registry, inputs.uinput, surfaces.cdp) by importing + configure()-injecting its
# own resolvers — and gets capability dispatch, a coordinate-exact click, and a CDP client for
# free. The whole "connector" below is ~15 lines; everything else lives in urirun source. This is
# the payoff of the extraction: a new connector re-implements NOTHING.
from __future__ import annotations

import struct

import pytest

from urirun.connectors import backend_registry as registry
try:
    from urirun.connectors.inputs import uinput
except ImportError:  # uinput surface extracted to the standalone urirun-uinput package
    uinput = None
try:
    from urirun.connectors.surfaces import cdp
except ImportError:  # cdp surface extracted to the standalone urirun-cdp package
    cdp = None
# This file's checks span the cdp + uinput surfaces; skip them when either extracted package isn't
# installed (e.g. a urirun-only CI checkout). Each surface's OWN tests live in its own package's
# tests/ dir (urirun-cdp/tests/, urirun-uinput/tests/).
pytestmark = pytest.mark.skipif(
    cdp is None or uinput is None, reason="urirun-cdp / urirun-uinput surfaces not installed")


# ─── a whole "mini desktop connector", built ONLY by adopting the kernels ──────────────
class MiniConnector:
    """Pretend this is urirun-connector-foo. It owns its platform/port/screen knowledge and
    injects them; the kernels do the rest. No websocket, no uinput ioctls, no dispatch loop here."""

    def __init__(self, *, platform="linux-wayland", port=9444, screen=(1920, 1080)):
        registry.configure(current_platform=lambda: platform)
        cdp.configure(port_resolver=lambda: port)
        uinput.configure(screen_size=lambda: screen)
        # register this connector's own backends for a capability — that's its only "registry" code
        registry.backend("foo_capture", "primary", priority=90, platforms=(platform,))(
            lambda **_: {"shot": "frame-0"})
        registry.backend("foo_capture", "fallback", priority=10)(lambda **_: {"shot": "fallback"})

    def capture(self):
        return registry.dispatch("foo_capture")          # kernel: highest-prio available wins


def test_a_new_connector_adopts_all_three_kernels(monkeypatch):
    conn = MiniConnector(platform="linux-wayland", port=9444, screen=(1920, 1080))

    # 1) backend_registry: dispatch picks the connector's platform-matched, highest-priority backend
    assert conn.capture()["shot"] == "frame-0"
    assert conn.capture()["backend"] == "primary"

    # 2) surfaces.cdp: the client's endpoint reflects the connector's injected port — zero CDP code
    assert cdp.endpoint() == "http://127.0.0.1:9444"

    # 3) inputs.uinput: a coordinate-exact click using the connector's injected screen size,
    #    proving the kernel scales pixels into ABS range without the connector touching /dev/uinput.
    abs_events = {}
    monkeypatch.setattr(uinput, "uinput_available", lambda: True)
    monkeypatch.setattr(uinput, "_create_abs", lambda: 3)
    monkeypatch.setattr(uinput._fcntl, "ioctl", lambda *a: 0)
    monkeypatch.setattr(uinput.os, "close", lambda fd: None)
    monkeypatch.setattr(uinput.time, "sleep", lambda s: None)
    monkeypatch.setattr(uinput.os, "write",
                        lambda fd, data: abs_events.__setitem__(*struct.unpack("llHHi", data)[3:5][::-1])
                        if struct.unpack("llHHi", data)[2] == uinput._EV_ABS else None)
    r = uinput.abs_click(960, 540, do_click=False, settle=0)   # screen omitted -> connector's 1920×1080
    assert r["abs"] == [uinput.ABS_RANGE // 2, uinput.ABS_RANGE // 2]   # centre of 1920×1080

    registry.configure(current_platform=lambda: "any")   # restore shared state
    cdp.configure(endpoint=lambda: "http://127.0.0.1:9222")
    uinput.configure(screen_size=lambda: (0, 0))


# ── surfaces.cdp contract: symbols the KVM connector shim needs from the generic surface ──
# A migration that removes/renames a symbol here fails BEFORE the connector reaches .201.
# (Prevents the gen-50 window_close class: cdp._evaluate→cdp.evaluate renamed, caught at gen 50
# on the live node; these tests catch it in <1s locally.)
#
# When you ADD a symbol needed from surfaces.cdp by the KVM connector: add it to _CDP_PUBLIC
# or _CDP_PRIVATE below.  When you REMOVE one from surfaces.cdp: this block fails first.

_CDP_PUBLIC = (                  # public API the shim re-exports or calls directly
    "configure",                 # cdp.py: _surface.configure(endpoint=..., env=...)
    "endpoint",                  # cdp.py re-exports; environment.py: cdp.endpoint()
    "reachable",                 # re-exports; strategies/core/environment: cdp.reachable()
    "navigate",                  # re-exports; core.py: cdp.navigate(url)
    "page_ready",                # re-exports; core.py: cdp.page_ready(timeout=...)
    "evaluate",                  # re-exports; core.py/_run: cdp.evaluate(expr)
    "CdpError",                  # re-exports; core.py/_run: except cdp.CdpError
)
_CDP_PRIVATE = ("_pages",)       # surface.py: _cdp._pages() — foreground surface detection


def test_cdp_surface_public_symbols_exist():
    from urirun.connectors.surfaces import cdp as surface
    missing = [s for s in _CDP_PUBLIC if not hasattr(surface, s)]
    assert missing == [], f"surfaces.cdp missing symbols used by KVM connector: {missing}"


def test_cdp_surface_private_symbols_exist():
    from urirun.connectors.surfaces import cdp as surface
    missing = [s for s in _CDP_PRIVATE if not hasattr(surface, s)]
    assert missing == [], f"surfaces.cdp missing private symbols used by KVM connector: {missing}"


def test_cdp_surface_configure_accepts_endpoint_and_env():
    import inspect
    from urirun.connectors.surfaces import cdp as surface
    params = inspect.signature(surface.configure).parameters
    assert "endpoint" in params, "configure() must accept 'endpoint' kwarg (wires kvm endpoint)"
    assert "env" in params, "configure() must accept 'env' kwarg (wires session_env for Chrome)"


def test_cdp_surface_callables_are_callable():
    from urirun.connectors.surfaces import cdp as surface
    for name in (*_CDP_PUBLIC[:-1], *_CDP_PRIVATE):  # all except CdpError (a class, not a fn)
        assert callable(getattr(surface, name)), f"surfaces.cdp.{name} must be callable"


def test_cdp_surface_CdpError_is_exception():
    from urirun.connectors.surfaces import cdp as surface
    assert issubclass(surface.CdpError, Exception), "CdpError must be an Exception subclass"


# ── end surfaces.cdp contract ──────────────────────────────────────────────────────────────


# ── lint_kernel_symbols ─────────────────────────────────────────────────────

from urirun.connectors.connector_lint import lint_kernel_symbols
import os as _os, tempfile as _tmpfile


def _write_py(tmp: str, name: str, src: str) -> None:
    with open(_os.path.join(tmp, name), "w") as f:
        f.write(src)


def test_lint_kernel_symbols_clean_connector_ok():
    with _tmpfile.TemporaryDirectory() as d:
        _write_py(d, "core.py", "def handler(): return 42\n")
        result = lint_kernel_symbols(d)
    assert result["ok"] is True
    assert result["violations"] == []


def test_lint_kernel_symbols_bad_direct_import_caught():
    src = "from urirun.connectors.surfaces.cdp import _evaluate\n"
    with _tmpfile.TemporaryDirectory() as d:
        _write_py(d, "core.py", src)
        result = lint_kernel_symbols(d)
    assert not result["ok"]
    assert any(v["symbol"] == "_evaluate" for v in result["violations"])


def test_lint_kernel_symbols_bad_attribute_access_caught():
    src = (
        "import urirun.connectors.surfaces.cdp as cdp\n"
        "def foo(): return cdp._evaluate('1+1')\n"
    )
    with _tmpfile.TemporaryDirectory() as d:
        _write_py(d, "core.py", src)
        result = lint_kernel_symbols(d)
    assert not result["ok"]
    assert any(v["symbol"] == "_evaluate" for v in result["violations"])


def test_lint_kernel_symbols_good_attribute_access_passes():
    src = (
        "import urirun.connectors.surfaces.cdp as cdp\n"
        "def foo(): return cdp.evaluate('1+1')\n"
    )
    with _tmpfile.TemporaryDirectory() as d:
        _write_py(d, "core.py", src)
        result = lint_kernel_symbols(d)
    assert result["ok"] is True
    assert result["violations"] == []


def test_lint_kernel_symbols_backend_registry_checked():
    src = "from urirun.connectors.backend_registry import _internal_fn\n"
    with _tmpfile.TemporaryDirectory() as d:
        _write_py(d, "core.py", src)
        result = lint_kernel_symbols(d)
    assert not result["ok"]
    assert any(v["module"].endswith("backend_registry") for v in result["violations"])


def test_lint_kernel_symbols_kvm_connector_is_clean():
    kvm_dir = _os.path.join(_os.path.dirname(__file__), "..", "..", "..",
                            "..", "urirun-connector-kvm")
    if not _os.path.isdir(kvm_dir):
        import pytest
        pytest.skip("urirun-connector-kvm not found alongside urirun")
    result = lint_kernel_symbols(kvm_dir)
    violations = result["violations"]
    assert not violations, (
        f"urirun-connector-kvm uses {len(violations)} kernel symbol(s) absent from contract:\n"
        + "\n".join(f"  {v['file']}:{v['line']} {v['module']}.{v['symbol']}" for v in violations)
    )


def test_lint_kernel_symbols_scanned_count_matches_files():
    with _tmpfile.TemporaryDirectory() as d:
        _write_py(d, "a.py", "x = 1\n")
        _write_py(d, "b.py", "y = 2\n")
        result = lint_kernel_symbols(d)
    assert result["scanned"] == 2


def test_fleet_kernel_symbols_all_connectors_clean():
    """Fleet gate: no connector in ~/github/if-uri/urirun-connector-* may call a kernel symbol
    absent from the contract. Skipped in CI where the fleet checkout isn't present."""
    import glob
    fleet_glob = _os.path.join(_os.path.expanduser("~"), "github", "if-uri", "urirun-connector-*")
    dirs = sorted(glob.glob(fleet_glob))
    if not dirs:
        import pytest
        pytest.skip("urirun-connector-* repos not found (fleet not checked out)")
    all_violations: list[dict] = []
    for pkg_dir in dirs:
        r = lint_kernel_symbols(pkg_dir)
        for v in r["violations"]:
            all_violations.append({**v, "connector": _os.path.basename(pkg_dir)})
    assert not all_violations, (
        f"{len(all_violations)} kernel contract violation(s) across {len(dirs)} connectors:\n"
        + "\n".join(
            f"  {v['connector']}/{v['file']}:{v['line']} "
            f"{v['module'].split('.')[-1]}.{v['symbol']}"
            for v in all_violations
        )
    )


def test_injected_platform_gates_a_connectors_backend():
    # a connector registers a wayland-only backend + a cross-platform fallback; the injected
    # platform resolver decides which one dispatch picks — the gating the kernel provides for free.
    registry.backend("bar_act", "wayland", priority=90, platforms=("linux-wayland",))(lambda **_: {"v": "wl"})
    registry.backend("bar_act", "any", priority=10)(lambda **_: {"v": "any"})
    try:
        registry.configure(current_platform=lambda: "linux-wayland")
        assert registry.dispatch("bar_act")["v"] == "wl"     # platform matches -> specific wins
        registry.configure(current_platform=lambda: "macos")
        assert registry.dispatch("bar_act")["v"] == "any"    # gated out -> cross-platform fallback
    finally:
        registry.configure(current_platform=lambda: "any")
