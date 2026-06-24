from __future__ import annotations

from urirun.host import host_db


def test_delete_logs_filters_stream_and_event(tmp_path):
    db = str(tmp_path / "host.db")
    chat_message = host_db.add_log(db, "chat", "message", {"role": "system"})
    chat_audit = host_db.add_log(db, "chat", "ask", {"prompt": "keep"})
    service_message = host_db.add_log(db, "service", "message", {"event": "keep"})

    deleted = host_db.delete_logs(
        db,
        [chat_message["id"], chat_audit["id"], service_message["id"]],
        stream="chat",
        event="message",
    )

    assert deleted == 1
    remaining = {item["id"] for item in host_db.recent_logs(db, limit=10)}
    assert chat_message["id"] not in remaining
    assert chat_audit["id"] in remaining
    assert service_message["id"] in remaining


def test_delete_artifacts_by_ids(tmp_path):
    db = str(tmp_path / "host.db")
    first = host_db.register_artifact(db, "camera-scan", "scanner://one", "/tmp/one.jpg")
    second = host_db.register_artifact(db, "document-pdf", "document://two", "/tmp/two.pdf")

    rows = host_db.artifacts_by_ids(db, [first["id"], "missing"])
    deleted = host_db.delete_artifacts(db, [first["id"], "missing"])

    assert [row["id"] for row in rows] == [first["id"]]
    assert deleted == 1
    remaining = {item["id"] for item in host_db.list_artifacts(db, limit=10)}
    assert first["id"] not in remaining
    assert second["id"] in remaining
