# urihandler python adapter

Install directly from GitHub:

```bash
pip install "git+https://github.com/tellmesh/urihandler.git@main#subdirectory=adapters/python"
```

After installation the `urihandler` CLI is available:

```bash
urihandler scan ./project --out .urihandler/bindings.v5.json --registry-out .urihandler/registry.merged.json
urihandler compile .urihandler/bindings.v5.json --out .urihandler/registry.merged.json
urihandler discover manifest ./urihandler-routes.json --out /tmp/manifest.registry.json
urihandler build-registry /tmp/manifest.registry.json --out .urihandler/registry.merged.json
urihandler call 'cli://local/git/status' --registry .urihandler/registry.merged.json
```

`urihandler-v4`, `urihandler-v5`, `urihandler-v6`, `urihandler-v7`, and
`urihandler-v8` are also installed as explicit versioned entry points.

v8 can generate schema-first bindings and a compiled registry from existing
artifacts:

```bash
urihandler-v8 scan ./project \
  --out generated/bindings.v8.json \
  --registry-out generated/registry.json
urihandler-v8 validate generated/bindings.v8.json
urihandler-v8 list generated/registry.json
```


## License

Licensed under Apache-2.0.
