# Integration-layer CLI moved to urirun.host.task_cli (Phase 5).
# This shim re-exports everything so existing callers keep working unchanged.
from urirun.host.task_cli import *  # noqa: F401,F403
from urirun.host.task_cli import (  # noqa: F401 (explicit for type checkers)
    task_command,
    _TASK_COMMANDS,
    _task_plan, _task_bindings, _task_schedule, _task_list, _task_show,
    _task_next, _task_create, _task_claim, _task_start, _task_complete,
    _task_fail, _task_block, _task_ready, _task_wait, _task_dsl,
    _task_run, _task_loop, _run_task_flow, _task_prompt,
)
