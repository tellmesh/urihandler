# device_mesh_lab

Local URI mesh demo with a dashboard, two device agents and URI-addressed flows.

## Why `browser://.../open` can be blocked

`browser://desktop/page/command/open` reaches the `desktop` agent through the URI
registry, but the local browser side effect is disabled unless the device agent is
started with:

```bash
URIRUN_MESH_ALLOW_BROWSER=1
```

The default in `.env` is intentionally conservative:

```bash
URIRUN_MESH_ALLOW_BROWSER=0
```

With that default, the agent records a `browser.blocked` log and returns a policy
error. Other safe URI routes, such as `proc://`, `shell://.../which`, `note://`
and `log://`, still execute.

## Run with browser execution enabled

Start the dashboard and agents from this directory:

```bash
cd v2/examples/device_mesh_lab

python3 controller.py
```

In another terminal:

```bash
URIRUN_MESH_DEVICE_NAME=desktop \
URIRUN_MESH_DEVICE_ROLE=controller \
URIRUN_MESH_AGENT_PORT=18765 \
URIRUN_MESH_ALLOW_BROWSER=1 \
python3 device_agent.py
```

For the second simulated device:

```bash
URIRUN_MESH_DEVICE_NAME=laptop \
URIRUN_MESH_DEVICE_ROLE=remote-laptop \
URIRUN_MESH_AGENT_PORT=18766 \
URIRUN_MESH_ALLOW_BROWSER=1 \
python3 device_agent.py
```

Then open:

```text
http://127.0.0.1:8193/
```

## noVNC note

`webbrowser.open()` opens a browser in the operating system environment where the
agent process runs. If you want the action to appear inside a noVNC computer, run
that device agent inside the same desktop/noVNC container or replace the
`browser-intent` adapter with a browser automation adapter for that environment.
