"""Red team automation and adversary emulation helpers."""

from __future__ import annotations

import os
import platform
from typing import List

from command_utils import execute_command
from logging_utils import log_table, write_action


def vulnerability_scan() -> None:
    """Run an nmap scan with selectable depth."""

    target = input("Enter target hostname or IP address for vulnerability scan: ").strip()
    print("\nSelect scan type:")
    print("1. Version Scan (-sV)")
    print("2. OS Detection (-O)")
    print("3. Aggressive Scan (-A)")
    scan_choice = input("Enter your scan type choice (1, 2, or 3): ").strip()

    if scan_choice == "1":
        cmd = f"nmap -sV {target}"
        desc = f"Version Scan on {target}"
    elif scan_choice == "2":
        cmd = f"nmap -O {target}"
        desc = f"OS Detection Scan on {target}"
    elif scan_choice == "3":
        cmd = f"nmap -A {target}"
        desc = f"Aggressive Scan on {target}"
    else:
        print("Invalid choice. Defaulting to Version Scan.")
        cmd = f"nmap -sV {target}"
        desc = f"Version Scan on {target}"

    result = execute_command(cmd, desc)
    if result:
        write_action(
            "Vulnerability scan executed.",
            context={"target": target, "command": cmd, "duration": f"{result.duration:.2f}s"},
            detailed_results=result.output,
        )


def credential_dump_simulation() -> None:
    """Identify credential exposure risks without executing real dumping tools."""

    os_name = platform.system()
    findings: List[tuple[str, str]] = []

    if os_name == "Windows":
        paths = [
            ("LSA Secrets", "reg query HKLM\\SYSTEM\\CurrentControlSet\\Control\\Lsa /v DisableRestrictedAdmin"),
            ("Credential Guard", "reg query HKLM\\SYSTEM\\CurrentControlSet\\Control\\Lsa /v LsaCfgFlags"),
            ("Cached Credentials", "reg query HKLM\\Security\\Cache"),
        ]
        for label, cmd in paths:
            result = execute_command(cmd, f"Credential exposure check: {label}")
            status = "success" if result and result.succeeded else "failed"
            findings.append((label, status))
    else:
        files = ["/etc/passwd", "/etc/shadow", "~/.ssh/id_rsa"]
        for path in files:
            expanded = os.path.expanduser(path)
            exists = os.path.exists(expanded)
            permissions = oct(os.stat(expanded).st_mode)[-3:] if exists else "---"
            findings.append((expanded, permissions if exists else "missing"))
            print(f"{expanded}: {'accessible' if exists else 'missing'} (mode {permissions})")

    log_table("credential_exposure_baseline", ("item", "status"), findings)
    write_action("Credential exposure simulation complete.", context={"items": len(findings), "os": os_name})


def lateral_movement_simulation() -> None:
    """Baseline lateral movement surfaces by enumerating remote access tooling."""

    os_name = platform.system()
    commands = []
    if os_name == "Windows":
        commands = [
            ("WinRM configuration", "winrm enumerate winrm/config/listener"),
            ("Open SMB sessions", "net session"),
            ("Saved RDP connections", "dir %APPDATA%\\Microsoft\\Windows\\Recent\\AutomaticDestinations")
        ]
    else:
        commands = [
            ("SSH Known Hosts", "cat ~/.ssh/known_hosts"),
            ("SSH Config", "cat ~/.ssh/config"),
            ("Active SSH sessions", "who | grep -i ssh")
        ]

    results: List[tuple[str, str]] = []
    for label, cmd in commands:
        result = execute_command(cmd, f"Lateral movement surface: {label}")
        status = "collected" if result else "failed"
        results.append((label, status))

    log_table("lateral_movement_surface", ("check", "status"), results)
    write_action("Lateral movement simulation complete.", context={"checks": len(results), "os": os_name})


