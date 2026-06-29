from __future__ import annotations

import sys

from urirun_node import _util


def test_default_max_tokens_is_bounded(monkeypatch):
    monkeypatch.delenv("URIRUN_LLM_MAX_TOKENS", raising=False)
    monkeypatch.delenv("LLM_MAX_TOKENS", raising=False)
    assert _util._default_max_tokens() == 4096


def test_default_max_tokens_can_be_overridden(monkeypatch):
    monkeypatch.setenv("LLM_MAX_TOKENS", "2048")
    assert _util._default_max_tokens() == 2048


def test_default_max_tokens_ignores_invalid_values(monkeypatch):
    monkeypatch.setenv("URIRUN_LLM_MAX_TOKENS", "-1")
    assert _util._default_max_tokens() == 4096


def test_quiet_completion_retries_with_fewer_tokens_on_provider_limit(monkeypatch):
    calls = []

    class FakeLiteLLM:
        suppress_debug_info = False

        @staticmethod
        def completion(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                raise RuntimeError("requested up to 4096 tokens; use fewer max_tokens")
            return {"ok": True}

    monkeypatch.setitem(sys.modules, "litellm", FakeLiteLLM)
    monkeypatch.delenv("URIRUN_LLM_MAX_TOKENS", raising=False)
    monkeypatch.delenv("LLM_MAX_TOKENS", raising=False)

    assert _util.quiet_completion(model="x", messages=[]) == {"ok": True}
    assert [call["max_tokens"] for call in calls] == [4096, 1024]


def test_quiet_completion_does_not_retry_explicit_max_tokens(monkeypatch):
    calls = []

    class FakeLiteLLM:
        suppress_debug_info = False

        @staticmethod
        def completion(**kwargs):
            calls.append(kwargs)
            raise RuntimeError("requested up to 2048 tokens; use fewer max_tokens")

    monkeypatch.setitem(sys.modules, "litellm", FakeLiteLLM)

    try:
        _util.quiet_completion(model="x", messages=[], max_tokens=2048)
    except RuntimeError:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected explicit max_tokens failure")
    assert len(calls) == 1
