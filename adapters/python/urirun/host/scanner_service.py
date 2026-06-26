from __future__ import annotations

import os
import threading
from http.server import ThreadingHTTPServer
from typing import TYPE_CHECKING, Any, Callable

from .scanner_net import (
    _ensure_tls_cert,
    _lan_host,
    _phone_scanner_external_status,
    _phone_scanner_url,
    _probe_scanner_url,
    _scanner_page_url,
    _url_host,
)
from .service_control import (
    schedule_restart_command as _schedule_restart_command,
    service_restart_argv as _service_restart_argv,
)

if TYPE_CHECKING:
    pass

_SERVICE_LOCK: threading.Lock = threading.Lock()
_SERVICE_SERVERS: dict[str, ThreadingHTTPServer] = {}
_SERVICE_THREADS: dict[str, threading.Thread] = {}


def phone_scanner_service_id(bind_host: str, port: int) -> str:
    return f"https://{bind_host}:{port}"


def ensure_phone_scanner_service(
    project: str,
    db: "str | None",
    config: "str | None" = None,
    node_urls: "list[str] | None" = None,
    token: "str | None" = None,
    identity: "str | None" = None,
    *,
    host: "str | None" = None,
    port: "int | None" = None,
    tls_cert: "str | None" = None,
    tls_key: "str | None" = None,
    serve_fn: "Callable[..., ThreadingHTTPServer]",
    startup_phone_qr_fn: "Callable[..., dict]",
    host_db_fn: "Callable[[], Any]",
) -> dict:
    bind_host = host or os.environ.get("URIRUN_PHONE_SCANNER_HOST", "0.0.0.0")
    scanner_port = int(port or os.environ.get("URIRUN_PHONE_SCANNER_PORT", "8196"))
    cert = tls_cert or os.environ.get("URIRUN_PHONE_SCANNER_TLS_CERT", "~/.urirun/certs/urirun-dashboard.crt")
    key = tls_key or os.environ.get("URIRUN_PHONE_SCANNER_TLS_KEY", "~/.urirun/certs/urirun-dashboard.key")
    cert, key = _ensure_tls_cert(cert, key)
    scanner_url = _scanner_page_url(f"https://{_url_host(_lan_host())}:{scanner_port}/scanner")
    service_id = f"https://{bind_host}:{scanner_port}"

    with _SERVICE_LOCK:
        server = _SERVICE_SERVERS.get(service_id)
        thread = _SERVICE_THREADS.get(service_id)
        if server is not None and thread is not None and thread.is_alive():
            status = "already-running"
        elif _probe_scanner_url(scanner_url):
            status = "external-running"
        else:
            server = serve_fn(
                project=project,
                db=db,
                config=config,
                host=bind_host,
                port=scanner_port,
                node_urls=node_urls,
                token=token,
                identity=identity,
                tls_cert=cert,
                tls_key=key,
                startup_qr=False,
            )
            thread = threading.Thread(target=server.serve_forever, name=f"urirun-phone-scanner-{scanner_port}", daemon=True)
            thread.start()
            _SERVICE_SERVERS[service_id] = server
            _SERVICE_THREADS[service_id] = thread
            status = "started"

    qr = startup_phone_qr_fn(
        project,
        db,
        scheme="https",
        host=bind_host,
        port=scanner_port,
        qr_url=scanner_url,
        content_prefix="Phone scanner service ready",
    )
    meta = {
        "status": status,
        "service": "phone-scanner",
        "url": scanner_url,
        "bindHost": bind_host,
        "hostIp": _lan_host(),
        "port": scanner_port,
        "tlsCert": cert,
    }
    try:
        host_db_fn().add_log(db, "service", "phone-scanner", meta)
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, **meta, "qr": qr, "message": qr.get("message")}


def restart_phone_scanner_service(
    project: str,
    db: "str | None",
    config: "str | None" = None,
    node_urls: "list[str] | None" = None,
    token: "str | None" = None,
    identity: "str | None" = None,
    payload: "dict | None" = None,
    *,
    ensure_fn: "Callable[..., dict]",
    free_port_fn: "Callable[..., dict]",
) -> dict:
    payload = payload or {}
    force_port_kill = str(payload.get("forcePortKill") or payload.get("force") or "").strip().lower() in {"1", "true", "yes", "on"}
    argv, meta = _service_restart_argv(
        payload,
        service="phone-scanner",
        env_prefix="URIRUN_PHONE_SCANNER",
        default_unit="urirun-service-scanner.service",
    )
    meta.setdefault("exampleUri", "dashboard://host/service/phone-scanner/command/restart")
    if argv:
        return _schedule_restart_command(argv, payload, meta)

    bind_host = str(payload.get("host") or os.environ.get("URIRUN_PHONE_SCANNER_HOST", "0.0.0.0"))
    scanner_port = int(payload.get("port") or os.environ.get("URIRUN_PHONE_SCANNER_PORT", "8196"))
    service_id = phone_scanner_service_id(bind_host, scanner_port)
    with _SERVICE_LOCK:
        server = _SERVICE_SERVERS.pop(service_id, None)
        thread = _SERVICE_THREADS.pop(service_id, None)

    if server is not None and thread is not None and thread.is_alive():
        def _restart() -> None:
            try:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)
            except Exception:  # noqa: BLE001
                pass
            ensure_fn(
                project,
                db,
                config,
                node_urls=node_urls,
                token=token,
                identity=identity,
                host=bind_host,
                port=scanner_port,
            )

        threading.Thread(target=_restart, name=f"urirun-phone-scanner-restart-{scanner_port}", daemon=True).start()
        return {
            "ok": True,
            "scheduled": True,
            "manager": "in-process",
            "service": "phone-scanner",
            "port": scanner_port,
            "url": _phone_scanner_url(scanner_port),
        }

    replaced = free_port_fn(scanner_port, force=force_port_kill)
    if replaced.get("holders"):
        if not replaced.get("ok") or replaced.get("remaining"):
            return {
                "ok": False,
                **meta,
                "replace": replaced,
                "reason": "port is owned by a process that was not safely replaceable; use forcePortKill only in a controlled environment",
            }
        started = ensure_fn(
            project,
            db,
            config,
            node_urls=node_urls,
            token=token,
            identity=identity,
            host=bind_host,
            port=scanner_port,
        )
        return {"ok": True, "manager": "port-replace", "restart": True, "replace": replaced, **started}

    status = _phone_scanner_external_status(scanner_port)
    if not status.get("reachable"):
        started = ensure_fn(
            project,
            db,
            config,
            node_urls=node_urls,
            token=token,
            identity=identity,
            host=bind_host,
            port=scanner_port,
        )
        return {"ok": True, "manager": "start-if-stopped", "restart": False, **started}

    return {
        "ok": False,
        **meta,
        "status": status,
        "reason": "scanner is reachable but is not managed by this dashboard process; configure a supervisor restart command",
    }
