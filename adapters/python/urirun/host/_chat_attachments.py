from __future__ import annotations
import base64
import json
import os
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass


def _resolve_artifact_value(sr: dict) -> "dict | None":
    """Unwrap a step result to its artifact-tagged value dict, or None if not an artifact.

    Handles two shapes: mesh steps wrap value inside result.value; inprocess_fallback
    unwraps result.value into result directly (or leaves it on the top-level dict)."""
    res = sr.get("result")
    val = res.get("value") if isinstance(res, dict) else None
    if not isinstance(val, dict):
        val = res if isinstance(res, dict) else sr
    if isinstance(val, dict) and val.get("live") is False and val.get("kind"):
        return val
    return None


def _process_remote_path_entry(
    sr: dict, path_to_node: dict, path_inline: dict, path_artifact: dict
) -> None:
    node_url = str(sr.get("url") or "").removesuffix("/run")
    if not node_url or "localhost" in node_url or "127.0.0.1" in node_url:
        return
    val = _resolve_artifact_value(sr)
    if val is None:
        return
    p = str(val.get("path") or "")
    if not p:
        return
    path_to_node[p] = node_url
    png = val.get("pngBase64")
    if isinstance(png, str) and png:
        path_inline[p] = png
    elif isinstance(png, dict) and png.get("artifactPath"):
        path_artifact[p] = str(png.get("artifactPath") or "")


def _build_remote_path_maps(results: dict) -> tuple[dict, dict, dict]:
    """Build remote path maps from step results for attachment enrichment."""
    path_to_node: dict[str, str] = {}
    path_inline: dict[str, str] = {}
    path_artifact: dict[str, str] = {}
    for sr in results.values():
        if isinstance(sr, dict):
            _process_remote_path_entry(sr, path_to_node, path_inline, path_artifact)
    return path_to_node, path_inline, path_artifact


def _save_inline_attachment(att: dict, b64: str, shot_dir: str) -> bool:
    """Save base64 image to shot_dir, update att in-place. Returns True on success."""
    import base64 as _b64  # noqa: PLC0415
    import os as _os  # noqa: PLC0415
    from urllib.parse import quote as _quote  # noqa: PLC0415
    try:
        _os.makedirs(shot_dir, exist_ok=True)
        local = _os.path.join(shot_dir, _os.path.basename(str(att.get("path") or "")))
        with open(local, "wb") as _fh:
            _fh.write(_b64.b64decode(b64))
        att["path"] = local
        meta = att.get("meta")
        if isinstance(meta, dict):
            meta.pop("pngBase64", None)
        att["fileExists"] = True
        att["filePreviewUrl"] = att["previewUrl"] = f"/api/file?path={_quote(local)}"
        return True
    except Exception:  # noqa: BLE001 - fall back to remote proxy
        return False


def _resolve_attachment_preview(att, path_to_node: dict, path_inline: dict,
                                path_artifact: dict, shot_dir: str) -> None:
    """Resolve ONE attachment's preview URL: local file -> artifact copy -> inline b64 -> remote proxy.

    A step that ran on a remote node leaves its file there; the remote-proxy fallback injects a
    ``/api/file/remote?nodeUrl=...&path=...`` URL so the dashboard can display it without an SSH transfer."""
    import os as _os  # noqa: PLC0415
    from urllib.parse import quote as _quote  # noqa: PLC0415
    if not isinstance(att, dict) or att.get("fileExists") or att.get("filePreviewUrl"):
        return
    path = str(att.get("path") or "")
    if not path:
        return
    local_path = _os.path.expanduser(path)
    if _os.path.isfile(local_path):
        att["fileExists"] = True
        att["filePreviewUrl"] = att["previewUrl"] = f"/api/file?path={_quote(local_path)}"
        return
    artifact_path = path_artifact.get(path)
    if artifact_path and _os.path.isfile(_os.path.expanduser(artifact_path)):
        local = _os.path.expanduser(artifact_path)
        att["path"] = local
        att["fileExists"] = True
        att["filePreviewUrl"] = att["previewUrl"] = f"/api/file?path={_quote(local)}"
        return
    b64 = path_inline.get(path)
    if b64 and _save_inline_attachment(att, b64, shot_dir):
        return
    node_url = path_to_node.get(path)
    if node_url:
        att["fileExists"] = True
        att["filePreviewUrl"] = f"/api/file/remote?nodeUrl={_quote(node_url)}&path={_quote(path)}"
        if not att.get("previewUrl"):
            att["previewUrl"] = att["filePreviewUrl"]


def _enrich_remote_attachments(attachments: list, results: dict) -> None:
    """Set filePreviewUrl for attachments whose file lives on a remote node.

    Matches attachment paths to step-result paths via _build_remote_path_maps, then resolves each
    attachment's preview (see _resolve_attachment_preview)."""
    import os as _os  # noqa: PLC0415
    path_to_node, path_inline, path_artifact = _build_remote_path_maps(results)
    _shot_dir = _os.path.join(
        _os.path.expanduser(_os.environ.get("URIRUN_ARTIFACT_DIR", "~/.urirun/artifacts")), "screenshots")
    for att in attachments:
        _resolve_attachment_preview(att, path_to_node, path_inline, path_artifact, _shot_dir)
    # Strip large pngBase64 blobs from attachment meta regardless of capture path.
    # The image is accessible via previewUrl/filePreviewUrl; base64 in meta is redundant
    # and would be sent to the browser on every chat-history load.
    for att in attachments:
        meta = att.get("meta") if isinstance(att, dict) else None
        if isinstance(meta, dict):
            meta.pop("pngBase64", None)


def _register_step_artifacts(result: dict, db: str | None, host_db) -> int:
    """Catalog frozen-artifact step results so a mesh-routed capture gets a durable artifact
    address, not just a transient chat attachment.

    A step result tagged per the urirun.tag contract as a frozen artifact (``live=False`` with a
    ``kind`` and an on-disk ``path``) -- e.g. a screenshot from kvm://.../screen/query/capture -- is
    registered in the artifact store. Mesh-routed steps bypass _run_inprocess_connector_uri's
    register hook, so registration happens here at flow completion. Best-effort: never raises."""
    results = result.get("results") or {}
    uri_by_id = {t.get("id"): t.get("uri") for t in (result.get("timeline") or []) if isinstance(t, dict)}
    registered = 0
    for sid, sr in results.items():
        if not isinstance(sr, dict):
            continue
        val = _resolve_artifact_value(sr)
        if val is None:
            continue
        path = str(val.get("path") or "")
        if not path or not os.path.isfile(os.path.expanduser(path)):
            continue
        try:
            host_db.register_artifact(db, str(val.get("kind")), uri_by_id.get(sid) or "", path, val)
            registered += 1
        except Exception:  # noqa: BLE001 - a catalog hiccup must not fail the chat turn
            pass
    return registered
