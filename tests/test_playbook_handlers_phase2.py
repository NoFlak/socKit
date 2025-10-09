from playbooks import handlers
from tools import validate_tools


def test_nmap_handler_dry_run(tmp_path):
    artifact = handlers.nmap_top_ports(target="127.0.0.1", operator="tester", artifact_base=tmp_path)
    assert artifact["operator"] == "tester"
    assert artifact["dry_run"] is True
    json_dir = tmp_path / "json"
    assert any(json_dir.rglob("*.json"))


def test_osquery_handler_dry_run(tmp_path):
    artifact = handlers.osquery_snapshot(operator="tester", artifact_base=tmp_path)
    assert artifact["tool"] == "osquery_snapshot"
    assert artifact["dry_run"] is True


def test_tcpdump_handler_dry_run(tmp_path):
    artifact = handlers.tcpdump_capture(operator="tester", artifact_base=tmp_path)
    assert artifact["tool"] == "tcpdump_capture"
    assert artifact["dry_run"] is True


def test_placeholder_validation_passes():
    validate_tools.check_placeholders()


def test_system_task_validation_detects_present_functions():
    validate_tools.ensure_system_tasks(create_stubs=False)
