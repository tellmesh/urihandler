# v2 binding generators

These examples show the same v2 binding contract generated from several
language-native declaration styles:

- `js/` - plain JavaScript helper, no transpiler
- `nodejs/` - Node.js script that writes a binding document
- `ts/` - TypeScript decorator-style declaration
- `php/` - PHP 8 attribute + reflection

All examples generate the same shape:

```json
{
  "version": "urirun.bindings.v2",
  "bindings": {
    "scheme://target/resource/operation": {
      "kind": "command",
      "adapter": "argv-template",
      "inputSchema": {},
      "argv": []
    }
  }
}
```

The runtime does not care which language generated the file. It only consumes
the v2 JSON contract.
