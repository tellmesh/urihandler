# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.

import contextlib
import io
import importlib.util
import json
import os
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

from urirun import host_dashboard, host_db, mesh, planfile_adapter, v2


PLANFILE_AVAILABLE = importlib.util.find_spec("planfile") is not None


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


@unittest.skipUnless(PLANFILE_AVAILABLE, "planfile is not installed")
class HostDashboardTests(unittest.TestCase):
    def test_dashboard_html_summary_and_task_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "host.db")
            config = str(Path(tmp) / "mesh.json")
            mesh.init_host(config, name="test-host")
            ticket = planfile_adapter.create_ticket(
                tmp,
                {
                    "name": "Check daily domains",
                    "queue": "daily",
                    "prompt": "check domains",
                    "executor_handler": "flow://host/daily/command/run",
                },
            )
            host_db.add_log(db, "daily", "dashboard.test", {"ok": True})
            host_db.add_check(db, "ifuri.com", "monitor://ifuri.com/http/query/status", "ok", {"status": 200})
            with contextlib.redirect_stdout(io.StringIO()):
                server = host_dashboard.serve(project=tmp, db=db, config=config, host="127.0.0.1", port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_address[1]}"
            try:
                with urllib.request.urlopen(f"{base}/", timeout=5) as response:
                    html = response.read().decode("utf-8")
                self.assertIn("urirun host", html)
                self.assertIn("/api/summary", html)
                self.assertIn("documentReconcileBtn", html)  # index reconcile button is wired in

                summary = get_json(f"{base}/api/summary")
                self.assertTrue(summary["ok"], summary)
                self.assertEqual(summary["taskCounts"]["open"], 1)
                self.assertEqual(summary["logs"][0]["event"], "dashboard.test")
                self.assertEqual(summary["checks"][0]["subject"], "ifuri.com")

                tasks = get_json(f"{base}/api/tasks?sprint=current")
                self.assertEqual(tasks["tickets"][0]["id"], ticket["id"])

                started = post_json(f"{base}/api/tasks/{ticket['id']}/start", {"assigned_to": "dashboard"})
                self.assertTrue(started["ok"], started)
                self.assertEqual(started["ticket"]["status"], "in_progress")
            finally:
                server.shutdown()
                server.server_close()

    def test_documents_reconcile_http_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "host.db")
            config = str(Path(tmp) / "mesh.json")
            mesh.init_host(config, name="test-host")
            docs_dir = Path(tmp) / "documents"
            docs_dir.mkdir()
            live_pdf = docs_dir / "live.pdf"
            live_pdf.write_bytes(b"%PDF-1.4")
            (docs_dir / "index.json").write_text(json.dumps({"version": 1, "documents": [
                {"docId": "ALIVE", "pdfPath": str(live_pdf)},
                {"docId": "ORPHAN", "pdfPath": str(docs_dir / "gone.pdf")},
            ]}), encoding="utf-8")

            with contextlib.redirect_stdout(io.StringIO()):
                server = host_dashboard.serve(project=tmp, db=db, config=config, host="127.0.0.1", port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_address[1]}"
            try:
                with patch.dict(os.environ, {"URIRUN_DOCUMENT_DIR": str(docs_dir)}, clear=False):
                    result = post_json(f"{base}/api/documents/reconcile", {})
                self.assertTrue(result["ok"], result)
                self.assertEqual(result["prunedCount"], 1)
                self.assertEqual([p["docId"] for p in result["pruned"]], ["ORPHAN"])
            finally:
                server.shutdown()
                server.server_close()

    def test_v2_dashboard_url_command(self):
        buffer = []

        class Writer:
            def write(self, value):
                buffer.append(value)

        with patch("sys.stdout", Writer()):
            code = v2.main(["host", "dashboard", "url", "--port", "8123"])
        self.assertEqual(code, 0)
        self.assertIn("http://127.0.0.1:8123/", "".join(buffer))


