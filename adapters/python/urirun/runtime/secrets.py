# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.

"""secret:// — address credentials by *reference*, never by value.

A URI carries a reference to a secret (``secret://keyring/ksef/{nip}``,
``getv://OPENROUTER_API_KEY``); the value is resolved **lazily, only in
``--execute``**, behind a deny-by-default policy, and injected at the executor
boundary (env / header / stdin). Resolved values are wrapped in ``SecretStr`` so
every serialized surface (registry, route table, error store, logs, MCP/A2A)
prints ``****`` instead of the secret.

Providers: ``env`` / ``getv`` (process env), ``dotenv`` (a .env file), ``keyring``
(OS credential store). ``vault`` / ``oauth`` / ``browser`` are reserved (§2).
"""

from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path
from typing import Any

SECRET_PLACEHOLDER = re.compile(r"\{(secret|getv):([^{}]*)\}")


class SecretStr:
    """An opaque secret value. ``str``/``repr``/JSON show ``****``; ``reveal()``
    returns the plaintext (call only at the injection boundary)."""

    __slots__ = ("_value", "_ref")

    def __init__(self, value: str | None, ref: str):
        self._value = value
        self._ref = ref

    def reveal(self) -> str:
        if self._value is None:
            raise ValueError(f"secret not resolved (dry-run): {self._ref}")
        return self._value

    @property
    def ref(self) -> str:
        return self._ref

    def __str__(self) -> str:  # noqa: D105
        return "****"

    def __repr__(self) -> str:  # noqa: D105
        return f"SecretStr(ref={self._ref!r})"

    def __bool__(self) -> bool:  # noqa: D105
        return self._value is not None


def redact(value: Any) -> Any:
    """Recursively replace SecretStr (and obvious secret refs) with ``****``."""
    if isinstance(value, SecretStr):
        return "****"
    if isinstance(value, dict):
        return {key: redact(val) for key, val in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


# --- providers -------------------------------------------------------------

def _provider_env(location: str, field: str | None) -> str:
    name = field or location
    if name not in os.environ:
        raise KeyError(f"env var not set: {name}")
    return os.environ[name]


def _provider_dotenv(location: str, field: str | None) -> str:
    if not field:
        raise ValueError("dotenv secret needs a #NAME fragment")
    for line in Path(location).expanduser().read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        if key.strip() == field:
            return val.strip().strip('"').strip("'")
    raise KeyError(f"{field} not found in {location}")


def _provider_keyring(location: str, field: str | None) -> str:
    try:
        import keyring
    except ImportError as exc:
        raise RuntimeError("keyring provider needs the 'keyring' package (pip install keyring)") from exc
    service, _, account = location.partition("/")
    value = keyring.get_password(service, account or field or "")
    if value is None:
        raise KeyError(f"no keyring entry for {service}/{account}")
    return value


_PROVIDERS = {"env": _provider_env, "getv": _provider_env, "dotenv": _provider_dotenv, "keyring": _provider_keyring}


def _parse_ref(ref: str) -> tuple[str, str, str | None]:
    if ref.startswith("getv://"):
        return ("env", ref[len("getv://"):], None)
    if not ref.startswith("secret://"):
        raise ValueError(f"not a secret reference: {ref}")
    rest = ref[len("secret://"):]
    location, _, field = rest.partition("#")
    provider, _, loc = location.partition("/")
    return (provider, loc, field or None)


def allowed(ref: str, allow: list[str] | None) -> bool:
    """Deny-by-default: a secret is resolvable only if it matches the allow-list."""
    if not allow:
        return False
    return any(fnmatch.fnmatch(ref, pattern) for pattern in allow)


def resolve(ref: str, *, execute: bool, allow: list[str] | None = None) -> SecretStr:
    if execute and not allowed(ref, allow):
        raise PermissionError(f"secret denied by policy (add it to --secret-allow): {ref}")
    if not execute:
        return SecretStr(None, ref)  # dry-run: reference only, never the value
    provider, location, field = _parse_ref(ref)
    func = _PROVIDERS.get(provider)
    if func is None:
        raise ValueError(f"unknown secret provider '{provider}' in {ref}")
    return SecretStr(func(location, field), ref)


def fill_secrets(text: str, *, execute: bool, allow: list[str] | None = None) -> str:
    """Replace ``{secret:...}`` / ``{getv:...}`` in a string with the value
    (execute) or ``****`` (dry-run). Run payload templating first so nested
    ``{param}`` slots are already filled."""
    def repl(match: re.Match) -> str:
        ref = f"{match.group(1)}://{match.group(2)}"
        if not execute:
            return "****"
        return resolve(ref, execute=True, allow=allow).reveal()

    return SECRET_PLACEHOLDER.sub(repl, str(text))


def has_secret(text: str) -> bool:
    return bool(SECRET_PLACEHOLDER.search(str(text)))
