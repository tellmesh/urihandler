# Transports

`urirun` keeps the URI contract separate from the transport. The same URI can be
called locally, through a service endpoint, or by a flow orchestrator.

## Local and shell

- `local-function` calls an in-process function registered by code.
- `argv-template` renders an argv list and executes it without a shell.
- `shell-template` renders a shell string and requires explicit policy approval.

## Docker

Docker examples use URI targets as service names:

```text
python://python-worker/text/normalize
node://node-worker/text/slugify
shell://shell-worker/report/write
```

See `v8/examples/docker_uri_flow` for a Compose flow where services publish
bindings and an orchestrator runs a multi-step URI flow.

## HTTP and browser

The HTML example in `v8/examples/html_uri_app` loads a binding document, renders
URI forms, and calls a Python backend through `POST /api/run`.

The backend can expose logs, recent calls, MCP tools, and A2A cards from the same
registry, so frontend actions use the same URI names as backend actions.

## gRPC

`urirun.v8_grpc` provides a small RPC surface for route listing, unary calls,
and stream-style calls. Install the optional dependency set when using it:

```bash
pip install "urirun[grpc] @ git+https://github.com/tellmesh/urihandler.git@main#subdirectory=adapters/python"
```

## MCP and A2A

Because v8 bindings include JSON Schema, the registry can be projected into:

- MCP `tools/list`
- MCP `tools/call`
- A2A agent card skills

Execution still goes through the same `urirun` policy gate.
