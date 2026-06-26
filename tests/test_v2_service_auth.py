from __future__ import annotations

import json

from urirun import v2_service
from urirun.node import keyauth


class _Resp:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps({"ok": True, "result": {"pong": True}}).encode("utf-8")


def test_v2_service_post_signs_with_identity(monkeypatch):
    captured = {}

    def fake_sign(identity, purpose, raw):
        captured["signed"] = (identity, purpose, raw)
        return {"X-Urirun-Sig": "sig", "X-Urirun-Key": identity}

    def fake_urlopen(request, timeout=None):
        captured["headers"] = dict(request.header_items())
        captured["body"] = request.data
        return _Resp()

    monkeypatch.setenv("URIRUN_RUN_IDENTITY", "/tmp/id_ed25519")
    monkeypatch.delenv("URIRUN_RUN_TOKEN", raising=False)
    monkeypatch.setattr(v2_service.urllib.request, "urlopen", fake_urlopen)
    # v2_service uses _signer (injected via register_signer), not a keyauth module attribute
    monkeypatch.setattr(v2_service, "_signer", fake_sign)

    data, status = v2_service._post("http://node/run", {"uri": "env://node/runtime/query/health"}, 3)

    assert status == 200
    assert data["ok"] is True
    assert captured["signed"][0] == "/tmp/id_ed25519"
    assert captured["signed"][1] == keyauth.PURPOSE_RUN
    assert captured["signed"][2] == captured["body"]
    assert captured["headers"]["X-urirun-sig"] == "sig"
