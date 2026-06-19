<?php
return [
    'docs' => [
        'getting-started' => [
            'title' => 'Getting started',
            'description' => 'Install from GitHub, scan artifacts, validate, and run the first URI.',
        ],
        'naming' => [
            'title' => 'Naming',
            'description' => 'Where to use urirun and why the repository URL still contains urihandler.',
        ],
        'commands' => [
            'title' => 'Commands',
            'description' => 'CLI commands, versioned entry points, and one-line binding generation.',
        ],
        'registry-and-bindings' => [
            'title' => 'Registry',
            'description' => 'How portable binding documents become dispatchable runtime routes.',
        ],
        'transports' => [
            'title' => 'Transports',
            'description' => 'Local functions, shell, Docker, HTTP, gRPC, browser, MCP, and A2A.',
        ],
        'logo' => [
            'title' => 'Logo',
            'description' => 'Generated SVG assets for icon, wordmark, favicon, and lockups.',
        ],
        'roadmap' => [
            'title' => 'Roadmap',
            'description' => 'Practical next work for making urirun easier to use.',
        ],
    ],
    'workflow' => [
        ['uri' => 'repo://project/artifacts/query/scan', 'title' => 'Scan artifacts', 'text' => 'Read Dockerfile labels, package metadata, Make targets, shell scripts, and explicit bindings.'],
        ['uri' => 'registry://local/routes/command/compile', 'title' => 'Compile a registry', 'text' => 'Turn portable binding files into one lookup tree for every runtime.'],
        ['uri' => 'policy://local/execution/query/check', 'title' => 'Gate execution', 'text' => 'Dry-run first, then require allow rules for real argv, shell, Docker, or network calls.'],
        ['uri' => 'flow://local/task/command/run', 'title' => 'Run the same URI', 'text' => 'Call it from shell, backend, browser, Docker service, MCP tool, or A2A agent card.'],
    ],
    'features' => [
        ['title' => 'Artifact-first adoption', 'text' => 'Existing Dockerfiles, pyproject scripts, package.json scripts, shell files, and Makefile targets become routes without hand-writing every endpoint.'],
        ['title' => 'Schema-first calls', 'text' => 'v8 bindings use JSON Schema. Python decorators can generate schemas from function signatures through Pydantic.'],
        ['title' => 'One address across layers', 'text' => 'Frontend buttons, backend handlers, shell clients, firmware tables, and service flows can share the same URI naming standard.'],
        ['title' => 'Policy before execution', 'text' => 'Command routes dry-run by default. Real execution is explicit and can be limited by URI allow and deny rules.'],
    ],
    'transports' => [
        ['name' => 'local', 'detail' => 'In-process function dispatch'],
        ['name' => 'argv', 'detail' => 'Safe argument templates'],
        ['name' => 'shell', 'detail' => 'Policy-gated shell templates'],
        ['name' => 'Docker', 'detail' => 'Compose services and image labels'],
        ['name' => 'HTTP/gRPC', 'detail' => 'Remote route calls'],
        ['name' => 'MCP/A2A', 'detail' => 'Agent tool projection'],
    ],
    'examples' => [
        ['path' => 'v8/examples/html_uri_app', 'text' => 'Browser UI that calls a Python backend through URI actions and exposes logs/tools.'],
        ['path' => 'v8/examples/docker_uri_flow', 'text' => 'Docker Compose services communicating through generated URI bindings and a flow runner.'],
        ['path' => 'v8/examples/generators', 'text' => 'JS, Node.js, TypeScript, and PHP declarations that generate the same v8 binding contract.'],
        ['path' => 'examples/reference_adapters', 'text' => 'Minimal adapters for JavaScript, Python, C/firmware, and browser use.'],
    ],
    'roadmap' => [
        'urirun init for a starter registry, policy, and example route',
        'urirun doctor for environment, dependency, port, and route conflict checks',
        'urirun serve for a local route browser, log viewer, dry-run console, and policy-gated execution',
        'standard log:// routes across frontend, backend, shell, firmware, and Docker examples',
        'urirun diff for comparing registries before deployment',
    ],
];
