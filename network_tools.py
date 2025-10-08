"""Network diagnostics and automation helpers."""

from __future__ import annotations

import getpass
import platform
import shutil
import socket
import statistics
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from command_utils import execute_command
from logging_utils import log_table, write_action

tested_devices: set[str] = set()


@dataclass
class PingStatistics:
    target: str
    minimum_ms: float
    maximum_ms: float
    average_ms: float
    packet_loss: float


def _resolve_target(target: str) -> Tuple[Optional[str], Optional[str]]:
    resolved_name = None
    resolved_ip = None
    try:
        resolved_name = socket.gethostbyaddr(target)[0]
    except socket.herror:
        pass
    except OSError as exc:
        print(f"[WARN] Reverse lookup failed for {target}: {exc}")

    try:
        resolved_ip = socket.gethostbyname(target)
    except socket.gaierror:
        pass
    except OSError as exc:
        print(f"[WARN] Forward lookup failed for {target}: {exc}")

    return resolved_name, resolved_ip


def _parse_ping_output(output: str) -> Optional[PingStatistics]:
    lines = output.splitlines()
    latencies: List[float] = []
    packet_loss = 0.0
    for line in lines:
        if "time=" in line:
            try:
                fragment = line.split("time=")[1]
                value = fragment.split()[0]
                latencies.append(float(value.replace("ms", "")))
            except (IndexError, ValueError):
                continue
        elif "loss" in line.lower() or "packet loss" in line.lower():
            numbers = [token.strip("%") for token in line.split() if token.strip("%") and token.replace("%", "").isdigit()]
            for token in numbers:
                try:
                    packet_loss = float(token)
                except ValueError:
                    continue

    if not latencies:
        return None

    return PingStatistics(
        target="",
        minimum_ms=min(latencies),
        maximum_ms=max(latencies),
        average_ms=statistics.mean(latencies),
        packet_loss=packet_loss,
    )


def ping_test(target: Optional[str] = None, *, count: int = 4) -> Optional[PingStatistics]:
    target = target or input("Enter the target hostname or IP address for Ping Test: ").strip()
    user = getpass.getuser()
    resolved_name, resolved_ip = _resolve_target(target)

    if resolved_name:
        print(f"[INFO] DNS Name for {target}: {resolved_name}")
    if resolved_ip:
        print(f"[INFO] IP Address for {target}: {resolved_ip}")

    device_id = resolved_name or resolved_ip or target
    if device_id not in tested_devices:
        write_action("First connectivity test on device.", context={"device": device_id, "user": user})
        tested_devices.add(device_id)

    os_name = platform.system()
    if os_name == "Windows":
        command = f"ping -n {count} {target}"
    else:
        command = f"ping -c {count} {target}"

    result = execute_command(command, f"Ping Test to {target}")
    if not result:
        print(f"[FAIL] Ping Test to {target} failed.")
        return None

    stats = _parse_ping_output(result.output)
    if stats:
        stats.target = target
        print("\n--- Ping Statistics ---")
        print(f"Min   : {stats.minimum_ms:.2f} ms")
        print(f"Max   : {stats.maximum_ms:.2f} ms")
        print(f"Avg   : {stats.average_ms:.2f} ms")
        print(f"Loss  : {stats.packet_loss:.1f}%")
        write_action(
            "Ping test completed.",
            context={
                "target": target,
                "user": user,
                "min_ms": f"{stats.minimum_ms:.2f}",
                "max_ms": f"{stats.maximum_ms:.2f}",
                "avg_ms": f"{stats.average_ms:.2f}",
                "packet_loss": stats.packet_loss,
            },
            detailed_results=result.output,
        )
    return stats


def tcp_port_scan(host: str, ports: Iterable[int], *, timeout: float = 1.0) -> Dict[int, str]:
    """Perform a lightweight TCP port scan without external dependencies."""

    host = host.strip()
    print(f"\n[SCAN] TCP ports on {host}")
    scan_results: Dict[int, str] = {}
    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            try:
                result = sock.connect_ex((host, port))
                if result == 0:
                    scan_results[port] = "open"
                    print(f"  [OPEN] {port}")
                else:
                    scan_results[port] = "closed"
            except OSError as exc:
                scan_results[port] = f"error: {exc}" 
                print(f"  [ERR ] {port}: {exc}")

    log_table(
        "tcp_port_scan",
        ("port", "status"),
        ((port, status) for port, status in scan_results.items()),
    )
    write_action("TCP port scan complete.", context={"host": host, "open_ports": [p for p, s in scan_results.items() if s == "open"]})
    return scan_results


def dns_health_check(domains: Iterable[str]) -> None:
    """Validate DNS resolution for a list of domains."""

    records: List[Tuple[str, str]] = []
    for domain in domains:
        try:
            ip_address = socket.gethostbyname(domain)
            print(f"[DNS] {domain} -> {ip_address}")
            records.append((domain, ip_address))
        except socket.gaierror as exc:
            print(f"[DNS] {domain} -> resolution failed ({exc})")
            records.append((domain, "error"))

    log_table("dns_health", ("domain", "result"), records)
    write_action("DNS health check complete.", context={"domains": len(records)})


def http_health_check(url: str, *, timeout: int = 10) -> None:
    """Perform an HTTP HEAD request using curl or powershell."""

    os_name = platform.system()
    if shutil.which("curl"):
        command = f"curl -I --max-time {timeout} {url}"
    elif os_name == "Windows":
        command = f"powershell -Command \"(Invoke-WebRequest -UseBasicParsing -Method Head -TimeoutSec {timeout} '{url}').StatusCode\""
    else:
        command = f"wget --spider --timeout={timeout} --tries=1 {url}"

    execute_command(command, f"HTTP health check for {url}")