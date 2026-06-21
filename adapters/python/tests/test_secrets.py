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


def test_node_guard_disables_secrets_even_when_allowed(monkeypatch):
    monkeypatch.setenv("T", "v")
    # the node guard refuses secret resolution even if the policy would allow it
    with pytest.raises(PermissionError):
        secrets.fill_secrets("Bearer {getv:T}", execute=True, allow=["getv://*"], disabled=True)

    route_entry = {"config": {"method": "POST", "url": "https://api.x/a",
                              "headers": {"Authorization": "Bearer {getv:T}"}}}
    ctx = {"routeEntry": route_entry, "payload": {}, "target": "prod", "args": [], "descriptor": {}}
    with pytest.raises(PermissionError):
        _runtime.run_fetch(ctx, {"secretAllow": ["getv://T"], "secretsDisabled": True, "timeout": 5})


def _resp(payload):
    import json as _json

    class _R:
        def read(self):
            return _json.dumps(payload).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    return _R()


def test_vault_provider(monkeypatch):
    monkeypatch.setenv("VAULT_ADDR", "https://vault.example")
    monkeypatch.setenv("VAULT_TOKEN", "vt")
    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["hdr"] = {k.lower(): v for k, v in request.header_items()}.get("x-vault-token")
        return _resp({"data": {"data": {"access_token": "from-vault"}}})

    monkeypatch.setattr(secrets, "_PROVIDERS", dict(secrets._PROVIDERS))  # isolate
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    out = secrets.resolve("secret://vault/kv/ksef#access_token", execute=True, allow=["secret://vault/**"])
    assert out.reveal() == "from-vault"
    assert captured["url"] == "https://vault.example/v1/kv/data/ksef"   # Vault KV v2 path
    assert captured["hdr"] == "vt"


def test_oauth_provider_returns_cached_then_refreshes(monkeypatch):
    import json as _json
    import time
    import types

    store = {("oauth:google", "me"): _json.dumps({
        "access_token": "old", "refresh_token": "r1", "expires_at": time.time() - 10,
        "token_url": "https://oauth.example/token", "client_id": "cid"})}
    fake_keyring = types.SimpleNamespace(
        get_password=lambda s, a: store.get((s, a)),
        set_password=lambda s, a, v: store.__setitem__((s, a), v))
    monkeypatch.setitem(__import__("sys").modules, "keyring", fake_keyring)

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda request, timeout=None: _resp({"access_token": "new", "expires_in": 3600}))
    out = secrets.resolve("secret://oauth/google/me", execute=True, allow=["secret://oauth/**"])
    assert out.reveal() == "new"                                  # expired -> refreshed
    assert "new" in store[("oauth:google", "me")]                 # cached back to keyring


def test_browser_provider_refuses(monkeypatch):
    with pytest.raises(PermissionError) as exc:
        secrets.resolve("secret://browser/chrome/example.com", execute=True, allow=["secret://browser/**"])
    assert "keyring" in str(exc.value)


def test_run_fetch_secret_denied_without_allow(monkeypatch):
    monkeypatch.setenv("KSEF_TOKEN", "tok-xyz")
    route_entry = {"config": {"method": "POST", "url": "https://api.x/auth",
                              "headers": {"Authorization": "Bearer {getv:KSEF_TOKEN}"}}}
    ctx = {"routeEntry": route_entry, "payload": {}, "target": "prod", "args": [], "descriptor": {}}
    with pytest.raises(PermissionError):
        _runtime.run_fetch(ctx, {"timeout": 5})  # no secretAllow -> denied
