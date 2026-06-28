from __future__ import annotations

import base64
import tempfile
from pathlib import Path

from urirun.node._artifacts import (
    _artifact_extension,
    _decode_base64_artifact,
    materialize_base64_artifacts,
)

# Must be >= 4096 chars when base64-encoded (≈ 3072 bytes raw)
_PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"\x00" * 3100
_JPEG_HEADER = b"\xff\xd8\xff" + b"\x00" * 3100
_GIF_HEADER = b"GIF89a" + b"\x00" * 3100


# ─── _artifact_extension ─────────────────────────────────────────────────────

def test_extension_from_mime_png():
    ext, mime = _artifact_extension(b"x", "image/png")
    assert ext == ".png"
    assert mime == "image/png"


def test_extension_from_mime_jpeg():
    ext, mime = _artifact_extension(b"x", "image/jpeg")
    assert ext == ".jpg"
    assert mime == "image/jpeg"


def test_extension_from_mime_with_charset():
    ext, mime = _artifact_extension(b"x", "image/png; charset=utf-8")
    assert ext == ".png"


def test_extension_detected_from_magic_png():
    ext, mime = _artifact_extension(_PNG_HEADER)
    assert ext == ".png"
    assert mime == "image/png"


def test_extension_detected_from_magic_jpeg():
    ext, mime = _artifact_extension(_JPEG_HEADER)
    assert ext == ".jpg"


def test_extension_detected_from_magic_gif():
    ext, mime = _artifact_extension(_GIF_HEADER)
    assert ext == ".gif"


def test_extension_unknown_binary():
    ext, mime = _artifact_extension(b"\x00\x01\x02")
    assert ext == ".bin"


# ─── _decode_base64_artifact ─────────────────────────────────────────────────

def test_decode_plain_base64():
    payload = base64.b64encode(_PNG_HEADER).decode()
    result = _decode_base64_artifact(payload)
    assert result is not None
    raw, mime = result
    assert raw[:8] == _PNG_HEADER[:8]
    assert mime is None


def test_decode_data_url():
    payload = "data:image/png;base64," + base64.b64encode(_PNG_HEADER).decode()
    result = _decode_base64_artifact(payload)
    assert result is not None
    raw, mime = result
    assert mime == "image/png"


def test_decode_too_short_returns_none():
    short = base64.b64encode(b"hi").decode()
    assert _decode_base64_artifact(short) is None


def test_decode_invalid_base64_returns_none():
    assert _decode_base64_artifact("not!!base64@@content") is None


# ─── materialize_base64_artifacts ────────────────────────────────────────────

def test_materialize_replaces_large_png():
    with tempfile.TemporaryDirectory() as tmpdir:
        data = {"screenshot": base64.b64encode(_PNG_HEADER).decode()}
        out, artifacts = materialize_base64_artifacts(data, artifact_dir=tmpdir, hint="screen")
        assert "artifactPath" in out["screenshot"]
        assert Path(out["screenshot"]["artifactPath"]).exists()
        assert len(artifacts) == 1
        assert artifacts[0]["mime"] == "image/png"


def test_materialize_replaces_png_base64_capture_field():
    with tempfile.TemporaryDirectory() as tmpdir:
        data = {"result": {"value": {"kind": "screenshot", "pngBase64": base64.b64encode(_PNG_HEADER).decode()}}}
        out, artifacts = materialize_base64_artifacts(data, artifact_dir=tmpdir, hint="screen")
        ref = out["result"]["value"]["pngBase64"]
        assert "artifactPath" in ref
        assert Path(ref["artifactPath"]).exists()
        assert len(artifacts) == 1
        assert artifacts[0]["fields"] == ["screen.result.value.pngBase64"]


def test_materialize_deduplicates_identical_content():
    with tempfile.TemporaryDirectory() as tmpdir:
        encoded = base64.b64encode(_PNG_HEADER).decode()
        data = {"png": encoded, "screenshot": encoded}
        out, artifacts = materialize_base64_artifacts(data, artifact_dir=tmpdir, hint="x")
        # Same SHA256 → one artifact, two references
        assert len(artifacts) == 1
        assert out["png"]["sha256"] == out["screenshot"]["sha256"]


def test_materialize_ignores_non_artifact_keys():
    with tempfile.TemporaryDirectory() as tmpdir:
        encoded = base64.b64encode(_PNG_HEADER).decode()
        data = {"text": "hello", "png": encoded, "nested": {"image": encoded}}
        out, artifacts = materialize_base64_artifacts(data, artifact_dir=tmpdir, hint="x")
        assert out["text"] == "hello"
        assert "artifactPath" in out["png"]


def test_materialize_walks_nested_lists():
    with tempfile.TemporaryDirectory() as tmpdir:
        encoded = base64.b64encode(_PNG_HEADER).decode()
        data = {"frames": [{"screenshot": encoded}]}
        out, artifacts = materialize_base64_artifacts(data, artifact_dir=tmpdir, hint="frames")
        assert "artifactPath" in out["frames"][0]["screenshot"]


def test_materialize_passthrough_when_not_base64():
    with tempfile.TemporaryDirectory() as tmpdir:
        data = {"name": "myvalue", "count": 42}
        out, artifacts = materialize_base64_artifacts(data, artifact_dir=tmpdir, hint="x")
        assert out == data
        assert artifacts == []