@unittest.skipUnless(host_dashboard._business_key is not None, "docid.dedup not installed")
class ScanDedupBusinessKeyTests(unittest.TestCase):
    """A cash receipt has no transaction token and re-scans differ in framing/OCR, so the
    merchant+date+total business key (corroborated by shared monetary tokens) is what stops
    the duplicate. Regression for the real CYFRONIKA double-scan."""

    META = {"type": "paragon", "contractor": "CYFRONIKA", "date": "2026-06-24", "amount": "10.21", "currency": "PLN"}
    TEXT_A = "CYFRONIKA PARAGON 4.68 6.59 7.32 12.50 4.70 Sprzedaz A 54.61 SUMA 10.21"
    TEXT_B = "CYFRONIKA PARAGON F ISKALNY 4.68 6.59 7.32 12.50 4.70 opodatkowana 54.61 DO ZAPLATY 10.21 Gotowka 54.61"
    EMPTY_FP = {"number": "", "auth": "", "time": "", "card": ""}

    def test_business_key_matches_cash_rescan_with_inline_text(self):
        index = {"documents": [{
            "docId": "DOC-1", "fingerprint": self.EMPTY_FP,
            "dhash": "6747434b43435b79", "phash": "a07aa05aa19fa17f", "text": self.TEXT_B, **self.META,
        }]}
        match = host_dashboard._find_duplicate_document(
            index, doc_id="DOC-2", source_sha256="aaa", text_sha256="bbb",
            fingerprint=self.EMPTY_FP, dhash="736345454143496d", phash="a857a057a89fa24f",
            metadata=self.META, text=self.TEXT_A,
        )
        self.assertIsNotNone(match)
        self.assertEqual(match["docId"], "DOC-1")
        self.assertEqual(match["_matchReason"], "business-key")

    def test_business_key_hydrates_text_from_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            sidecar = Path(tmp) / "doc1.json"
            sidecar.write_text(json.dumps({"text": self.TEXT_B}), encoding="utf-8")
            # Index entry omits text (as real entries did before this change).
            index = {"documents": [{
                "docId": "DOC-1", "fingerprint": self.EMPTY_FP,
                "dhash": "6747434b43435b79", "jsonPath": str(sidecar), **self.META,
            }]}
            match = host_dashboard._find_duplicate_document(
                index, doc_id="DOC-2", source_sha256="aaa", text_sha256="bbb",
                fingerprint=self.EMPTY_FP, dhash="736345454143496d",
                metadata=self.META, text=self.TEXT_A,
            )
            self.assertIsNotNone(match)
            self.assertEqual(match["_matchReason"], "business-key")

    def test_distinct_receipts_same_total_stay_separate(self):
        index = {"documents": [{
            "docId": "DOC-1", "fingerprint": self.EMPTY_FP,
            "text": "PARAGON 3.00 51.61 SUMA 54.61", **self.META,
        }]}
        match = host_dashboard._find_duplicate_document(
            index, doc_id="DOC-2", source_sha256="aaa", text_sha256="bbb",
            fingerprint=self.EMPTY_FP, dhash="", metadata=self.META,
            text="PARAGON 20.00 34.61 SUMA 54.61",
        )
        self.assertIsNone(match)


class DocumentIndexReconcileTests(unittest.TestCase):
    """Index<->filesystem reconciliation: orphaned entries (no PDF and no JSON on disk)
    are pruned, entries that still have a file are kept, real files are never deleted."""

    def test_prune_orphaned_documents_keeps_entries_with_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            live_pdf = Path(tmp) / "live.pdf"
            live_pdf.write_bytes(b"%PDF-1.4")
            index = {"documents": [
                {"docId": "ALIVE", "pdfPath": str(live_pdf), "jsonPath": str(Path(tmp) / "missing.json")},
                {"docId": "ORPHAN-1", "pdfPath": str(Path(tmp) / "gone.pdf"), "jsonPath": str(Path(tmp) / "gone.json")},
                {"docId": "ORPHAN-2", "pdfPath": "", "jsonPath": ""},
            ]}
            pruned = host_dashboard._prune_orphaned_documents(index)

            self.assertEqual({p["docId"] for p in pruned}, {"ORPHAN-1", "ORPHAN-2"})
            self.assertEqual([d["docId"] for d in index["documents"]], ["ALIVE"])
            self.assertTrue(live_pdf.is_file())  # real file untouched

    def test_documents_reconcile_endpoint_prunes_and_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            live_pdf = Path(tmp) / "live.pdf"
            live_pdf.write_bytes(b"%PDF-1.4")
            index_path = Path(tmp) / "index.json"
            index_path.write_text(json.dumps({"version": 1, "documents": [
                {"docId": "ALIVE", "pdfPath": str(live_pdf)},
                {"docId": "ORPHAN", "pdfPath": str(Path(tmp) / "gone.pdf"), "jsonPath": str(Path(tmp) / "gone.json")},
            ]}), encoding="utf-8")

            with patch.dict(os.environ, {"URIRUN_DOCUMENT_DIR": tmp}, clear=False):
                report = host_dashboard.documents_reconcile("proj", None, {})

            self.assertTrue(report["ok"])
            self.assertEqual(report["before"], 2)
            self.assertEqual(report["after"], 1)
            self.assertEqual([p["docId"] for p in report["pruned"]], ["ORPHAN"])
            # Change is persisted to the index file.
            persisted = json.loads(index_path.read_text(encoding="utf-8"))
            self.assertEqual([d["docId"] for d in persisted["documents"]], ["ALIVE"])


if __name__ == "__main__":
    unittest.main()
