# HTML URI app

Static HTML + JS example that uses v5 URI bindings as the application contract.

The app does not create one JavaScript handler per button. Buttons and links only carry URI addresses:

```html
<a href="#device://device-01/led/set/on">LED on</a>
<button data-uri="service://api/user/create/basic">Create user</button>
```

One delegated click handler calls:

```js
runtime.dispatch(uri, payload)
```

The runtime resolves the URI through `bindings.json`, picks the adapter and executes a local demo adapter.

## Run

```bash
bash v5/examples/html_uri_app/run.sh
```

Open:

```txt
http://127.0.0.1:41735/
```

## Test

```bash
node v5/examples/html_uri_app/test.mjs
```

## Files

- `bindings.json` - URI to adapter map
- `uri-runtime.js` - small browser-safe dispatcher
- `app.js` - demo adapters and UI wiring
- `index.html` - URI-driven controls
