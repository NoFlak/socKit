"""Workflow orchestration for the socKit automation platform."""

from __future__ import annotations

import inspect
import os
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

import yaml

from logging_utils import write_action
from config import load_config


TaskCallable = Callable[..., Any]
TASK_REGISTRY: Dict[str, TaskCallable] = {}


class WorkflowError(Exception):
    """Raised when a workflow fails to execute."""


def register_task(name: str, func: TaskCallable) -> None:
    """Register a callable as an automation task."""

    TASK_REGISTRY[name] = func


def list_tasks() -> List[str]:
    return sorted(TASK_REGISTRY.keys())


def _call_task(name: str, kwargs: Dict[str, Any]) -> Any:
    if name not in TASK_REGISTRY:
        raise WorkflowError(f"Task '{name}' is not registered.")

    func = TASK_REGISTRY[name]
    signature = inspect.signature(func)
    filtered_kwargs = {k: v for k, v in kwargs.items() if k in signature.parameters}

    try:
        result = func(**filtered_kwargs)
        write_action(
            "Workflow task executed.",
            context={"task": name, "provided_args": list(kwargs.keys()), "used_args": list(filtered_kwargs.keys())},
        )
        return result
    except Exception as exc:  # noqa: BLE001
        write_action(
            "Workflow task failed.",
            level="ERROR",
            context={"task": name, "error": str(exc)},
        )
        raise WorkflowError(f"Task '{name}' raised an exception: {exc}") from exc


def load_playbook(path: str | os.PathLike[str]) -> Dict[str, Any]:
    playbook_path = Path(path)
    if not playbook_path.exists():
        raise WorkflowError(f"Playbook {playbook_path} not found.")

    try:
        with playbook_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise WorkflowError("Playbook root must be a mapping/dictionary.")
        return data
    except yaml.YAMLError as exc:
        raise WorkflowError(f"Invalid YAML in playbook {playbook_path}: {exc}") from exc


def run_playbook(path: str | os.PathLike[str], *, dry_run: bool = False) -> List[Any]:
    playbook = load_playbook(path)
    steps = playbook.get("steps", [])
    if not isinstance(steps, list):
        raise WorkflowError("Playbook 'steps' must be a list.")

    results: List[Any] = []
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict) or "task" not in step:
            raise WorkflowError(f"Invalid step at position {index}: {step}")
        task_name = step["task"]
        args = step.get("args", {})
        print(f"\n[PLAYBOOK] Step {index}: {task_name}")
        if dry_run:
            print(f"  Dry run - would execute with args: {args}")
            continue
        result = _call_task(task_name, args)
        results.append(result)

    write_action("Playbook execution complete.", context={"path": str(path), "steps": len(steps)})
    return results


def bootstrap_builtin_tasks() -> None:
    """Register default tasks from toolkit modules."""

    # Import locally to avoid circular dependencies during module import.
    from system_tools import display_system_overview, enumerate_services, list_critical_paths, system_file_checker
    from network_tools import dns_health_check, ping_test, tcp_port_scan
    from blue_team import (  # noqa: F401
        backup_verification,
        event_log_analyzer,
        file_integrity_checker,
        firewall_av_status_checker,
        network_share_auditor,
        patch_status_checker,
        service_process_monitor,
        shadow_file_management,
        user_session_tracker,
    )
    from red_team import credential_dump_simulation, lateral_movement_simulation, persistence_checker, privilege_escalation_checker
    from purple_team import dashboard_report, log_correlation_engine, mitre_attack_mapping
    from system_tool.system_tools import (
        scan_and_repair,
        package_repair,
        disk_cleanup,
        network_reset,
        resource_monitor,
        gpu_usage_monitor,
        thermal_sensor_check,
        startup_program_auditor,
        scheduled_task_auditor,
        power_settings_optimizer,
    )

    # Wrapper to inject log_folder for system_tool tasks
    def _with_log_folder(func: Callable[..., Any]) -> TaskCallable:
        def runner() -> Any:
            cfg = load_config()
            return func(cfg.log_folder)
        return runner

    task_map = {
        "system.overview": display_system_overview,
        "system.services": enumerate_services,
        "system.paths": list_critical_paths,
        "system.sfc": system_file_checker,
        "network.ping": ping_test,
        "network.dns_health": dns_health_check,
        "network.tcp_scan": tcp_port_scan,
        "blue.shadow": shadow_file_management,
        "blue.event_logs": event_log_analyzer,
        "blue.network_shares": network_share_auditor,
        "blue.patch_status": patch_status_checker,
        "blue.file_integrity": file_integrity_checker,
        "blue.services": service_process_monitor,
        "blue.backup": backup_verification,
        "blue.sessions": user_session_tracker,
        "blue.firewall": firewall_av_status_checker,
        "red.credential_exposure": credential_dump_simulation,
        "red.lateral_movement": lateral_movement_simulation,
        "red.persistence": persistence_checker,
        "red.privilege": privilege_escalation_checker,
        "purple.dashboard": dashboard_report,
        "purple.correlation": log_correlation_engine,
        "purple.mitre_mapping": mitre_attack_mapping,
        # Detailed system toolkit tasks
        "system.repair_all": _with_log_folder(scan_and_repair),
        "system.package_repair": _with_log_folder(package_repair),
        "system.disk_cleanup": _with_log_folder(disk_cleanup),
        "system.network_reset": _with_log_folder(network_reset),
        "system.resource_monitor": _with_log_folder(resource_monitor),
        "system.gpu_monitor": _with_log_folder(gpu_usage_monitor),
        "system.thermal_check": _with_log_folder(thermal_sensor_check),
        "system.startup_auditor": _with_log_folder(startup_program_auditor),
        "system.scheduled_tasks": _with_log_folder(scheduled_task_auditor),
        "system.power_settings": _with_log_folder(power_settings_optimizer),
    }

    for name, func in task_map.items():
        register_task(name, func)


def ensure_playbook(path: str | os.PathLike[str], *, overwrite: bool = False) -> Path:
    """Create a starter playbook if it does not already exist."""

    playbook_path = Path(path)
    if playbook_path.exists() and not overwrite:
        return playbook_path

    sample_playbook = {
        "name": "Quick Health Check",
        "description": "Baseline system/network checks to validate readiness.",
        "steps": [
            {"task": "system.overview"},
            {"task": "network.ping", "args": {"target": "8.8.8.8", "count": 2}},
            {"task": "network.dns_health", "args": {"domains": ["example.com", "google.com"]}},
            {"task": "blue.shadow"},
            {"task": "purple.dashboard"},
        ],
    }

    playbook_path.parent.mkdir(parents=True, exist_ok=True)
    with playbook_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(sample_playbook, handle, sort_keys=False)
    write_action("Sample playbook created.", context={"path": str(playbook_path)})
    return playbook_path
