# urirun SDK contract (all languages)

Every urirun SDK — `adapters/python`, `adapters/js`, `adapters/go`, `adapters/php`,
… — exists to build **one document**: `urirun.bindings.v2`. A connector written
in any language is standardized when its SDK emits the same contract for the same
inputs. This file is that contract; `adapters/conformance.py` enforces it.

## The document

```json
{
  "version": "urirun.bindings.v2",
  "bindings": {
    "<scheme>://<target>/<resource>/<operation>": {
      "uri": "<same key>",
      "kind": "command",
      "adapter": "argv-template",
      "inputSchema": { "type": "object", "properties": {}, "required": [], "additionalProperties": false },
      "argv": ["cli", "sub", "{param}"],
      "meta": { "connector": "<id>" }
    }
  }
}
```

## Required SDK surface

Each language SDK MUST expose, in its own idiom, three operations:

1. **Create a connector** with an id and a URI `scheme` (default target `host`).
2. **Declare a command**: a route (`resource/operation`), an input schema
   (`required` + `properties`), and an `argv` template whose `{placeholders}`
   match the schema property names.
3. **Emit bindings**: return the `urirun.bindings.v2` document.

| Language | create | declare command | emit |
| --- | --- | --- | --- |
| Python | `urirun.connector(id, scheme=…)` | `@c.command("res/op")` (signature = schema) | `c.bindings()` |
| JavaScript | `connector(id, {scheme})` | `c.command(route, {input, argv})` | `c.bindings()` |
| Go | `urirun.NewConnector(id, scheme)` | `c.Command(route, Schema{…}, argv)` | `c.Bindings()` |
| PHP | `new Urirun\Connector(id, scheme)` | `$c->command(route, $schema, $argv)` | `$c->bindings()` |

## Invariants (what conformance checks)

For the same connector, every SDK must agree on:

- `version == "urirun.bindings.v2"`,
- the route key (`<scheme>://host/<resource>/<operation>`),
- `kind` (`command`) and `adapter` (`argv-template`),
- the `argv` array,
- the schema's `required` list and `properties` keys,
- `additionalProperties == false`.

Language-idiomatic extras are allowed (Python copies a `title` from the function
signature; any SDK may add `meta`/`policy`) as long as the invariants hold and
the document passes `urirun validate`.

## Conformance

```bash
python3 adapters/conformance.py
```

Builds the reference `hash` connector with each available SDK, validates each
against the runtime, and asserts the essential contracts are identical. JS joins
the check once its SDK exposes the connector builder.

See also the cross-language guide:
<https://docs.ifuri.com/generating-connectors.html>.
