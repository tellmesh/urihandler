"""Pure HTTP response primitives for the dashboard HTTP server.

These helpers write well-formed HTTP responses to a BaseHTTPRequestHandler
and carry no business logic — they are the lowest layer of the dashboard
stack and have no dependencies on service state or configuration.
"""
from __future__ import annotations

import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

from .html_templates import INDEX_HTML


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _html_response(handler: BaseHTTPRequestHandler, html: str = INDEX_HTML) -> None:
    body = html.encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _asset_response(handler: BaseHTTPRequestHandler, body: bytes, content_type: str) -> None:
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _js_sdk_response(handler: BaseHTTPRequestHandler, project: str) -> None:
    configured = os.environ.get("URIRUN_JS_SDK")
    roots = []
    if configured:
        roots.append(Path(configured).expanduser())
    project_path = Path(project).expanduser().resolve()
    roots.extend([
        project_path.parent / "js-urirun-com" / "urirun.js",
        project_path.parent / "js-urirun-com" / "src" / "urirun.js",
        Path("/home/tom/github/if-uri/js-urirun-com/urirun.js"),
        Path("/home/tom/github/if-uri/js-urirun-com/src/urirun.js"),
    ])
    for source in roots:
        try:
            resolved = source.expanduser().resolve()
            if resolved.is_file():
                _asset_response(handler, resolved.read_bytes(), "application/javascript; charset=utf-8")
                return
        except Exception:  # noqa: BLE001
            continue
    _json_response(handler, 404, {"ok": False, "error": "urirun JS SDK not found"})


def _read_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    return json.loads(handler.rfile.read(length).decode("utf-8") or "{}")


def _file_response(handler: BaseHTTPRequestHandler, path: str, project: str) -> None:
    import tempfile  # noqa: PLC0415
    source = Path(path).expanduser().resolve()
    allowed_roots = [
        Path(project).expanduser().resolve(),
        Path("~/.urirun").expanduser().resolve(),
        Path(os.environ.get("URIRUN_ARTIFACT_DIR", "~/.urirun/artifacts")).expanduser().resolve(),
    ]
    in_temp = source.parent == Path(tempfile.gettempdir()) and source.name.startswith("urirun-")
    if not in_temp and not any(source == root or source.is_relative_to(root) for root in allowed_roots):
        _json_response(handler, 403, {"ok": False, "error": "file is outside dashboard preview roots"})
        return
    if not source.is_file():
        _json_response(handler, 404, {"ok": False, "error": "file not found"})
        return
    mime = mimetypes.guess_type(str(source))[0] or "application/octet-stream"
    body = source.read_bytes()
    handler.send_response(200)
    handler.send_header("Content-Type", mime)
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)
