# urirun — Java SDK

Build `urirun.bindings.v2` documents from Java (no dependencies; pass JSON
fragments for schema and argv).

```bash
javac -d out Urirun.java example/HashConnector.java
java -cp out HashConnector > bindings.json
urirun validate bindings.json && urirun compile bindings.json --out registry.json
```

Contract: https://docs.ifuri.com/generating-connectors.html
