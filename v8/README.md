# urihandler v8

v8 is schema-first command packaging.

It replaces custom `params.required/default` declarations with standard JSON
Schema and adds Python decorators that generate that schema from function
signatures.

## Decorator

```python
from urihandler.v8 import uri_command, uri_shell

@uri_command("media://local/video/transcode")
def transcode(input: str, output: str, width: int = 1280, height: int = 720):
    return ["ffmpeg", "-i", "{input}", "-vf", "scale={width}:{height}", "{output}"]

@uri_shell("shell://local/echo/message")
def echo(text: str):
    return "printf '%s\\n' '{text}'"
```

The decorator creates an `inputSchema` from Pydantic and stores the argv or shell
template as a normal v8 binding. The runtime validates payload/query values
against that schema, applies defaults, renders placeholders, and then runs the
command.

Shell routes are real shell execution, but they stay behind the v6 policy gate:
execution needs both an allow rule and `allowShellTemplates: true`.

## JSON binding

```json
{
  "bindings": {
    "media://local/video/transcode": {
      "kind": "command",
      "adapter": "argv-template",
      "inputSchema": {
        "type": "object",
        "required": ["input", "output"],
        "properties": {
          "input": { "type": "string" },
          "output": { "type": "string" },
          "width": { "type": "integer", "default": 1280 },
          "height": { "type": "integer", "default": 720 }
        },
        "additionalProperties": false
      },
      "argv": ["ffmpeg", "-i", "{input}", "-vf", "scale={width}:{height}", "{output}"]
    }
  }
}
```

## Artifact adoption

`urihandler.v8 scan ./project` adopts common package standards:

- Dockerfile with `io.tellmesh.urihandler.manifest=...`
- OCI-compatible labels such as `org.opencontainers.image.source`
- `package.json` scripts
- `pyproject.toml` `[project.scripts]`
- `Makefile` targets
- `*.sh` scripts
- explicit `urihandler.manifest.json` / `bindings.v8.json`

This makes existing repositories behave like URI packages without manually
writing every endpoint.

## CLI

```bash
PYTHONPATH=adapters/python python -m urihandler.v8 scan v8/examples/artifacts --out /tmp/v8.bindings.json
PYTHONPATH=adapters/python python -m urihandler.v8 validate /tmp/v8.bindings.json
PYTHONPATH=adapters/python python -m urihandler.v8 compile /tmp/v8.bindings.json --out /tmp/v8.registry.json
PYTHONPATH=adapters/python python -m urihandler.v8 run tool://local/report/render --registry /tmp/v8.registry.json --payload '{"name":"Ada"}'
```

## Standards used

- JSON Schema Draft 2020-12 for input validation.
- Pydantic v2 for Python authoring and schema generation.
- OCI image labels/annotations for discoverable image metadata.
- Existing package metadata: `package.json`, `pyproject.toml`, Makefile targets.
