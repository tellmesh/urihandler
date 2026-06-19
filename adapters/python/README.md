# urirun python adapter

Install from PyPI:

```bash
pip install urirun
```

The PyPI distribution is named `urirun` because `urihandler` is already used by
another project. The Python import package remains `urihandler`:

```python
import urihandler
```

Install directly from GitHub:

```bash
pip install "git+https://github.com/tellmesh/urihandler.git@main#subdirectory=adapters/python"
```

After installation the `urirun` CLI is available:

```bash
urirun scan ./project --out .urihandler/bindings.v8.json --registry-out .urihandler/registry.merged.json
urirun validate .urihandler/bindings.v8.json
urirun list .urihandler/registry.merged.json
urirun run 'cli://local/git/status' .urihandler/registry.merged.json
```

`urirun-v4`, `urirun-v5`, `urirun-v6`, `urirun-v7`, and `urirun-v8` are also
installed as explicit versioned entry points. Compatibility aliases
`urihandler-v4` through `urihandler-v8` are kept for existing scripts.

v8 can generate schema-first bindings and a compiled registry from existing
artifacts:

```bash
urirun scan ./project \
  --out generated/bindings.v8.json \
  --registry-out generated/registry.json
urirun validate generated/bindings.v8.json
urirun list generated/registry.json
```


## License

Licensed under Apache-2.0.
