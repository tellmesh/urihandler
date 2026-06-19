# urihandler v8

`urihandler v8` turns command endpoints into schema-first packages.

```txt
function signature -> Pydantic model -> JSON Schema -> URI binding -> shell/argv runtime
existing artifact -> scanner -> URI binding -> registry
```

## Contract

The portable contract is JSON:

```json
{
  "uri": "media://local/video/transcode",
  "kind": "command",
  "adapter": "argv-template",
  "inputSchema": { "type": "object" },
  "argv": ["ffmpeg", "-i", "{input}", "{output}"]
}
```

`inputSchema` is JSON Schema Draft 2020-12. The runtime validates the merged
input object, applies schema defaults, and then renders placeholders.

Parameter sources:

1. URI query string
2. payload object
3. URI target as `{target}`
4. trailing URI args as `{0}`, `{1}`, ...

The schema validates named payload/query fields. `{target}` and numeric
placeholders are runtime values and do not need to be listed in the schema.

## Adapters

| adapter | execution |
|---------|-----------|
| `argv-template` | renders `argv[]` and executes it with `subprocess.run(argv)` |
| `shell-template` | renders a shell string and executes it with `shell=True` |
| `docker-run` | inherited from v7, renders command inside `docker run` |
| `docker-exec` | inherited from v7, renders command inside `docker exec` |

Use `argv-template` by default. `shell-template` is intentionally policy-gated:
execution requires an allow rule plus `allowShellTemplates: true`.

## Decorators

```python
@uri_command("say://local/echo/message")
def echo(text: str):
    return ["python3", "-c", "import sys; print(sys.argv[1])", "{text}"]

@uri_shell("shell://local/echo/message")
def shell_echo(text: str):
    return "printf '%s\\n' '{text}'"
```

The function is not the runtime handler. It is the authoring surface: its
signature creates the schema and its return value creates the command template.
The compiled registry remains JSON.

## Artifact adoption

v8 can scan a project directory and adopt common declarations:

- Dockerfile labels, including `io.tellmesh.urihandler.manifest`
- `package.json` scripts
- `pyproject.toml` `project.scripts`
- Makefile targets
- shell scripts
- explicit v8 manifests

For Docker images, the recommended declaration is:

```dockerfile
LABEL org.opencontainers.image.source="https://github.com/org/repo"
LABEL io.tellmesh.urihandler.manifest="urihandler.manifest.json"
```

The image/build artifact points to the URI manifest; the manifest describes the
actual URI contract.
