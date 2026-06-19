# Docker URI flow

This example demonstrates URI-addressed resources communicating across Docker
services:

- `python-worker` owns `python://python-worker/...`
- `node-worker` owns `node://node-worker/...`
- `shell-worker` owns `shell://shell-worker/...`
- `orchestrator` reads `flows/cross_service_report.yaml` and calls each service
  through the URI target hostname.

Every worker exposes:

- `GET /routes` - its v8 bindings
- `POST /run` - execute one URI resource

The Dockerfiles include `io.tellmesh.urihandler.manifest=/app/bindings.json`,
so the image declares where its URI package manifest lives.

## Flow

The flow format mirrors the compact office examples from `uri2flow`:

```yaml
steps:
  - id: normalize_text
    uri: python://python-worker/text/normalize
    payload:
      text: "Supplier Report June 2026"

  - id: slugify_text
    uri: node://node-worker/text/slugify
    depends_on:
      - normalize_text
    payload:
      text_from: normalize_text.result.normalized
```

Fields ending in `_from` read values from previous step results.

## Run

```bash
bash v8/examples/docker_uri_flow/run.sh
```

Expected final path:

```txt
/data/supplier-report-june-2026.txt
```

The point is that the orchestrator only sees URI resources and JSON payloads.
It does not need to know whether the backing implementation is Python, Node.js,
a shell script, a package script, or another Docker image.
