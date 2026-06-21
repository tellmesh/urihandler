# urirun

SUMD - Structured Unified Markdown Descriptor for AI-aware project refactorization

## Contents

- [Metadata](#metadata)
- [Architecture](#architecture)
- [Workflows](#workflows)
- [Call Graph](#call-graph)
- [Test Contracts](#test-contracts)
- [Refactoring Analysis](#refactoring-analysis)
- [Intent](#intent)

## Metadata

- **name**: `urirun`
- **version**: `0.0.0`
- **ecosystem**: SUMD + DOQL + testql + taskfile
- **generated_from**: Makefile, testql(1), app.doql.less, goal.yaml, .env.example, package.json, project/(5 analysis files)

## Architecture

```
SUMD (description) → DOQL/source (code) → taskfile (automation) → testql (verification)
```

### DOQL Application Declaration (`app.doql.less`)

```less markpact:doql path=app.doql.less
// LESS format — define @variables here as needed

app {
  name: urirun;
  version: 0.3.14;
}

workflow[name="test"] {
  trigger: manual;
  step-1: depend target=version-check;
  step-2: depend target=test-js;
  step-3: depend target=test-python;
  step-4: depend target=test-c;
  step-5: depend target=conformance;
  step-6: depend target=test-v1;
  step-7: depend target=test-v2;
}

workflow[name="version-check"] {
  trigger: manual;
  step-1: run cmd=$(PYTHON) -c 'import json, pathlib, sys, tomllib; root = pathlib.Path("."); versions = {"VERSION": (root / "VERSION").read_text().strip(), "package.json": json.loads((root / "package.json").read_text())["version"], "adapters/python/VERSION": (root / "adapters/python/VERSION").read_text().strip(), "adapters/python/pyproject.toml": tomllib.loads((root / "adapters/python/pyproject.toml").read_text())["project"]["version"], "adapters/js/package.json": json.loads((root / "adapters/js/package.json").read_text())["version"]}; print("urirun versions:", ", ".join(f"{k}={v}" for k, v in versions.items())); sys.exit(0 if len(set(versions.values())) == 1 else 1)';
}

workflow[name="test-js"] {
  trigger: manual;
  step-1: run cmd=$(NODE) --test adapters/js/*.test.js;
}

workflow[name="test-python"] {
  trigger: manual;
  step-1: run cmd=PYTHONPATH=adapters/python $(PYTHON) -m unittest discover -s adapters/python/tests -p 'test_*.py';
}

workflow[name="test-c"] {
  trigger: manual;
  step-1: run cmd=$(CC) -Wall -Wextra -Werror -Iadapters/c adapters/c/urirun.c adapters/c/urirun_test.c -o /tmp/urirun-c-test;
  step-2: run cmd=/tmp/urirun-c-test;
}

workflow[name="conformance"] {
  trigger: manual;
  step-1: run cmd=$(PYTHON) adapters/conformance.py;
}

workflow[name="test-v1"] {
  trigger: manual;
  step-1: run cmd=printf '%s\n' '{"bindings":{"media://local/video/transcode":{"kind":"cli","adapter":"spawn","command":["ffmpeg","-i","{input}","-vf","scale={width}:{height}","{output}"],"params":{"input":{"required":true},"output":{"required":true},"width":{"default":1280},"height":{"default":720}}}}}' >/tmp/urirun-v1.bindings.json;
  step-2: run cmd=$(PYTHON) -m json.tool /tmp/urirun-v1.bindings.json >/tmp/urirun-v1-bindings.pretty.json;
  step-3: run cmd=PYTHONPATH=adapters/python $(PYTHON) -m urirun.v1 compile /tmp/urirun-v1.bindings.json --out /tmp/urirun-v1.registry.json --generated-at 2026-06-19T00:00:00.000Z;
  step-4: run cmd=PYTHONPATH=adapters/python $(PYTHON) -m urirun.v1 run 'media://local/video/transcode' --registry /tmp/urirun-v1.registry.json --payload '{"input":"a.mp4","output":"b.mp4"}' >/tmp/urirun-v1-ffmpeg.json;
  step-5: run cmd=PYTHONPATH=adapters/python $(PYTHON) -m urirun.v1 list /tmp/urirun-v1.registry.json --allow 'media://**';
}

workflow[name="test-v2"] {
  trigger: manual;
  step-1: run cmd=printf '%s\n' '{"bindings":{"util://local/echo/message":{"kind":"command","adapter":"argv-template","inputSchema":{"type":"object","required":["text"],"properties":{"text":{"type":"string"}},"additionalProperties":false},"argv":["python3","-c","import sys; print(sys.argv[1])","{text}"]}}}' >/tmp/urirun-v2.bindings.json;
  step-2: run cmd=$(PYTHON) -m json.tool /tmp/urirun-v2.bindings.json >/tmp/urirun-v2-bindings.pretty.json;
  step-3: run cmd=PYTHONPATH=adapters/python $(PYTHON) -m urirun.v2 compile /tmp/urirun-v2.bindings.json --out /tmp/urirun-v2.registry.json;
  step-4: run cmd=PYTHONPATH=adapters/python $(PYTHON) -m urirun.v2_mcp tools /tmp/urirun-v2.registry.json >/tmp/urirun-v2-mcp.json;
  step-5: run cmd=PYTHONPATH=adapters/python $(PYTHON) -m urirun.v2_mcp card /tmp/urirun-v2.registry.json >/tmp/urirun-v2-a2a.json;
  step-6: run cmd=PYTHONPATH=adapters/python $(PYTHON) -m urirun.v2_adopt add-python-package pip --out /tmp/urirun-v2-adopt.bindings.json;
  step-7: run cmd=PYTHONPATH=adapters/python $(PYTHON) -m urirun.v2 compile /tmp/urirun-v2-adopt.bindings.json --out /tmp/urirun-v2-adopt.registry.json;
  step-8: run cmd=PYTHONPATH=adapters/python $(PYTHON) -m urirun.v2 run 'cli://pip/pip/run' --registry /tmp/urirun-v2-adopt.registry.json --payload '{"args":["--version"]}' >/tmp/urirun-v2-adopt-run.json;
}

workflow[name="clean"] {
  trigger: manual;
  step-1: run cmd=rm -rf node_modules .pytest_cache adapters/python/tests/__pycache__ adapters/python/urirun/__pycache__ adapters/python/*.egg-info adapters/python/build __pycache__;
}

tests {
  import: testql-scenarios/**/*.testql.toon.yaml;
}

env_vars {
  keys: OPENROUTER_API_KEY, LLM_MODEL, PFIX_AUTO_APPLY, PFIX_AUTO_INSTALL_DEPS, PFIX_AUTO_RESTART, PFIX_MAX_RETRIES, PFIX_DRY_RUN, PFIX_ENABLED, PFIX_GIT_COMMIT, PFIX_GIT_PREFIX, PFIX_CREATE_BACKUPS;
}

deploy {
  target: docker;
}

environment[name="local"] {
  runtime: docker-compose;
  env_file: .env;
  template_file: .env.example;
  vars: LLM_MODEL, OPENROUTER_API_KEY, PFIX_AUTO_APPLY, PFIX_AUTO_INSTALL_DEPS, PFIX_AUTO_RESTART, PFIX_CREATE_BACKUPS, PFIX_DRY_RUN, PFIX_ENABLED, PFIX_GIT_COMMIT, PFIX_GIT_PREFIX, PFIX_MAX_RETRIES;
  runtime_llm: OPENROUTER_API_KEY;
  runtime_pfix: PFIX_AUTO_APPLY, PFIX_AUTO_INSTALL_DEPS, PFIX_AUTO_RESTART, PFIX_CREATE_BACKUPS, PFIX_DRY_RUN, PFIX_ENABLED, PFIX_GIT_COMMIT, PFIX_GIT_PREFIX, PFIX_MAX_RETRIES;
}
```

## Workflows

## Call Graph

*403 nodes · 500 edges · 31 modules · CC̄=4.4*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `run_planfile_task` *(in adapters.python.urirun.host.host_integrations)* | 31 ⚠ | 0 | 66 | **66** |
| `run_uri_route` *(in adapters.python.urirun.host.domain_monitor)* | 46 ⚠ | 0 | 57 | **57** |
| `create_handler` *(in adapters.python.urirun.host.host_dashboard)* | 1 | 1 | 52 | **53** |
| `run_uri_route` *(in adapters.python.urirun.host.host_db)* | 45 ⚠ | 0 | 45 | **45** |
| `build_ticket_payload` *(in adapters.python.urirun.host.planfile_adapter)* | 35 ⚠ | 1 | 43 | **44** |
| `run` *(in adapters.python.urirun.runtime.v2)* | 18 ⚠ | 1 | 35 | **36** |
| `scan_path` *(in adapters.python.urirun.runtime._scan)* | 15 ⚠ | 4 | 27 | **31** |
| `normalize_binding` *(in adapters.python.urirun.runtime._scan)* | 11 ⚠ | 17 | 12 | **29** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/if-uri/urirun
# generated in 0.18s
# nodes: 403 | edges: 500 | modules: 31
# CC̄=4.4

HUBS[20]:
  adapters.python.urirun.host.host_integrations.run_planfile_task
    CC=31  in:0  out:66  total:66
  adapters.python.urirun.host.domain_monitor.run_uri_route
    CC=46  in:0  out:57  total:57
  adapters.python.urirun.host.host_dashboard.create_handler
    CC=1  in:1  out:52  total:53
  adapters.python.urirun.host.host_db.run_uri_route
    CC=45  in:0  out:45  total:45
  adapters.python.urirun.host.planfile_adapter.build_ticket_payload
    CC=35  in:1  out:43  total:44
  adapters.python.urirun.runtime.v2.run
    CC=18  in:1  out:35  total:36
  adapters.python.urirun.runtime._scan.scan_path
    CC=15  in:4  out:27  total:31
  adapters.python.urirun.runtime._scan.normalize_binding
    CC=11  in:17  out:12  total:29
  adapters.python.urirun.runtime.errors.info
    CC=13  in:2  out:27  total:29
  adapters.python.urirun.runtime.v2.run_error_store
    CC=23  in:0  out:28  total:28
  adapters.python.urirun.connectors.connect_catalog.diff_manifest
    CC=18  in:1  out:27  total:28
  adapters.python.urirun.host.host_dashboard.summary
    CC=6  in:1  out:25  total:26
  adapters.python.urirun.host.host_dashboard._json_response
    CC=1  in:13  out:13  total:26
  adapters.python.urirun.runtime.v2.validate_binding_document
    CC=12  in:1  out:24  total:25
  adapters.python.urirun.connectors.connect_catalog._cmd_show
    CC=9  in:0  out:25  total:25
  adapters.python.urirun.runtime.v1.run
    CC=14  in:2  out:23  total:25
  adapters.python.urirun.runtime._runtime.run
    CC=10  in:1  out:23  total:24
  adapters.python.urirun.runtime.v2_mcp.serve_mcp
    CC=15  in:1  out:23  total:24
  adapters.python.urirun.runtime.errors.main
    CC=16  in:0  out:23  total:23
  adapters.python.urirun.runtime.v2.scan_artifacts
    CC=11  in:4  out:19  total:23

MODULES:
  adapters.c.urirun  [5 funcs]
    copy_token  CC=2  out:1
    is_path_end  CC=3  out:0
    memcpy  CC=1  out:1
    memset  CC=5  out:0
    urirun_parse  CC=20  out:5
  adapters.c.urirun_test  [2 funcs]
    assert  CC=1  out:0
    main  CC=2  out:3
  adapters.go.urirun  [2 funcs]
    Bindings  CC=1  out:1
    BindingsJSON  CC=1  out:4
  adapters.java.Urirun  [1 funcs]
    Connector  CC=1  out:0
  adapters.js  [5 funcs]
    buildInvocation  CC=1  out:2
    dispatch  CC=3  out:4
    fn  CC=2  out:1
    match  CC=2  out:1
    parseUri  CC=8  out:9
  adapters.php.Urirun  [2 funcs]
    bindings  CC=1  out:0
    bindingsJson  CC=1  out:2
  adapters.python.urirun  [7 funcs]
    build_invocation  CC=1  out:2
    command  CC=1  out:1
    connector  CC=2  out:2
    dispatch  CC=4  out:10
    load_manifest  CC=1  out:1
    parse_uri  CC=7  out:13
    shell  CC=1  out:1
  adapters.python.urirun.connectors.connect_catalog  [13 funcs]
    _cmd_check  CC=7  out:15
    _cmd_install  CC=13  out:14
    _cmd_list  CC=9  out:20
    _cmd_show  CC=9  out:25
    _connectors  CC=2  out:3
    _emit_json  CC=1  out:2
    _find  CC=3  out:3
    _get_json  CC=2  out:5
    diff_manifest  CC=18  out:27
    fetch_catalog  CC=1  out:3
  adapters.python.urirun.connectors.connector_scaffold  [10 funcs]
    _go_files  CC=1  out:1
    _js_files  CC=1  out:2
    _manifest  CC=1  out:3
    _php_files  CC=1  out:1
    _pkg_module  CC=1  out:1
    _python_files  CC=1  out:2
    _scheme  CC=2  out:1
    _write  CC=2  out:5
    new_command  CC=3  out:7
    scaffold  CC=3  out:7
  adapters.python.urirun.connectors.connector_sdk  [2 funcs]
    connector_cli  CC=5  out:11
    emit  CC=1  out:2
  adapters.python.urirun.connectors.connector_smoke  [3 funcs]
    _load  CC=3  out:4
    smoke  CC=6  out:20
    smoke_command  CC=2  out:4
  adapters.python.urirun.host.domain_monitor  [14 funcs]
    _domain  CC=2  out:2
    _list  CC=6  out:8
    _namecheap_moved  CC=1  out:1
    _provider  CC=4  out:5
    capture_screenshot_artifact  CC=3  out:8
    check_domain  CC=16  out:19
    default_url  CC=2  out:1
    dns_mismatches  CC=4  out:5
    dns_records  CC=11  out:8
    expected_records  CC=8  out:15
  adapters.python.urirun.host.host_dashboard  [11 funcs]
    _host_db  CC=1  out:0
    _html_response  CC=1  out:9
    _json_response  CC=1  out:13
    _mesh  CC=1  out:0
    _planfile_adapter  CC=1  out:0
    _safe_tickets  CC=2  out:3
    command  CC=8  out:5
    create_handler  CC=1  out:52
    serve  CC=1  out:7
    summary  CC=6  out:25
  adapters.python.urirun.host.host_db  [26 funcs]
    _schema_json  CC=2  out:2
    _validate_record  CC=2  out:3
    add_check  CC=2  out:9
    add_llm_message  CC=2  out:9
    add_log  CC=2  out:9
    connect  CC=1  out:5
    connection  CC=1  out:3
    create_dataset  CC=1  out:7
    create_llm_session  CC=1  out:8
    db_path  CC=2  out:3
  adapters.python.urirun.host.host_integrations  [4 funcs]
    _planfile_action  CC=7  out:1
    _planfile_project  CC=4  out:5
    _simulate_planfile  CC=1  out:3
    run_planfile_task  CC=31  out:66
  adapters.python.urirun.host.planfile_adapter  [20 funcs]
    _imports  CC=2  out:1
    _model_dict  CC=1  out:1
    build_ticket_payload  CC=35  out:43
    claim_ticket  CC=2  out:3
    complete_ticket  CC=2  out:3
    create_ticket  CC=3  out:7
    fail_or_retry  CC=4  out:11
    fail_ticket  CC=2  out:3
    get_ticket  CC=2  out:3
    list_tickets  CC=9  out:5
  adapters.python.urirun.host.scheduler  [5 funcs]
    build_loop_command  CC=4  out:4
    cron_line  CC=1  out:4
    preview  CC=3  out:5
    shell_join  CC=2  out:2
    systemd_units  CC=2  out:1
  adapters.python.urirun.node.mesh  [25 funcs]
    add_node  CC=4  out:7
    append_if_available  CC=5  out:6
    binding_for_remote_route  CC=3  out:5
    default_host_config  CC=3  out:3
    default_node_config  CC=2  out:1
    discover_mesh  CC=7  out:8
    discover_node  CC=2  out:9
    first_url  CC=2  out:2
    heuristic_flow  CC=19  out:16
    host_config_path  CC=2  out:2
  adapters.python.urirun.runtime._registry  [35 funcs]
    _default_openapi_route  CC=9  out:11
    _discover_python_module  CC=1  out:2
    _emit_json  CC=3  out:3
    _get_route_entry  CC=1  out:0
    _iter_module_exports  CC=6  out:8
    _load_sources  CC=2  out:3
    _operation_from_method  CC=1  out:1
    _route_entry_equal  CC=2  out:2
    _walk_route_entries  CC=5  out:3
    add_route  CC=5  out:6
  adapters.python.urirun.runtime._runtime  [11 funcs]
    _matches_any  CC=3  out:1
    _truncate  CC=3  out:2
    check  CC=1  out:7
    default_policy  CC=1  out:0
    evaluate_policy  CC=16  out:19
    list_routes  CC=4  out:10
    merge_policy  CC=7  out:8
    run  CC=10  out:23
    run_local_function  CC=2  out:6
    run_shell_template  CC=3  out:11
  adapters.python.urirun.runtime._scan  [33 funcs]
    _read_toml  CC=12  out:17
    binding_to_route_source  CC=3  out:3
    build_binding_document  CC=3  out:6
    compile_registry_document  CC=4  out:5
    emit_json  CC=3  out:3
    github_dependency_binding  CC=4  out:3
    infer_kind  CC=12  out:11
    iter_project_files  CC=5  out:4
    list_bindings  CC=2  out:3
    load_binding_source  CC=5  out:11
  adapters.python.urirun.runtime.compat  [6 funcs]
    _entry_point_names  CC=4  out:5
    _importable  CC=3  out:1
    _print_table  CC=10  out:17
    main  CC=4  out:12
    module_status  CC=8  out:9
    report  CC=8  out:7
  adapters.python.urirun.runtime.errors  [20 funcs]
    _aggregate  CC=4  out:13
    _append  CC=3  out:13
    _load  CC=5  out:7
    _normalize_message  CC=2  out:6
    address  CC=1  out:0
    capture  CC=1  out:9
    category_meta  CC=1  out:1
    classify  CC=36  out:5
    error_code  CC=1  out:4
    fix_hints  CC=5  out:11
  adapters.python.urirun.runtime.v1  [19 funcs]
    _binding_pairs  CC=8  out:11
    _env_flags  CC=3  out:5
    _has_placeholders  CC=2  out:3
    _params_spec  CC=4  out:3
    _proc_env  CC=3  out:6
    _run_process  CC=1  out:8
    compile_registry  CC=1  out:2
    expand_binding  CC=7  out:6
    expand_bindings  CC=2  out:2
    load_registry_arg  CC=4  out:9
  adapters.python.urirun.runtime.v2  [60 funcs]
    _apply_defaults  CC=14  out:12
    _binding_pairs  CC=8  out:11
    _bindings_as_map  CC=2  out:2
    _coerce_default  CC=4  out:3
    _document_binding_from_expanded  CC=4  out:5
    _empty_input_schema  CC=1  out:0
    _first_payload_value  CC=3  out:1
    _host_integrations  CC=1  out:0
    _input_values  CC=4  out:8
    _iter_files  CC=5  out:4
  adapters.python.urirun.runtime.v2_adopt  [5 funcs]
    _command_binding  CC=2  out:2
    installed_python_bindings  CC=4  out:3
    npm_package_bindings  CC=4  out:12
    passthrough_schema  CC=2  out:1
    python_package_bindings  CC=4  out:6
  adapters.python.urirun.runtime.v2_grpc  [8 funcs]
    _method  CC=2  out:1
    _route_list  CC=2  out:5
    _validate  CC=5  out:4
    call  CC=6  out:7
    channel_target  CC=3  out:3
    list_routes  CC=1  out:3
    serve  CC=2  out:17
    stream  CC=4  out:7
  adapters.python.urirun.runtime.v2_mcp  [10 funcs]
    _input_schema  CC=4  out:3
    build_tool_index  CC=2  out:1
    call_tool  CC=3  out:4
    main  CC=9  out:16
    serve_mcp  CC=15  out:23
    to_a2a_card  CC=4  out:10
    to_mcp_manifest  CC=4  out:2
    to_mcp_tools  CC=4  out:8
    tool_name  CC=1  out:4
    unique_tool_name  CC=7  out:9
  adapters.python.urirun.runtime.v2_service  [3 funcs]
    _post  CC=3  out:10
    call  CC=9  out:10
    service_base  CC=3  out:4
  adapters.ts.urirun  [2 funcs]
    document  CC=1  out:0
    toJSON  CC=1  out:2
  v1.js.urirun-v1  [34 funcs]
    DEFAULT_TIMEOUT  CC=5  out:11
    OUTPUT_LIMIT  CC=5  out:11
    allow  CC=2  out:2
    check  CC=5  out:7
    compileRegistry  CC=1  out:2
    compileRegistryDocument  CC=5  out:3
    defaultAdapter  CC=2  out:0
    deny  CC=2  out:2
    envFlags  CC=3  out:4
    evaluatePolicy  CC=6  out:4

EDGES:
  adapters.ts.urirun.Connector.toJSON → adapters.ts.urirun.Connector.document
  adapters.js.parseUri → adapters.js.match
  adapters.js.dispatch → adapters.js.parseUri
  adapters.js.dispatch → adapters.js.buildInvocation
  adapters.js.dispatch → adapters.js.fn
  adapters.php.Urirun.Urirun.Connector.bindingsJson → adapters.php.Urirun.Urirun.Connector.bindings
  adapters.c.urirun.urirun_parse → adapters.c.urirun.memset
  adapters.c.urirun.urirun_parse → adapters.c.urirun.copy_token
  adapters.c.urirun.urirun_parse → adapters.c.urirun.is_path_end
  adapters.c.urirun_test.main → adapters.c.urirun_test.assert
  adapters.c.urirun.copy_token → adapters.c.urirun.memcpy
  adapters.c.urirun.memcpy → adapters.c.urirun.is_path_end
  adapters.go.urirun.BindingsJSON → adapters.go.urirun.Bindings
  adapters.python.urirun.host.scheduler.systemd_units → adapters.python.urirun.host.scheduler.shell_join
  adapters.python.urirun.host.scheduler.cron_line → adapters.python.urirun.host.scheduler.shell_join
  adapters.python.urirun.host.scheduler.preview → adapters.python.urirun.host.scheduler.build_loop_command
  adapters.python.urirun.host.scheduler.preview → adapters.python.urirun.host.scheduler.shell_join
  adapters.python.urirun.host.scheduler.preview → adapters.python.urirun.host.scheduler.systemd_units
  adapters.python.urirun.host.scheduler.preview → adapters.python.urirun.host.scheduler.cron_line
  adapters.python.urirun.runtime.v2_service.call → adapters.python.urirun.runtime.v2_service._post
  adapters.python.urirun.runtime.v2_service.call → adapters.python.urirun.runtime.v2_service.service_base
  adapters.python.urirun.host.planfile_adapter.load_planfile → adapters.python.urirun.host.planfile_adapter.project_root
  adapters.python.urirun.host.planfile_adapter.load_planfile → adapters.python.urirun.host.planfile_adapter._imports
  adapters.python.urirun.host.planfile_adapter.ticket_to_dict → adapters.python.urirun.host.planfile_adapter._model_dict
  adapters.python.urirun.host.planfile_adapter.build_ticket_payload → adapters.python.urirun.host.planfile_adapter._imports
  adapters.python.urirun.host.planfile_adapter.build_ticket_payload → adapters.python.urirun.host.planfile_adapter.normalize_priority
  adapters.python.urirun.host.planfile_adapter.create_ticket → adapters.python.urirun.host.planfile_adapter.load_planfile
  adapters.python.urirun.host.planfile_adapter.create_ticket → adapters.python.urirun.host.planfile_adapter.build_ticket_payload
  adapters.python.urirun.host.planfile_adapter.create_ticket → adapters.python.urirun.host.planfile_adapter.ticket_to_dict
  adapters.python.urirun.host.planfile_adapter.list_tickets → adapters.python.urirun.host.planfile_adapter.load_planfile
  adapters.python.urirun.host.planfile_adapter.list_tickets → adapters.python.urirun.host.planfile_adapter.ticket_to_dict
  adapters.python.urirun.host.planfile_adapter.next_ticket → adapters.python.urirun.host.planfile_adapter.ticket_to_dict
  adapters.python.urirun.host.planfile_adapter.next_ticket → adapters.python.urirun.host.planfile_adapter.load_planfile
  adapters.python.urirun.host.planfile_adapter.get_ticket → adapters.python.urirun.host.planfile_adapter.ticket_to_dict
  adapters.python.urirun.host.planfile_adapter.get_ticket → adapters.python.urirun.host.planfile_adapter.load_planfile
  adapters.python.urirun.host.planfile_adapter.claim_ticket → adapters.python.urirun.host.planfile_adapter.ticket_to_dict
  adapters.python.urirun.host.planfile_adapter.claim_ticket → adapters.python.urirun.host.planfile_adapter.load_planfile
  adapters.python.urirun.host.planfile_adapter.start_ticket → adapters.python.urirun.host.planfile_adapter.ticket_to_dict
  adapters.python.urirun.host.planfile_adapter.start_ticket → adapters.python.urirun.host.planfile_adapter.load_planfile
  adapters.python.urirun.host.planfile_adapter.complete_ticket → adapters.python.urirun.host.planfile_adapter.ticket_to_dict
  adapters.python.urirun.host.planfile_adapter.complete_ticket → adapters.python.urirun.host.planfile_adapter.load_planfile
  adapters.python.urirun.host.planfile_adapter.fail_ticket → adapters.python.urirun.host.planfile_adapter.ticket_to_dict
  adapters.python.urirun.host.planfile_adapter.fail_ticket → adapters.python.urirun.host.planfile_adapter.load_planfile
  adapters.python.urirun.host.planfile_adapter.fail_or_retry → adapters.python.urirun.host.planfile_adapter.load_planfile
  adapters.python.urirun.host.planfile_adapter.fail_or_retry → adapters.python.urirun.host.planfile_adapter.ticket_to_dict
  adapters.python.urirun.host.planfile_adapter.update_ticket → adapters.python.urirun.host.planfile_adapter.normalize_priority
  adapters.python.urirun.host.planfile_adapter.update_ticket → adapters.python.urirun.host.planfile_adapter.ticket_to_dict
  adapters.python.urirun.host.planfile_adapter.update_ticket → adapters.python.urirun.host.planfile_adapter.load_planfile
  adapters.python.urirun.host.planfile_adapter.wait_for_input → adapters.python.urirun.host.planfile_adapter.ticket_to_dict
  adapters.python.urirun.host.planfile_adapter.wait_for_input → adapters.python.urirun.host.planfile_adapter.load_planfile
```

## Test Contracts

*Scenarios as contract signatures — what the system guarantees.*

### Integration (1)

**`Auto-generated from Python Tests`**

## Refactoring Analysis

*Pre-refactoring snapshot — use this section to identify targets. Generated from `project/` toon files.*

### Call Graph & Complexity (`project/calls.toon.yaml`)

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/if-uri/urirun
# generated in 0.18s
# nodes: 403 | edges: 500 | modules: 31
# CC̄=4.4

HUBS[20]:
  adapters.python.urirun.host.host_integrations.run_planfile_task
    CC=31  in:0  out:66  total:66
  adapters.python.urirun.host.domain_monitor.run_uri_route
    CC=46  in:0  out:57  total:57
  adapters.python.urirun.host.host_dashboard.create_handler
    CC=1  in:1  out:52  total:53
  adapters.python.urirun.host.host_db.run_uri_route
    CC=45  in:0  out:45  total:45
  adapters.python.urirun.host.planfile_adapter.build_ticket_payload
    CC=35  in:1  out:43  total:44
  adapters.python.urirun.runtime.v2.run
    CC=18  in:1  out:35  total:36
  adapters.python.urirun.runtime._scan.scan_path
    CC=15  in:4  out:27  total:31
  adapters.python.urirun.runtime._scan.normalize_binding
    CC=11  in:17  out:12  total:29
  adapters.python.urirun.runtime.errors.info
    CC=13  in:2  out:27  total:29
  adapters.python.urirun.runtime.v2.run_error_store
    CC=23  in:0  out:28  total:28
  adapters.python.urirun.connectors.connect_catalog.diff_manifest
    CC=18  in:1  out:27  total:28
  adapters.python.urirun.host.host_dashboard.summary
    CC=6  in:1  out:25  total:26
  adapters.python.urirun.host.host_dashboard._json_response
    CC=1  in:13  out:13  total:26
  adapters.python.urirun.runtime.v2.validate_binding_document
    CC=12  in:1  out:24  total:25
  adapters.python.urirun.connectors.connect_catalog._cmd_show
    CC=9  in:0  out:25  total:25
  adapters.python.urirun.runtime.v1.run
    CC=14  in:2  out:23  total:25
  adapters.python.urirun.runtime._runtime.run
    CC=10  in:1  out:23  total:24
  adapters.python.urirun.runtime.v2_mcp.serve_mcp
    CC=15  in:1  out:23  total:24
  adapters.python.urirun.runtime.errors.main
    CC=16  in:0  out:23  total:23
  adapters.python.urirun.runtime.v2.scan_artifacts
    CC=11  in:4  out:19  total:23

MODULES:
  adapters.c.urirun  [5 funcs]
    copy_token  CC=2  out:1
    is_path_end  CC=3  out:0
    memcpy  CC=1  out:1
    memset  CC=5  out:0
    urirun_parse  CC=20  out:5
  adapters.c.urirun_test  [2 funcs]
    assert  CC=1  out:0
    main  CC=2  out:3
  adapters.go.urirun  [2 funcs]
    Bindings  CC=1  out:1
    BindingsJSON  CC=1  out:4
  adapters.java.Urirun  [1 funcs]
    Connector  CC=1  out:0
  adapters.js  [5 funcs]
    buildInvocation  CC=1  out:2
    dispatch  CC=3  out:4
    fn  CC=2  out:1
    match  CC=2  out:1
    parseUri  CC=8  out:9
  adapters.php.Urirun  [2 funcs]
    bindings  CC=1  out:0
    bindingsJson  CC=1  out:2
  adapters.python.urirun  [7 funcs]
    build_invocation  CC=1  out:2
    command  CC=1  out:1
    connector  CC=2  out:2
    dispatch  CC=4  out:10
    load_manifest  CC=1  out:1
    parse_uri  CC=7  out:13
    shell  CC=1  out:1
  adapters.python.urirun.connectors.connect_catalog  [13 funcs]
    _cmd_check  CC=7  out:15
    _cmd_install  CC=13  out:14
    _cmd_list  CC=9  out:20
    _cmd_show  CC=9  out:25
    _connectors  CC=2  out:3
    _emit_json  CC=1  out:2
    _find  CC=3  out:3
    _get_json  CC=2  out:5
    diff_manifest  CC=18  out:27
    fetch_catalog  CC=1  out:3
  adapters.python.urirun.connectors.connector_scaffold  [10 funcs]
    _go_files  CC=1  out:1
    _js_files  CC=1  out:2
    _manifest  CC=1  out:3
    _php_files  CC=1  out:1
    _pkg_module  CC=1  out:1
    _python_files  CC=1  out:2
    _scheme  CC=2  out:1
    _write  CC=2  out:5
    new_command  CC=3  out:7
    scaffold  CC=3  out:7
  adapters.python.urirun.connectors.connector_sdk  [2 funcs]
    connector_cli  CC=5  out:11
    emit  CC=1  out:2
  adapters.python.urirun.connectors.connector_smoke  [3 funcs]
    _load  CC=3  out:4
    smoke  CC=6  out:20
    smoke_command  CC=2  out:4
  adapters.python.urirun.host.domain_monitor  [14 funcs]
    _domain  CC=2  out:2
    _list  CC=6  out:8
    _namecheap_moved  CC=1  out:1
    _provider  CC=4  out:5
    capture_screenshot_artifact  CC=3  out:8
    check_domain  CC=16  out:19
    default_url  CC=2  out:1
    dns_mismatches  CC=4  out:5
    dns_records  CC=11  out:8
    expected_records  CC=8  out:15
  adapters.python.urirun.host.host_dashboard  [11 funcs]
    _host_db  CC=1  out:0
    _html_response  CC=1  out:9
    _json_response  CC=1  out:13
    _mesh  CC=1  out:0
    _planfile_adapter  CC=1  out:0
    _safe_tickets  CC=2  out:3
    command  CC=8  out:5
    create_handler  CC=1  out:52
    serve  CC=1  out:7
    summary  CC=6  out:25
  adapters.python.urirun.host.host_db  [26 funcs]
    _schema_json  CC=2  out:2
    _validate_record  CC=2  out:3
    add_check  CC=2  out:9
    add_llm_message  CC=2  out:9
    add_log  CC=2  out:9
    connect  CC=1  out:5
    connection  CC=1  out:3
    create_dataset  CC=1  out:7
    create_llm_session  CC=1  out:8
    db_path  CC=2  out:3
  adapters.python.urirun.host.host_integrations  [4 funcs]
    _planfile_action  CC=7  out:1
    _planfile_project  CC=4  out:5
    _simulate_planfile  CC=1  out:3
    run_planfile_task  CC=31  out:66
  adapters.python.urirun.host.planfile_adapter  [20 funcs]
    _imports  CC=2  out:1
    _model_dict  CC=1  out:1
    build_ticket_payload  CC=35  out:43
    claim_ticket  CC=2  out:3
    complete_ticket  CC=2  out:3
    create_ticket  CC=3  out:7
    fail_or_retry  CC=4  out:11
    fail_ticket  CC=2  out:3
    get_ticket  CC=2  out:3
    list_tickets  CC=9  out:5
  adapters.python.urirun.host.scheduler  [5 funcs]
    build_loop_command  CC=4  out:4
    cron_line  CC=1  out:4
    preview  CC=3  out:5
    shell_join  CC=2  out:2
    systemd_units  CC=2  out:1
  adapters.python.urirun.node.mesh  [25 funcs]
    add_node  CC=4  out:7
    append_if_available  CC=5  out:6
    binding_for_remote_route  CC=3  out:5
    default_host_config  CC=3  out:3
    default_node_config  CC=2  out:1
    discover_mesh  CC=7  out:8
    discover_node  CC=2  out:9
    first_url  CC=2  out:2
    heuristic_flow  CC=19  out:16
    host_config_path  CC=2  out:2
  adapters.python.urirun.runtime._registry  [35 funcs]
    _default_openapi_route  CC=9  out:11
    _discover_python_module  CC=1  out:2
    _emit_json  CC=3  out:3
    _get_route_entry  CC=1  out:0
    _iter_module_exports  CC=6  out:8
    _load_sources  CC=2  out:3
    _operation_from_method  CC=1  out:1
    _route_entry_equal  CC=2  out:2
    _walk_route_entries  CC=5  out:3
    add_route  CC=5  out:6
  adapters.python.urirun.runtime._runtime  [11 funcs]
    _matches_any  CC=3  out:1
    _truncate  CC=3  out:2
    check  CC=1  out:7
    default_policy  CC=1  out:0
    evaluate_policy  CC=16  out:19
    list_routes  CC=4  out:10
    merge_policy  CC=7  out:8
    run  CC=10  out:23
    run_local_function  CC=2  out:6
    run_shell_template  CC=3  out:11
  adapters.python.urirun.runtime._scan  [33 funcs]
    _read_toml  CC=12  out:17
    binding_to_route_source  CC=3  out:3
    build_binding_document  CC=3  out:6
    compile_registry_document  CC=4  out:5
    emit_json  CC=3  out:3
    github_dependency_binding  CC=4  out:3
    infer_kind  CC=12  out:11
    iter_project_files  CC=5  out:4
    list_bindings  CC=2  out:3
    load_binding_source  CC=5  out:11
  adapters.python.urirun.runtime.compat  [6 funcs]
    _entry_point_names  CC=4  out:5
    _importable  CC=3  out:1
    _print_table  CC=10  out:17
    main  CC=4  out:12
    module_status  CC=8  out:9
    report  CC=8  out:7
  adapters.python.urirun.runtime.errors  [20 funcs]
    _aggregate  CC=4  out:13
    _append  CC=3  out:13
    _load  CC=5  out:7
    _normalize_message  CC=2  out:6
    address  CC=1  out:0
    capture  CC=1  out:9
    category_meta  CC=1  out:1
    classify  CC=36  out:5
    error_code  CC=1  out:4
    fix_hints  CC=5  out:11
  adapters.python.urirun.runtime.v1  [19 funcs]
    _binding_pairs  CC=8  out:11
    _env_flags  CC=3  out:5
    _has_placeholders  CC=2  out:3
    _params_spec  CC=4  out:3
    _proc_env  CC=3  out:6
    _run_process  CC=1  out:8
    compile_registry  CC=1  out:2
    expand_binding  CC=7  out:6
    expand_bindings  CC=2  out:2
    load_registry_arg  CC=4  out:9
  adapters.python.urirun.runtime.v2  [60 funcs]
    _apply_defaults  CC=14  out:12
    _binding_pairs  CC=8  out:11
    _bindings_as_map  CC=2  out:2
    _coerce_default  CC=4  out:3
    _document_binding_from_expanded  CC=4  out:5
    _empty_input_schema  CC=1  out:0
    _first_payload_value  CC=3  out:1
    _host_integrations  CC=1  out:0
    _input_values  CC=4  out:8
    _iter_files  CC=5  out:4
  adapters.python.urirun.runtime.v2_adopt  [5 funcs]
    _command_binding  CC=2  out:2
    installed_python_bindings  CC=4  out:3
    npm_package_bindings  CC=4  out:12
    passthrough_schema  CC=2  out:1
    python_package_bindings  CC=4  out:6
  adapters.python.urirun.runtime.v2_grpc  [8 funcs]
    _method  CC=2  out:1
    _route_list  CC=2  out:5
    _validate  CC=5  out:4
    call  CC=6  out:7
    channel_target  CC=3  out:3
    list_routes  CC=1  out:3
    serve  CC=2  out:17
    stream  CC=4  out:7
  adapters.python.urirun.runtime.v2_mcp  [10 funcs]
    _input_schema  CC=4  out:3
    build_tool_index  CC=2  out:1
    call_tool  CC=3  out:4
    main  CC=9  out:16
    serve_mcp  CC=15  out:23
    to_a2a_card  CC=4  out:10
    to_mcp_manifest  CC=4  out:2
    to_mcp_tools  CC=4  out:8
    tool_name  CC=1  out:4
    unique_tool_name  CC=7  out:9
  adapters.python.urirun.runtime.v2_service  [3 funcs]
    _post  CC=3  out:10
    call  CC=9  out:10
    service_base  CC=3  out:4
  adapters.ts.urirun  [2 funcs]
    document  CC=1  out:0
    toJSON  CC=1  out:2
  v1.js.urirun-v1  [34 funcs]
    DEFAULT_TIMEOUT  CC=5  out:11
    OUTPUT_LIMIT  CC=5  out:11
    allow  CC=2  out:2
    check  CC=5  out:7
    compileRegistry  CC=1  out:2
    compileRegistryDocument  CC=5  out:3
    defaultAdapter  CC=2  out:0
    deny  CC=2  out:2
    envFlags  CC=3  out:4
    evaluatePolicy  CC=6  out:4

EDGES:
  adapters.ts.urirun.Connector.toJSON → adapters.ts.urirun.Connector.document
  adapters.js.parseUri → adapters.js.match
  adapters.js.dispatch → adapters.js.parseUri
  adapters.js.dispatch → adapters.js.buildInvocation
  adapters.js.dispatch → adapters.js.fn
  adapters.php.Urirun.Urirun.Connector.bindingsJson → adapters.php.Urirun.Urirun.Connector.bindings
  adapters.c.urirun.urirun_parse → adapters.c.urirun.memset
  adapters.c.urirun.urirun_parse → adapters.c.urirun.copy_token
  adapters.c.urirun.urirun_parse → adapters.c.urirun.is_path_end
  adapters.c.urirun_test.main → adapters.c.urirun_test.assert
  adapters.c.urirun.copy_token → adapters.c.urirun.memcpy
  adapters.c.urirun.memcpy → adapters.c.urirun.is_path_end
  adapters.go.urirun.BindingsJSON → adapters.go.urirun.Bindings
  adapters.python.urirun.host.scheduler.systemd_units → adapters.python.urirun.host.scheduler.shell_join
  adapters.python.urirun.host.scheduler.cron_line → adapters.python.urirun.host.scheduler.shell_join
  adapters.python.urirun.host.scheduler.preview → adapters.python.urirun.host.scheduler.build_loop_command
  adapters.python.urirun.host.scheduler.preview → adapters.python.urirun.host.scheduler.shell_join
  adapters.python.urirun.host.scheduler.preview → adapters.python.urirun.host.scheduler.systemd_units
  adapters.python.urirun.host.scheduler.preview → adapters.python.urirun.host.scheduler.cron_line
  adapters.python.urirun.runtime.v2_service.call → adapters.python.urirun.runtime.v2_service._post
  adapters.python.urirun.runtime.v2_service.call → adapters.python.urirun.runtime.v2_service.service_base
  adapters.python.urirun.host.planfile_adapter.load_planfile → adapters.python.urirun.host.planfile_adapter.project_root
  adapters.python.urirun.host.planfile_adapter.load_planfile → adapters.python.urirun.host.planfile_adapter._imports
  adapters.python.urirun.host.planfile_adapter.ticket_to_dict → adapters.python.urirun.host.planfile_adapter._model_dict
  adapters.python.urirun.host.planfile_adapter.build_ticket_payload → adapters.python.urirun.host.planfile_adapter._imports
  adapters.python.urirun.host.planfile_adapter.build_ticket_payload → adapters.python.urirun.host.planfile_adapter.normalize_priority
  adapters.python.urirun.host.planfile_adapter.create_ticket → adapters.python.urirun.host.planfile_adapter.load_planfile
  adapters.python.urirun.host.planfile_adapter.create_ticket → adapters.python.urirun.host.planfile_adapter.build_ticket_payload
  adapters.python.urirun.host.planfile_adapter.create_ticket → adapters.python.urirun.host.planfile_adapter.ticket_to_dict
  adapters.python.urirun.host.planfile_adapter.list_tickets → adapters.python.urirun.host.planfile_adapter.load_planfile
  adapters.python.urirun.host.planfile_adapter.list_tickets → adapters.python.urirun.host.planfile_adapter.ticket_to_dict
  adapters.python.urirun.host.planfile_adapter.next_ticket → adapters.python.urirun.host.planfile_adapter.ticket_to_dict
  adapters.python.urirun.host.planfile_adapter.next_ticket → adapters.python.urirun.host.planfile_adapter.load_planfile
  adapters.python.urirun.host.planfile_adapter.get_ticket → adapters.python.urirun.host.planfile_adapter.ticket_to_dict
  adapters.python.urirun.host.planfile_adapter.get_ticket → adapters.python.urirun.host.planfile_adapter.load_planfile
  adapters.python.urirun.host.planfile_adapter.claim_ticket → adapters.python.urirun.host.planfile_adapter.ticket_to_dict
  adapters.python.urirun.host.planfile_adapter.claim_ticket → adapters.python.urirun.host.planfile_adapter.load_planfile
  adapters.python.urirun.host.planfile_adapter.start_ticket → adapters.python.urirun.host.planfile_adapter.ticket_to_dict
  adapters.python.urirun.host.planfile_adapter.start_ticket → adapters.python.urirun.host.planfile_adapter.load_planfile
  adapters.python.urirun.host.planfile_adapter.complete_ticket → adapters.python.urirun.host.planfile_adapter.ticket_to_dict
  adapters.python.urirun.host.planfile_adapter.complete_ticket → adapters.python.urirun.host.planfile_adapter.load_planfile
  adapters.python.urirun.host.planfile_adapter.fail_ticket → adapters.python.urirun.host.planfile_adapter.ticket_to_dict
  adapters.python.urirun.host.planfile_adapter.fail_ticket → adapters.python.urirun.host.planfile_adapter.load_planfile
  adapters.python.urirun.host.planfile_adapter.fail_or_retry → adapters.python.urirun.host.planfile_adapter.load_planfile
  adapters.python.urirun.host.planfile_adapter.fail_or_retry → adapters.python.urirun.host.planfile_adapter.ticket_to_dict
  adapters.python.urirun.host.planfile_adapter.update_ticket → adapters.python.urirun.host.planfile_adapter.normalize_priority
  adapters.python.urirun.host.planfile_adapter.update_ticket → adapters.python.urirun.host.planfile_adapter.ticket_to_dict
  adapters.python.urirun.host.planfile_adapter.update_ticket → adapters.python.urirun.host.planfile_adapter.load_planfile
  adapters.python.urirun.host.planfile_adapter.wait_for_input → adapters.python.urirun.host.planfile_adapter.ticket_to_dict
  adapters.python.urirun.host.planfile_adapter.wait_for_input → adapters.python.urirun.host.planfile_adapter.load_planfile
```

### Code Analysis (`project/analysis.toon.yaml`)

```toon markpact:analysis path=project/analysis.toon.yaml
# code2llm | 96f 13352L | python:52,json:8,shell:5,yaml:4,csharp:4,javascript:3,toml:2,perl:2,rust:2,typescript:2,php:2,c:2,go:2,java:2,ruby:2,txt:1 | 2026-06-21
# generated in 0.02s
# CC̅=4.4 | critical:26/576 | dups:0 | cycles:0

HEALTH[20]:
  🟡 CC    urirun_parse CC=20 (limit:15)
  🟡 CC    main CC=17 (limit:15)
  🟡 CC    build_ticket_payload CC=35 (limit:15)
  🟡 CC    run_planfile_task CC=31 (limit:15)
  🟡 CC    check_domain CC=16 (limit:15)
  🟡 CC    run_uri_route CC=46 (limit:15)
  🟡 CC    run_uri_route CC=45 (limit:15)
  🟡 CC    serve_mcp CC=15 (limit:15)
  🟡 CC    diff_manifest CC=18 (limit:15)
  🟡 CC    resolveParams CC=15 (limit:15)
  🟡 CC    run CC=19 (limit:15)
  🟡 CC    evaluate_policy CC=16 (limit:15)
  🟡 CC    scan_path CC=15 (limit:15)
  🟡 CC    classify CC=36 (limit:15)
  🟡 CC    main CC=16 (limit:15)
  🟡 CC    run_error_store CC=23 (limit:15)
  🟡 CC    run CC=18 (limit:15)
  🟡 CC    expand_binding CC=16 (limit:15)
  🟡 CC    main CC=38 (limit:15)
  🟡 CC    heuristic_flow CC=19 (limit:15)

REFACTOR[1]:
  1. split 20 high-CC methods  (CC>15)

PIPELINES[172]:
  [1] Src [new]: new
      PURITY: 100% pure
  [2] Src [target]: target
      PURITY: 100% pure
  [3] Src [command]: command
      PURITY: 100% pure
  [4] Src [bindings_json]: bindings_json
      PURITY: 100% pure
  [5] Src [main]: main
      PURITY: 100% pure
  [6] Src [c]: c
      PURITY: 100% pure
  [7] Src [toJSON]: toJSON → document
      PURITY: 100% pure
  [8] Src [connector]: connector
      PURITY: 100% pure
  [9] Src [result]: result
      PURITY: 100% pure
  [10] Src [path]: path
      PURITY: 100% pure
  [11] Src [segments]: segments
      PURITY: 100% pure
  [12] Src [descriptor]: descriptor
      PURITY: 100% pure
  [13] Src [invocation]: invocation
      PURITY: 100% pure
  [14] Src [mod]: mod
      PURITY: 100% pure
  [15] Src [command]: command
      PURITY: 100% pure
  [16] Src [bindingsJson]: bindingsJson → bindings
      PURITY: 100% pure
  [17] Src [urirun_parse]: urirun_parse → memset
      PURITY: 100% pure
  [18] Src [main]: main → assert
      PURITY: 100% pure
  [19] Src [main]: main
      PURITY: 100% pure
  [20] Src [Target]: Target
      PURITY: 100% pure
  [21] Src [Command]: Command
      PURITY: 100% pure
  [22] Src [BindingsJSON]: BindingsJSON → Bindings
      PURITY: 100% pure
  [23] Src [main]: main
      PURITY: 100% pure
  [24] Src [command]: command
      PURITY: 100% pure
  [25] Src [bindingsJson]: bindingsJson
      PURITY: 100% pure
  [26] Src [main]: main → python_reference
      PURITY: 100% pure
  [27] Src [preview]: preview → build_loop_command
      PURITY: 100% pure
  [28] Src [install_systemd_user]: install_systemd_user
      PURITY: 100% pure
  [29] Src [call]: call → _post
      PURITY: 100% pure
  [30] Src [create_ticket]: create_ticket → load_planfile → project_root
      PURITY: 100% pure
  [31] Src [list_tickets]: list_tickets → load_planfile → project_root
      PURITY: 100% pure
  [32] Src [next_ticket]: next_ticket → ticket_to_dict → _model_dict
      PURITY: 100% pure
  [33] Src [get_ticket]: get_ticket → ticket_to_dict → _model_dict
      PURITY: 100% pure
  [34] Src [claim_ticket]: claim_ticket → ticket_to_dict → _model_dict
      PURITY: 100% pure
  [35] Src [start_ticket]: start_ticket → ticket_to_dict → _model_dict
      PURITY: 100% pure
  [36] Src [complete_ticket]: complete_ticket → ticket_to_dict → _model_dict
      PURITY: 100% pure
  [37] Src [fail_ticket]: fail_ticket → ticket_to_dict → _model_dict
      PURITY: 100% pure
  [38] Src [fail_or_retry]: fail_or_retry → load_planfile → project_root
      PURITY: 100% pure
  [39] Src [update_ticket]: update_ticket → normalize_priority
      PURITY: 100% pure
  [40] Src [wait_for_input]: wait_for_input → ticket_to_dict → _model_dict
      PURITY: 100% pure
  [41] Src [ready_ticket]: ready_ticket → ticket_to_dict → _model_dict
      PURITY: 100% pure
  [42] Src [run_dsl]: run_dsl → project_root
      PURITY: 100% pure
  [43] Src [loads_json]: loads_json
      PURITY: 100% pure
  [44] Src [planfile_task_bindings]: planfile_task_bindings
      PURITY: 100% pure
  [45] Src [run_planfile_task]: run_planfile_task → _planfile_action
      PURITY: 100% pure
  [46] Src [host_data_bindings]: host_data_bindings
      PURITY: 100% pure
  [47] Src [run_host_data]: run_host_data
      PURITY: 100% pure
  [48] Src [domain_monitor_bindings]: domain_monitor_bindings
      PURITY: 100% pure
  [49] Src [run_domain_monitor]: run_domain_monitor
      PURITY: 100% pure
  [50] Src [run_uri_route]: run_uri_route → _domain
      PURITY: 100% pure

LAYERS:
  adapters/                       CC̄=4.5    ←in:6  →out:0
  │ !! v2                        1602L  0C   66m  CC=38     ←1
  │ !! mesh                      1092L  0C   51m  CC=52     ←0
  │ !! _registry                  682L  0C   41m  CC=14     ←0
  │ !! _scan                      670L  0C   36m  CC=15     ←0
  │ !! host_dashboard             614L  0C   15m  CC=8      ←0
  │ !! errors                     511L  0C   21m  CC=36     ←0
  │ !! host_db                    475L  0C   27m  CC=45     ←0
  │ v1                         423L  0C   24m  CC=14     ←1
  │ !! _runtime                   422L  1C   18m  CC=16     ←1
  │ !! domain_monitor             393L  0C   18m  CC=46     ←0
  │ connector_scaffold         386L  0C   10m  CC=3      ←0
  │ !! host_integrations          382L  0C   11m  CC=31     ←0
  │ !! task_planner               344L  2C   13m  CC=22     ←0
  │ !! planfile_adapter           261L  1C   21m  CC=35     ←0
  │ __init__                   256L  1C   25m  CC=7      ←0
  │ !! connect_catalog            236L  0C   14m  CC=18     ←0
  │ v2_grpc                    205L  0C   11m  CC=9      ←0
  │ !! v2_mcp                     205L  0C   10m  CC=15     ←0
  │ compat                     199L  0C    6m  CC=10     ←0
  │ v2_adopt                   195L  0C    8m  CC=7      ←0
  │ new-connector.sh           168L  0C    1m  CC=0.0    ←0
  │ !! conformance                148L  0C    3m  CC=17     ←0
  │ scheduler                  133L  0C    6m  CC=4      ←0
  │ v2_service                 103L  0C    3m  CC=9      ←0
  │ connector_sdk               87L  0C    3m  CC=5      ←1
  │ connector_smoke             81L  0C    3m  CC=6      ←0
  │ urirun.go                   80L  3C    5m  CC=3      ←0
  │ Urirun.php                  73L  1C    5m  CC=3      ←0
  │ project.assets.json         71L  0C    0m  CC=0.0    ←0
  │ urirun-connector.csproj.nuget.dgspec.json    66L  0C    0m  CC=0.0    ←0
  │ pyproject.toml              60L  0C    0m  CC=0.0    ←0
  │ !! urirun.c                    56L  0C    5m  CC=20     ←0
  │ index.test.js               52L  0C    1m  CC=1      ←0
  │ Urirun.pm                   47L  0C    4m  CC=0.0    ←1
  │ urirun.ts                   41L  2C    4m  CC=4      ←0
  │ lib.rs                      39L  1C    4m  CC=1      ←0
  │ urirun.rb                   39L  1C    4m  CC=4      ←0
  │ Urirun.java                 38L  1C    3m  CC=1      ←1
  │ index.js                    33L  0C   11m  CC=8      ←6
  │ Urirun.cs                   32L  1C    3m  CC=1      ←0
  │ main.go                     24L  0C    1m  CC=1      ←0
  │ urirun-connector.AssemblyInfo.cs    22L  0C    0m  CC=0.0    ←0
  │ urirun_test.c               18L  0C    2m  CC=2      ←0
  │ urirun.sh                   17L  0C    2m  CC=0.0    ←0
  │ urirun-connector.csproj.FileListAbsolute.txt    15L  0C    0m  CC=0.0    ←0
  │ hash_connector.pl           14L  0C    0m  CC=0.0    ←0
  │ hash-connector.php          14L  0C    0m  CC=0.0    ←0
  │ hash_connector.rs           12L  0C    1m  CC=1      ←0
  │ HashConnector.java          11L  1C    1m  CC=1      ←0
  │ tsconfig.json               11L  0C    0m  CC=0.0    ←0
  │ hash-connector.ts           10L  0C    1m  CC=1      ←0
  │ package.json                10L  0C    0m  CC=0.0    ←0
  │ Cargo.toml                  10L  0C    0m  CC=0.0    ←0
  │ hash-connector.sh            9L  0C    0m  CC=0.0    ←0
  │ package.json                 8L  0C    0m  CC=0.0    ←0
  │ v2_service                   8L  0C    0m  CC=0.0    ←0
  │ v2_adopt                     8L  0C    0m  CC=0.0    ←0
  │ v2_mcp                       8L  0C    0m  CC=0.0    ←0
  │ _registry                    8L  0C    0m  CC=0.0    ←0
  │ compat                       8L  0C    0m  CC=0.0    ←0
  │ v2_grpc                      8L  0C    0m  CC=0.0    ←0
  │ _scan                        8L  0C    0m  CC=0.0    ←0
  │ errors                       8L  0C    0m  CC=0.0    ←0
  │ _runtime                     8L  0C    0m  CC=0.0    ←0
  │ v2                           8L  0C    0m  CC=0.0    ←0
  │ hash_connector.rb            8L  0C    0m  CC=0.0    ←0
  │ v1                           8L  0C    0m  CC=0.0    ←0
  │ composer.json                7L  0C    0m  CC=0.0    ←0
  │ Program.cs                   7L  0C    0m  CC=0.0    ←0
  │ host_dashboard               5L  0C    0m  CC=0.0    ←0
  │ connector_smoke              5L  0C    0m  CC=0.0    ←0
  │ planfile_adapter             5L  0C    0m  CC=0.0    ←0
  │ connector_scaffold           5L  0C    0m  CC=0.0    ←0
  │ task_planner                 5L  0C    0m  CC=0.0    ←0
  │ host_integrations            5L  0C    0m  CC=0.0    ←0
  │ host_db                      5L  0C    0m  CC=0.0    ←0
  │ connector_sdk                5L  0C    0m  CC=0.0    ←0
  │ scheduler                    5L  0C    0m  CC=0.0    ←0
  │ mesh                         5L  0C    0m  CC=0.0    ←0
  │ domain_monitor               5L  0C    0m  CC=0.0    ←0
  │ connect_catalog              5L  0C    0m  CC=0.0    ←0
  │ .NETCoreApp,Version=v8.0.AssemblyAttributes.cs     4L  0C    0m  CC=0.0    ←0
  │ __init__                     1L  0C    0m  CC=0.0    ←0
  │ __init__                     1L  0C    0m  CC=0.0    ←0
  │ __init__                     1L  0C    0m  CC=0.0    ←0
  │ __init__                     1L  0C    0m  CC=0.0    ←0
  │ urirun-connector.sourcelink.json     1L  0C    0m  CC=0.0    ←0
  │
  v1/                             CC̄=3.7    ←in:0  →out:0
  │ !! urirun-v1.js               334L  0C   54m  CC=19     ←4
  │
  ./                              CC̄=0.0    ←in:0  →out:0
  │ !! planfile.yaml              851L  0C    0m  CC=0.0    ←0
  │ !! goal.yaml                  526L  0C    0m  CC=0.0    ←0
  │ prefact.yaml                94L  0C    0m  CC=0.0    ←0
  │ project.sh                  66L  0C    0m  CC=0.0    ←0
  │ Makefile                    56L  0C    0m  CC=0.0    ←0
  │ package.json                27L  0C    0m  CC=0.0    ←0
  │ tree.sh                      4L  0C    0m  CC=0.0    ←0
  │
  testql-scenarios/               CC̄=0.0    ←in:0  →out:0
  │ generated-from-pytests.testql.toon.yaml    10L  0C    0m  CC=0.0    ←0
  │

COUPLING:
                   adapters.python         adapters            v1.js    adapters.java    adapters.perl
  adapters.python               ──                6                6                1                1  !! fan-out
         adapters               ←6               ──                                                     hub
            v1.js               ←6                                ──                                    hub
    adapters.java               ←1                                                 ──                 
    adapters.perl               ←1                                                                  ──
  CYCLES: none
  HUB: v1.js/ (fan-in=6)
  HUB: adapters/ (fan-in=6)
  SMELL: adapters.python/ fan-out=14 → split needed

EXTERNAL:
  validation: run `vallm batch .` → validation.toon
  duplication: run `redup scan .` → duplication.toon
```

### Duplication (`project/duplication.toon.yaml`)

```toon markpact:analysis path=project/duplication.toon.yaml
# redup/duplication | 0 groups | 1f 148L | 2026-06-21

SUMMARY:
  files_scanned: 1
  total_lines:   148
  dup_groups:    0
  dup_fragments: 0
  saved_lines:   0
  scan_ms:       2167
```

### Evolution / Churn (`project/evolution.toon.yaml`)

```toon markpact:analysis path=project/evolution.toon.yaml
# code2llm/evolution | 575 func | 43f | 2026-06-21
# generated in 0.00s

NEXT[10] (ranked by impact):
  [1] !! SPLIT           adapters/python/urirun/runtime/v2.py
      WHY: 1602L, 0 classes, max CC=38
      EFFORT: ~4h  IMPACT: 60876

  [2] !! SPLIT           adapters/python/urirun/node/mesh.py
      WHY: 1092L, 0 classes, max CC=52
      EFFORT: ~4h  IMPACT: 56784

  [3] !! SPLIT-FUNC      main  CC=38  fan=122
      WHY: CC=38 exceeds 15
      EFFORT: ~1h  IMPACT: 4636

  [4] !! SPLIT-FUNC      task_command  CC=52  fan=35
      WHY: CC=52 exceeds 15
      EFFORT: ~1h  IMPACT: 1820

  [5] !! SPLIT-FUNC      run_uri_route  CC=46  fan=23
      WHY: CC=46 exceeds 15
      EFFORT: ~1h  IMPACT: 1058

  [6] !! SPLIT-FUNC      run_uri_route  CC=45  fan=19
      WHY: CC=45 exceeds 15
      EFFORT: ~1h  IMPACT: 855

  [7] !! SPLIT-FUNC      run_planfile_task  CC=31  fan=25
      WHY: CC=31 exceeds 15
      EFFORT: ~1h  IMPACT: 775

  [8] !  SPLIT-FUNC      main  CC=17  fan=29
      WHY: CC=17 exceeds 15
      EFFORT: ~1h  IMPACT: 493

  [9] !! SPLIT-FUNC      build_ticket_payload  CC=35  fan=13
      WHY: CC=35 exceeds 15
      EFFORT: ~1h  IMPACT: 455

  [10] !  SPLIT-FUNC      run_error_store  CC=23  fan=15
      WHY: CC=23 exceeds 15
      EFFORT: ~1h  IMPACT: 345


RISKS[3]:
  ⚠ Splitting adapters/python/urirun/runtime/v2.py may break 66 import paths
  ⚠ Splitting adapters/python/urirun/node/mesh.py may break 51 import paths
  ⚠ Splitting planfile.yaml may break 0 import paths

METRICS-TARGET:
  CC̄:          4.4 → ≤3.1
  max-CC:      52 → ≤20
  god-modules: 8 → 0
  high-CC(≥15): 26 → ≤13
  hub-types:   0 → ≤0

PATTERNS (language parser shared logic):
  _extract_declarations() in base.py — unified extraction for:
    - TypeScript: interfaces, types, classes, functions, arrow funcs
    - PHP: namespaces, traits, classes, functions, includes
    - Ruby: modules, classes, methods, requires
    - C++: classes, structs, functions, #includes
    - C#: classes, interfaces, methods, usings
    - Java: classes, interfaces, methods, imports
    - Go: packages, functions, structs
    - Rust: modules, functions, traits, use statements

  Shared regex patterns per language:
    - import: language-specific import/require/using patterns
    - class: class/struct/trait declarations with inheritance
    - function: function/method signatures with visibility
    - brace_tracking: for C-family languages ({ })
    - end_keyword_tracking: for Ruby (module/class/def...end)

  Benefits:
    - Consistent extraction logic across all languages
    - Reduced code duplication (~70% reduction in parser LOC)
    - Easier maintenance: fix once, apply everywhere
    - Standardized FunctionInfo/ClassInfo models

HISTORY:
  prev CC̄=4.9 → now CC̄=4.4
```

## Intent

urirun
