import {
  buildRegistryDocument,
  discoverDockerLabels,
  discoverManifest,
  discoverObjectRoutes,
  dispatchGenerated,
  hydrateRegistry,
  withUriRoute,
} from './urihandler-v4.js';

// withUriRoute is the JavaScript equivalent of Python's @uri_handler.
// It does not call the function. It only attaches URI route metadata to
// the function so a discovery step can generate registry entries from
// existing code.
const ledSet = withUriRoute(
  // Runtime function shape used by the local-function executor:
  // target comes from the URI authority, args come from path segments
  // after resource/operation, and payload is caller-provided data.
  (target, args, payload) => ({ ok: true, target, state: args[0], payload }),

  // This URI declares the contract. It maps to route device.led.set.
  // The concrete target device-01 and sample state on are examples; the
  // same route can later handle device://device-02/led/set/off.
  'device://device-01/led/set/on',

  // ref is symbolic so generated registry JSON can be stored and shared.
  // hydrateRegistry below maps this string back to the real JS function.
  { kind: 'function', adapter: 'local-function', ref: 'devices.ledSet' },
);

const routes = [
  // Scan JS objects for functions annotated with withUriRoute.
  // This is the dynamic registry generation path for application code.
  ...discoverObjectRoutes({ devices: { ledSet } }),

  // Manifest discovery is useful for CLI, shell, and other commands that
  // do not live as JS functions in the current process.
  ...discoverManifest({
    routes: [
      {
        package: 'cli',
        resource: 'git',
        operation: 'status',
        routeEntry: { kind: 'cli', adapter: 'spawn', config: { command: ['git', 'status'] } },
      },
    ],
  }),

  // Docker labels let running services publish their own URI contract.
  // The generated route below maps service://api/user/create/basic to an
  // HTTP executor entry without writing backend-specific SDK code here.
  ...discoverDockerLabels({
    'urihandler.uri': 'service://api/user/create/basic',
    'urihandler.kind': 'http',
    'urihandler.adapter': 'fetch',
    'urihandler.method': 'POST',
    'urihandler.url': 'http://user-service:8080/api/users',
  }),
];

// The registry document is portable JSON: routes + URI hash index + source
// metadata. At this point local function refs are still symbolic strings.
const registry = buildRegistryDocument(routes);

// Hydration is process-local. It replaces symbolic refs with real functions
// only in the runtime that is allowed to execute them.
const hydrated = hydrateRegistry(registry, { 'devices.ledSet': ledSet });

// device.led.set resolves from the generated registry and executes ledSet.
console.log(await dispatchGenerated('device://device-01/led/set/off', hydrated, { source: 'example' }));

// cli.git.status resolves through the same registry, but uses the spawn
// adapter. In this reference implementation it is simulated.
console.log(await dispatchGenerated('cli://local/git/status', registry));
