from urirun.host import service_control


def test_service_restart_argv_systemd_payload_unit() -> None:
    argv, meta = service_control.service_restart_argv(
        {"manager": "systemd", "unit": "custom.service"},
        service="chat",
        env_prefix="URIRUN_CHAT",
        default_unit="urirun-service-chat.service",
    )

    assert argv == ["systemctl", "--user", "restart", "custom.service"]
    assert meta == {"manager": "systemd", "unit": "custom.service"}


def test_service_restart_argv_env_command(monkeypatch) -> None:
    monkeypatch.setenv("URIRUN_CHAT_RESTART_CMD", "svc restart 'chat service'")

    argv, meta = service_control.service_restart_argv(
        {},
        service="chat",
        env_prefix="URIRUN_CHAT",
        default_unit="urirun-service-chat.service",
    )

    assert argv == ["svc", "restart", "chat service"]
    assert meta == {"manager": "command", "source": "URIRUN_CHAT_RESTART_CMD"}


def test_chat_service_restart_argv_builds_port_replace_command(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("URIRUN_CHAT_HOST", "0.0.0.0")
    monkeypatch.setenv("URIRUN_CHAT_PORT", "9001")

    argv, meta = service_control.chat_service_restart_argv(
        str(tmp_path),
        "/tmp/host.db",
        "/tmp/mesh.yaml",
        ["lenovo=http://192.168.1.10:8765"],
        "token-1",
        "identity-1",
        {"command": "urirun-service-chat", "forcePortKill": True},
    )

    assert argv[:6] == [
        "urirun-service-chat",
        "restart",
        "--project",
        str(tmp_path.resolve()),
        "--host",
        "0.0.0.0",
    ]
    assert "--port" in argv
    assert "9001" in argv
    assert "--force-replace" in argv
    assert meta == {
        "manager": "port-replace",
        "port": 9001,
        "commandSource": "urirun-service-chat",
    }


def test_schedule_restart_command_spawns_detached_process(monkeypatch) -> None:
    calls = []

    class _P:
        pass

    monkeypatch.setattr(
        service_control.subprocess,
        "Popen",
        lambda argv, **kwargs: calls.append((argv, kwargs)) or _P(),
    )

    result = service_control.schedule_restart_command(
        ["systemctl", "--user", "restart", "x.service"],
        {"delaySeconds": 0.01},
        {"manager": "systemd"},
    )

    assert result["ok"] is True
    assert result["scheduled"] is True
    assert result["command"] == ["systemctl", "--user", "restart", "x.service"]
    assert calls
    assert calls[0][1]["start_new_session"] is True


def test_port_holder_pids_parses_ss_output(monkeypatch) -> None:
    sample = (
        'LISTEN 0 5 0.0.0.0:8194 0.0.0.0:* users:(("urirun",pid=4242,fd=3))\n'
        'LISTEN 0 4096 0.0.0.0:8788 0.0.0.0:* users:(("python",pid=99,fd=7))\n'
    )

    class _R:
        stdout = sample

    monkeypatch.setattr(service_control.subprocess, "run", lambda *a, **k: _R())

    assert service_control.port_holder_pids(8194) == [4242]
    assert service_control.port_holder_pids(8788) == [99]
    assert service_control.port_holder_pids(9999) == []


def test_is_android_node_process_matches_service_names() -> None:
    assert service_control.is_android_node_process(
        1,
        process_cmdline_fn=lambda pid: "python -m urirun_service_android_node.core serve",
    )
    assert service_control.is_android_node_process(
        2,
        process_cmdline_fn=lambda pid: "/venv/bin/urirun-android-node serve --port 8195",
    )
    assert not service_control.is_android_node_process(
        3,
        process_cmdline_fn=lambda pid: "python other_server.py",
    )


def test_free_port_from_matching_processes_refuses_unrelated_holder() -> None:
    killed = []

    result = service_control.free_port_from_matching_processes(
        8196,
        force=False,
        emit=False,
        is_target=lambda pid: pid == 11,
        event_prefix="test",
        port_holder_pids_fn=lambda port: [22],
        process_cmdline_fn=lambda pid: "python other_server.py",
        kill_fn=lambda pid, sig: killed.append((pid, sig)),
        getpid_fn=lambda: 999,
        sleep_fn=lambda seconds: None,
    )

    assert result["ok"] is False
    assert result["targets"] == []
    assert result["skipped"] == [{"pid": 22, "cmdline": "python other_server.py"}]
    assert killed == []


def test_free_port_from_old_dashboard_kills_only_matching_process() -> None:
    live = {111, 222}
    killed = []

    def kill(pid, sig):
        killed.append(pid)
        live.discard(pid)

    service_control.free_port_from_old_dashboard(
        8194,
        is_dashboard_process_fn=lambda pid: pid == 111,
        port_holder_pids_fn=lambda port: sorted(live),
        kill_fn=kill,
        getpid_fn=lambda: 999,
        sleep_fn=lambda seconds: None,
        emit_fn=lambda *a, **k: None,
    )

    assert killed == [111]
    assert live == {222}
