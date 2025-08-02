import platform
import psutil
from utils.logging_utils import log_findings, write_action
import socket
import subprocess

def network_connectivity_check(log_folder, target="8.8.8.8"):
    """
    Simple network check by pinging a public IP (Google DNS by default).
    """
    os_name = platform.system()
    ping_count = "4"
    if os_name == "Windows":
        cmd = ["ping", "-n", ping_count, target]
    else:
        cmd = ["ping", "-c", ping_count, target]

    print(f"=== Running Network Connectivity Check (ping {target}) ===")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(proc.stdout)
        write_action(f"Network connectivity check passed for {target}", log_folder, level="INFO")
        return {"tool": "Network Connectivity Check", "status": "OK", "details": f"Ping to {target} succeeded"}
    except subprocess.CalledProcessError as e:
        error_msg = f"Ping failed: {e.stderr.strip()}"
        print(error_msg)
        write_action(error_msg, log_folder, level="ERROR")
        return {"tool": "Network Connectivity Check", "status": "FAIL", "details": error_msg}


def cpu_memory_snapshot():
    """
    Returns current CPU and memory usage metrics.
    """
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    return {
        "cpu_percent": cpu,
        "memory_percent": mem.percent,
        "memory_total_gb": round(mem.total / (1024**3), 2),
        "memory_used_gb": round(mem.used / (1024**3), 2),
    }


def run_investigation(log_folder, disk_threshold=85):
    print("=== Starting Automated Investigation ===")
    write_action("Automated investigation started", log_folder, level="INFO")

    # Lazy import to avoid circular imports
    from system_tool.system_tools import investigate_disk_usage, resource_monitor

    findings = []

    # Disk Usage Investigation
    disk_findings = investigate_disk_usage(threshold=disk_threshold)
    log_findings(disk_findings, log_folder)
    findings.extend(disk_findings)

    # Resource Snapshot (CPU, Memory, Disk)
    try:
        resource_monitor(log_folder)
        write_action("Resource monitor ran successfully", log_folder, level="INFO")
    except Exception as e:
        write_action(f"Resource monitor failed: {e}", log_folder, level="ERROR")

    # Network Connectivity Check
    net_check = network_connectivity_check(log_folder)
    findings.append(net_check)

    # Summarize CPU and Memory snapshot
    metrics = cpu_memory_snapshot()
    metrics_summary = (
        f"CPU Usage: {metrics['cpu_percent']}%\n"
        f"Memory Usage: {metrics['memory_percent']}% ({metrics['memory_used_gb']}/{metrics['memory_total_gb']} GB)"
    )
    print(f"=== CPU & Memory Snapshot ===\n{metrics_summary}")
    write_action(f"CPU & Memory snapshot:\n{metrics_summary}", log_folder, level="INFO")

    # Placeholder for future investigations
    print("\n=== Additional probes can be added here ===")

    print("=== Investigation Complete ===")
    write_action("Automated investigation completed", log_folder, level="INFO")

    return findings

def run(log_folder):
    run_investigation(log_folder)



if __name__ == "__main__":
    import os
    logs_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    run_investigation(logs_dir)
