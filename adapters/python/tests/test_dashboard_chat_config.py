from __future__ import annotations

from urirun.host.dashboard_api import llm_runtime_config


def test_llm_runtime_config_reads_llm_model(monkeypatch):
    monkeypatch.delenv("URIRUN_LLM_MODEL", raising=False)
    monkeypatch.setenv("LLM_MODEL", "env/model")

    assert llm_runtime_config() == {
        "ok": True,
        "configured": True,
        "model": "env/model",
        "source": "LLM_MODEL",
    }


def test_llm_runtime_config_prefers_urirun_llm_model(monkeypatch):
    monkeypatch.setenv("URIRUN_LLM_MODEL", "urirun/model")
    monkeypatch.setenv("LLM_MODEL", "env/model")

    result = llm_runtime_config()

    assert result["configured"] is True
    assert result["model"] == "urirun/model"
    assert result["source"] == "URIRUN_LLM_MODEL"

