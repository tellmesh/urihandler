# Complexity gate

<!-- docs-nav -->
📖 **Dokumentacja urirun:** [← README](../README.md) · [Architektura](ARCHITECTURE.md) · [Komponenty](COMPONENTS.md) · [URI Objects](URI_OBJECTS.md) · [Łączenie node](NODE_CONNECTIONS.md) · [Dashboard & chat](HOST_DASHBOARD_CHAT.md) · [Host↔Node](HOST_NODE_COMMUNICATION.md) · [Sekrety](SECRETS.md) · [Archiwum dok.](DOCUMENT_ARCHIVE.md) · [Decision Loop](DECISION_LOOP.md) · [Roadmap](REFACTOR_ROADMAP.md) · **Complexity gate** · [Podział paczek](URIRUN_PACKAGE_SPLIT_PLAN.md) · [Planfile](PLANFILE_HOST_INTEGRATION_PLAN.md)
<!-- /docs-nav -->

Every Python function in the adapter is kept under **cyclomatic complexity 15**. A CI gate
enforces it so the limit can't quietly regress as new code lands.

## Run it

```bash
make complexity                       # the gate (used by CI)
python scripts/cc_gate.py             # same thing, directly
python scripts/cc_gate.py --limit 12  # try a stricter bar
python scripts/cc_gate.py --paths adapters/python/urirun/host
```

Exit `0` when clean, `1` with a ranked offender list (worst first) otherwise:

```text
CC gate FAILED: 1 function(s) over CC=15:
  CC=24  adapters/python/urirun/host/host_dashboard.py:9243  _merge_live_webpage_nodes
```

## What it checks

- **Metric:** [`radon`](https://pypi.org/project/radon/) cyclomatic complexity — the Python
  standard, already a project tool. The gate fails on `complexity > limit` (default `15`).
- **Scope:** `adapters/python/urirun` and `scripts/` (`--paths` to narrow). Vendored/generated
  trees (`build/`, `dist/`, `.venv`, `*.egg-info`, …) are skipped.
- **Enforcement:** a step in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs
  `pip install radon` then `make complexity` on every push and PR, alongside `make lint`
  (ruff) and `make test`.

## Fixing a violation

The offender output gives `file:line`. Reduce the function below the limit by the same moves
the refactor used — they preserve behaviour:

- **Extract helpers** — pull a cohesive block (a guard cascade, a result builder, a per-item
  loop body, a dense `or`-default cluster) into its own named function.
- **Dispatch table** — replace a long `if/elif` URI/command router with a `dict` of handlers
  (see `_dashboard_api_response` / `_uri_invoke_route` in `host_dashboard.py`).
- **Split a god-function** — move each intent branch to its own handler and leave a thin
  dispatcher (see `chat_ask`, which went from CC=100 to a small dispatcher + handlers).

## The radon gate vs. the `code2llm` `critical` metric

These are **two different metrics** and only one is enforced. The CI gate above is **radon,
`complexity > 15`**. The `code2llm` HEALTH report (e.g. `critical:7/2384`, `🟡 CC … (limit:15)`)
is a *separate* analyzer with its own count — its `critical` tier and the per-function CC it
prints do **not** match radon's, so a function `code2llm` flags `🟡 CC=15` already **passes**
the radon gate (which only fails on `> 15`), and a non-zero `code2llm critical:N` does **not**
mean CI is red. When deciding what to refactor, run `python scripts/cc_gate.py` — that is the
authoritative list of what breaks the build. Treat `code2llm` as a trend signal, not a gate.

JS/Go functions (e.g. `dashboard.js`'s `humanTaskBanner`) are **out of scope** for this
Python gate; their complexity is covered by the xlang polyglot proofs and the `code2llm`
report only.

## Recent reductions

- **2026-06-28** — four host functions taken back under the limit by pure helper extraction
  (behaviour-preserving): `_try_recall_gate` 17→8 (`_recall_env_fp`, `_unwrap_recall`),
  `_enrich_remote_attachments` 17→5 (`_resolve_attachment_preview`),
  `local_entry_point_host_routes` 16→5 (`_host_entry_point_route`, `_entry_point_safe`),
  `_chat_ask_general` 17→14 (`_attach_known_good_recall`). Gate green afterwards.

## Background

This gate locks in a complexity-reduction pass that brought the worst offenders under the
limit (`host_dashboard.py`'s `chat_ask` was **CC=100**; `scanner_best_finish` was 47) and
extracted two self-contained concerns out of the 10k-line `host_dashboard.py` into
[`host/document_metadata.py`](../adapters/python/urirun/host/document_metadata.py) (OCR + LLM
metadata) and [`host/scanner_net.py`](../adapters/python/urirun/host/scanner_net.py) (scanner
networking / QR / TLS). See [Roadmap](REFACTOR_ROADMAP.md) for the broader backlog.

> Want exact parity with the `code2llm` metric instead? The gate's backend is a one-line swap —
> but radon is the right call for CI (fast, deterministic, no output parsing).
