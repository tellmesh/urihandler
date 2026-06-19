# Naming

The public runtime name is `urirun`. The GitHub repository URL is still
`tellmesh/urirun`.

## Use `urirun` for runtime surfaces

Use `urirun` for:

- Python distribution name
- Python import namespace
- JS package name and imports
- primary CLI command
- versioned CLI commands
- JSON document versions
- Docker/OCI labels
- C firmware adapter files
- documentation title
- logo and website branding

Recommended commands:

```bash
urirun --help
urirun scan ./project
urirun validate generated/bindings.v8.json
urirun list generated/registry.json
urirun run 'tool://local/report/render' --registry generated/registry.json
```

Version-specific CLIs are also available:

```bash
urirun-v7 --help
urirun-v8 --help
```

Examples:

```python
from urirun import v8
from urirun.v8 import uri_command
```

```js
import { parseUri } from "urirun";
```

```json
{ "version": "urirun.bindings.v8" }
```

```dockerfile
LABEL io.tellmesh.urirun.manifest="/app/bindings.json"
```

## `urihandler` is now only historical

The repository was renamed to `tellmesh/urirun`, so everything user-facing is
`urirun`, including the remote and install commands:

```txt
git@github.com:tellmesh/urirun.git
```

```bash
pip install "git+https://github.com/tellmesh/urirun.git@main#subdirectory=adapters/python"
npm install github:tellmesh/urirun
```

GitHub keeps a redirect from the old `tellmesh/urihandler` URL, and historical
changelog entries can still mention `urihandler`.
