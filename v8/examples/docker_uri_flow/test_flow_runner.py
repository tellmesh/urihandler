from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / "orchestrator" / "flow_runner.py"
FLOW = ROOT / "flows" / "cross_service_report.yaml"


def load_runner():
    spec = importlib.util.spec_from_file_location("flow_runner", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_compact_uri_flow():
    runner = load_runner()
    flow = runner.parse_flow(FLOW)

    assert flow["task"]["id"] == "docker-cross-service-report"
    assert [step["id"] for step in flow["steps"]] == [
        "normalize_text",
        "slugify_text",
        "write_report",
        "summarize_report",
    ]
    assert flow["steps"][2]["payload"]["slug_from"] == "slugify_text.result.slug"


if __name__ == "__main__":
    test_parse_compact_uri_flow()
    print("PASS docker_uri_flow parser")