def persistence_checker() -> None:
    """Inspect common persistence mechanisms for suspicious entries."""

    os_name = platform.system()
    findings: List[tuple[str, str]] = []

    if os_name == "Windows":
        commands = [
            ("Run registry", "reg query HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"),
            ("RunOnce registry", "reg query HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce"),
            ("Scheduled tasks", "schtasks /query /fo LIST"),
        ]
        for label, cmd in commands:
            result = execute_command(cmd, f"Persistence check: {label}")
            findings.append((label, "collected" if result else "failed"))
    else:
        cron_dirs = ["/etc/cron.d", "/etc/cron.daily", os.path.expanduser("~/.config/autostart")]
        for path in cron_dirs:
            expanded = os.path.expanduser(path)
            exists = os.path.exists(expanded)
            entries = os.listdir(expanded) if exists else []
            findings.append((expanded, f"{len(entries)} entries" if exists else "missing"))
            print(f"{expanded}: {len(entries)} entries" if exists else f"{expanded}: missing")

    log_table("persistence_check", ("location", "status"), findings)
    write_action("Persistence mechanism assessment complete.", context={"items": len(findings), "os": os_name})


def privilege_escalation_checker() -> None:
    """Check for basic privilege escalation indicators."""

    os_name = platform.system()
    results: List[tuple[str, str]] = []

    if os_name == "Linux":
        suid_search = execute_command("find / -perm -4000 -type f 2>/dev/null | head -n 50", "SUID binary inventory")
        results.append(("SUID binaries", "collected" if suid_search else "failed"))
        sudoers = execute_command("sudo -n true", "Passwordless sudo test")
        results.append(("Passwordless sudo", "configured" if sudoers else "requires password"))
    elif os_name == "Windows":
        command = "whoami /priv"
        privs = execute_command(command, "Enumerate user privileges")
        results.append(("User privileges", "collected" if privs else "failed"))
    else:
        results.append(("Privilege checks", "unsupported"))

    log_table("privilege_escalation_checks", ("check", "status"), results)
    write_action("Privilege escalation assessment complete.", context={"os": os_name})


def phishing_simulation() -> None:
    """Generate a phishing simulation template for awareness exercises."""

    subject = input("Enter the phishing email subject: ").strip() or "Security Update Required"
    lure = input("Enter the primary lure (e.g., payroll, MFA): ").strip() or "mandatory MFA reset"
    link = input("Enter the tracking link or landing page URL: ").strip() or "https://soc.internal/training"

    template = f"""
Subject: {subject}

Hello {{employee_name}},

We detected unusual activity on your account that requires immediate attention.
To continue working without interruption, please complete the {lure} at the secure
link below within the next 24 hours.

{link}

Failure to complete this step will result in a temporary suspension of access.
If you have any questions, contact the Security Operations Center.

Stay vigilant,
SOC Automation Platform
"""
    print("\n--- Phishing Simulation Template ---\n")
    print(template)
    write_action("Generated phishing simulation template.", context={"subject": subject, "lure": lure, "link": link})


def red_team_menu():
    while True:
        print("\n==== Red Team Tools ====")
        print("1. Vulnerability Scan (Dual-use)")
        print("2. Credential Dumping Simulation (Mostly Windows)")
        print("3. Lateral Movement Simulation (Dual-use)")
        print("4. Persistence Mechanism Checker (Dual-use)")
        print("5. Privilege Escalation Checker (Dual-use)")
        print("6. Phishing Simulation (Platform Independent)")
        print("Q. Back")
        choice = input("Select an option: ").strip().upper()
        if choice == "1":
            vulnerability_scan()
        elif choice == "2":
            credential_dump_simulation()
        elif choice == "3":
            lateral_movement_simulation()
        elif choice == "4":
            persistence_checker()
        elif choice == "5":
            privilege_escalation_checker()
        elif choice == "6":
            phishing_simulation()
        elif choice == "Q":
            break
        else:
            print("Invalid selection.")
