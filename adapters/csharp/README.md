# urirun — C# SDK

Build `urirun.bindings.v2` documents from C# (no dependencies; pass JSON
fragments for schema and argv).

```bash
dotnet run > bindings.json
urirun validate bindings.json && urirun compile bindings.json --out registry.json
```

Contract: https://docs.ifuri.com/generating-connectors.html
