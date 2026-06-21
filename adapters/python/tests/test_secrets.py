"""Tests for secret:// — reference-not-value, execute-only, deny-by-default, redacted."""

from __future__ import annotations

import json

import pytest

from urirun.runtime import _runtime, secrets


def test_secretstr_is_redacted():
    s = secrets.SecretStr("sk-12345", "secret://env/TOKEN")
    assert str(s) == "****"
    assert "sk-12345" not in repr(s)
    assert s.reveal() == "sk-12345"
    assert json.dumps(secrets.redact({"auth": s, "n": 1})) == '{"auth": "****", "n": 1}'


def test_resolve_env(monkeypatch):
    monkeypatch.setenv("MY_TOKEN", "abc")
    out = secrets.resolve("getv://MY_TOKEN", execute=True, allow=["getv://*"])
    assert out.reveal() == "abc"


def test_dry_run_never_resolves():
    out = secrets.resolve("secret://keyring/svc/acct", execute=False, allow=["secret://keyring/**"])
    assert bool(out) is False
    with pytest.raises(ValueError):
        out.reveal()


def test_deny_by_default():
    with pytest.raises(PermissionError):
        secrets.resolve("getv://TOKEN", execute=True, allow=None)
    with pytest.raises(PermissionError):
        secrets.resolve("getv://TOKEN", execute=True, allow=["secret://keyring/**"])


def test_fill_secrets_dry_run_redacts(monkeypatch):
    monkeypatch.setenv("T", "secretvalue")
    assert secrets.fill_secrets("Bearer {getv:T}", execute=False) == "Bearer ****"


def test_fill_secrets_execute_injects(monkeypatch):
    monkeypatch.setenv("T", "secretvalue")
    out = secrets.fill_secrets("Bearer {getv:T}", execute=True, allow=["getv://*"])
    assert out == "Bearer secretvalue"


def test_run_fetch_injects_secret_into_header_only(monkeypatch):
    monkeypatch.setenv("KSEF_TOKEN", "tok-xyz")
    captured = {}

    class _Resp:
        status = 200

        def read(self):
            return b'{"ok": true}'   # server does NOT echo the secret

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(request, timeout=None):
        captured["auth"] = request.get_header("Authorization")
        captured["url"] = request.full_url
        return _Resp()

    monkeypatch.setattr(_runtime.urllib.request, "urlopen", fake_urlopen)
    route_entry = {"config": {
        "method": "POST", "path": "/auth", "environments": {"prod": "https://api.x"},
        "headers": {"Authorization": "Bearer {getv:KSEF_TOKEN}"},
    }}
    ctx = {"routeEntry": route_entry, "payload": {}, "target": "prod", "args": [], "descriptor": {}}
    policy = {"secretAllow": ["getv://KSEF_TOKEN"], "timeout": 5}

    result = _runtime.run_fetch(ctx, policy)
    assert captured["auth"] == "Bearer tok-xyz"          # injected into the header
    assert "tok-xyz" not in json.dumps(result)            # never in the returned surface
    assert captured["url"] == "https://api.x/auth"


def test_run_fetch_secret_denied_without_allow(monkeypatch):
    monkeypatch.setenv("KSEF_TOKEN", "tok-xyz")
    route_entry = {"config": {"method": "POST", "url": "https://api.x/auth",
                              "headers": {"Authorization": "Bearer {getv:KSEF_TOKEN}"}}}
    ctx = {"routeEntry": route_entry, "payload": {}, "target": "prod", "args": [], "descriptor": {}}
    with pytest.raises(PermissionError):
        _runtime.run_fetch(ctx, {"timeout": 5})  # no secretAllow -> denied
