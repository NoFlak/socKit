"""Blue team defensive automation utilities."""

from __future__ import annotations

import csv
import getpass
import hashlib
import os
import platform
import stat
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from command_utils import execute_command
from logging_utils import log_table, write_action


def _prompt_path(prompt: str) -> Path:
    path = Path(input(prompt).strip() or ".")
    return path.expanduser().resolve()


def shadow_file_management() -> None:
    """Review sensitive identity files for hygiene issues."""

    os_name = platform.system()
    entries: List[Tuple[str, str]] = []

    if os_name == "Linux":
        passwd_path = Path("/etc/passwd")
        try:
            with passwd_path.open("r", encoding="utf-8", errors="ignore") as handle:
                for line in handle:
                    if not line.strip() or line.startswith("#"):
                        continue
                    user, _, uid, _, _, home, shell = (line.strip().split(":") + [""] * 7)[:7]
                    risk = "system" if int(uid) < 1000 else "user"
                    if shell in ("/bin/false", "/usr/sbin/nologin"):
                        risk += " (disabled)"
                    entries.append((user, uid, home, shell, risk))
            log_table("passwd_audit", ("user", "uid", "home", "shell", "risk"), entries)
            write_action("Shadow file management baseline captured.", context={"users": len(entries)})
        except OSError as exc:
            print(f"[ERROR] Unable to read {passwd_path}: {exc}")
            write_action("Shadow file read failed.", level="ERROR", context={"path": str(passwd_path), "error": str(exc)})
    else:
        print("Shadow file management is tailored for Unix-like systems.")
        write_action("Shadow file management skipped.", context={"os": os_name}, level="WARNING")


def ad_user_password_check() -> None:
    """Review an exported AD user CSV to detect risky password settings."""

    csv_path = _prompt_path("Enter path to exported AD users CSV (leave blank to skip): ")
    if not csv_path.exists():
        print(f"[WARN] {csv_path} does not exist. Skipping analysis.")
        write_action("AD password check skipped.", level="WARNING", context={"path": str(csv_path)})
        return

    weak_flags = []
    try:
        with csv_path.open("r", encoding="utf-8", errors="ignore") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if not row:
                    continue
                username = row.get("sAMAccountName") or row.get("UserPrincipalName") or row.get("Name")
                if not username:
                    continue
                password_never_expires = row.get("PasswordNeverExpires", "false").lower() in {"true", "1", "yes"}
                pwd_not_required = row.get("PasswordNotRequired", "false").lower() in {"true", "1", "yes"}
                if password_never_expires or pwd_not_required:
                    weak_flags.append((username, password_never_expires, pwd_not_required))

        if weak_flags:
            print("\n[!] Accounts with risky password settings:")
            for username, never_expires, not_required in weak_flags:
                print(f" - {username}: never_expires={never_expires}, pwd_not_required={not_required}")
        else:
            print("[OK] No risky password settings detected in the provided CSV.")

        log_table("ad_password_risks", ("username", "never_expires", "not_required"), weak_flags)
        write_action("AD password hygiene review complete.", context={"flagged_accounts": len(weak_flags)})
    except OSError as exc:
        print(f"[ERROR] Unable to read CSV {csv_path}: {exc}")
        write_action("AD password CSV read failed.", level="ERROR", context={"path": str(csv_path), "error": str(exc)})


def ad_user_privileges() -> None:
    """Query Active Directory for a user's group memberships."""

    try:
        from ldap3 import ALL, Connection, NTLM, Server
    except ImportError:
        print("ldap3 is not installed. Please run `pip install -r requirements.txt`.")
        write_action("AD privilege audit skipped due to missing ldap3.", level="WARNING")
        return

    ad_server = input("Enter AD server (hostname or IP): ").strip()
    ad_domain = input("Enter AD domain (e.g., CONTOSO): ").strip()
    ad_user = input("Enter AD username (e.g., jdoe): ").strip()
    ad_password = getpass.getpass("Enter AD password: ")
    target_user = input("Enter the username to audit (e.g., jdoe): ").strip()

    server = Server(ad_server, get_info=ALL)
    conn = Connection(server, user=f"{ad_domain}\\{ad_user}", password=ad_password, authentication=NTLM, auto_bind=True)

    search_base = f"DC={ad_domain.replace('.', ',DC=')}"
    search_filter = f"(&(objectClass=user)(sAMAccountName={target_user}))"
    conn.search(search_base, search_filter, attributes=["memberOf", "distinguishedName", "description", "whenCreated", "lastLogonTimestamp"])

    if not conn.entries:
        print(f"User {target_user} not found in AD.")
        write_action("AD privilege audit user not found.", level="WARNING", context={"user": target_user})
        return

    user_entry = conn.entries[0]
    print(f"\nUser: {target_user}")
    print(f"Distinguished Name: {user_entry.distinguishedName.value}")
    print(f"Description: {user_entry.description.value}")
    print(f"Created: {user_entry.whenCreated.value}")
    print(f"Last Logon: {user_entry.lastLogonTimestamp.value}")

    groups = user_entry.memberOf.values if user_entry.memberOf else []
    privileged_groups = [g for g in groups if any(p in g for p in ["Domain Admins", "Enterprise Admins", "Administrators", "Schema Admins"])]

    print("\nGroup Memberships:")
    for group in groups:
        marker = " [PRIV]" if group in privileged_groups else ""
        print(f"  - {group}{marker}")

    log_table("ad_privilege_audit", ("group", "privileged"), ((g, g in privileged_groups) for g in groups))
    write_action("AD privilege audit complete.", context={"user": target_user, "privileged_memberships": len(privileged_groups)})
    conn.unbind()


def local_user_password_check() -> None:
    """Check local passwd entries for empty passwords on Unix systems."""

    if platform.system() != "Linux":
        print("Local password check currently supports Linux shadow files.")
        write_action("Local password audit skipped.", level="WARNING", context={"os": platform.system()})
        return

    shadow_path = Path("/etc/shadow")
    if not shadow_path.exists():
        print("/etc/shadow not accessible. Run with elevated privileges.")
        write_action("Shadow file missing.", level="ERROR")
        return

    weak_accounts = []
    try:
        with shadow_path.open("r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                if not line.strip():
                    continue
                username, password_hash, *_ = line.strip().split(":")
                if password_hash in {"!", "*", ""}:
                    weak_accounts.append((username, password_hash or "<empty>"))
        if weak_accounts:
            print("Accounts with disabled or empty passwords:")
            for username, password_hash in weak_accounts:
                print(f" - {username}: {password_hash}")
        else:
            print("All accounts have password hashes set.")
        log_table("shadow_password_check", ("user", "hash"), weak_accounts)
        write_action("Local password audit complete.", context={"weak_accounts": len(weak_accounts)})
    except OSError as exc:
        print(f"[ERROR] Unable to read {shadow_path}: {exc}")
        write_action("Local password audit failed.", level="ERROR", context={"error": str(exc)})


def event_log_analyzer(log_path: str | None = None) -> None:
    """Scan a log file for suspicious keywords and spikes."""

    path = Path(log_path).expanduser() if log_path else _prompt_path("Enter path to log file: ")
    if not path.exists():
        print(f"[WARN] Log file {path} not found.")
        write_action("Event log analysis skipped.", level="WARNING", context={"path": str(path)})
        return

    suspicious_keywords = ["failed", "error", "unauthorized", "denied", "malware"]
    matches: List[Tuple[int, str]] = []
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for lineno, line in enumerate(handle, start=1):
                lowered = line.lower()
                if any(keyword in lowered for keyword in suspicious_keywords):
                    matches.append((lineno, line.strip()))
        print(f"Found {len(matches)} suspicious entries.")
        for lineno, entry in matches[:20]:
            print(f"[{lineno}] {entry}")
        log_table("event_log_alerts", ("line", "entry"), matches)
        write_action("Event log analysis complete.", context={"matches": len(matches), "path": str(path)})
    except OSError as exc:
        print(f"[ERROR] Unable to read log file {path}: {exc}")
        write_action("Event log analysis failed.", level="ERROR", context={"path": str(path), "error": str(exc)})


def network_share_auditor() -> None:
    """Enumerate a network share and identify world-writable directories."""

    share_path = _prompt_path("Enter path to network share: ")
    if not share_path.exists():
        print(f"[WARN] {share_path} does not exist.")
        write_action("Network share audit skipped.", level="WARNING", context={"path": str(share_path)})
        return

    findings: List[Tuple[str, str]] = []
    for root, dirs, _files in os.walk(share_path):
        for directory in dirs:
            full_path = Path(root) / directory
            try:
                mode = full_path.stat().st_mode
                world_writable = bool(mode & stat.S_IWOTH)
                if world_writable:
                    findings.append((str(full_path), "world-writable"))
            except OSError:
                continue

    if findings:
        print("World-writable directories detected:")
        for path, status in findings:
            print(f" - {path}: {status}")
    else:
        print("No world-writable directories detected in the provided path.")

    log_table("network_share_findings", ("path", "status"), findings)
    write_action("Network share audit complete.", context={"flagged": len(findings), "path": str(share_path)})


def patch_status_checker() -> None:
    """Check for pending OS updates using native tooling."""

    os_name = platform.system()
    if os_name == "Windows":
        command = "powershell -Command \"Get-WindowsUpdateLog\""
    elif os_name == "Linux":
        command = "sudo apt list --upgradable"
    elif os_name == "Darwin":
        command = "softwareupdate -l"
    else:
        print("Patch status checker unsupported on this OS.")
        write_action("Patch status unsupported OS.", level="WARNING", context={"os": os_name})
        return

    execute_command(command, "Patch status assessment")


def file_integrity_checker() -> None:
    """Calculate a SHA256 hash for one or more files."""

    paths = input("Enter file paths separated by commas: ").split(",")
    entries: List[Tuple[str, str]] = []
    for raw_path in paths:
        path = Path(raw_path.strip()).expanduser()
        if not path.exists():
            print(f"[WARN] {path} missing.")
            entries.append((str(path), "missing"))
            continue
        hash_obj = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                hash_obj.update(chunk)
        digest = hash_obj.hexdigest()
        entries.append((str(path), digest))
        print(f"{path}: {digest}")

    log_table("file_integrity_hashes", ("path", "sha256"), entries)
    write_action("File integrity hashes computed.", context={"files": len(entries)})


def service_process_monitor() -> None:
    """List running processes or services using platform tooling."""

    os_name = platform.system()
    if os_name == "Windows":
        command = "tasklist"
    else:
        command = "ps aux"
    execute_command(command, "Process inventory", timeout=180)


def backup_verification() -> None:
    """Validate that a backup file exists and is recent."""

    backup_path = _prompt_path("Enter path to backup file or directory: ")
    if not backup_path.exists():
        print(f"[WARN] Backup path {backup_path} missing.")
        write_action("Backup verification failed.", level="ERROR", context={"path": str(backup_path)})
        return

    mtime = datetime.fromtimestamp(backup_path.stat().st_mtime)
    age_days = (datetime.now() - mtime).days
    print(f"Backup last modified: {mtime} ({age_days} days ago)")
    write_action("Backup verification complete.", context={"path": str(backup_path), "age_days": age_days})


def user_session_tracker() -> None:
    """Display current interactive sessions."""

    os_name = platform.system()
    if os_name == "Windows":
        command = "query user"
    else:
        command = "who"
    execute_command(command, "User session tracker")


def firewall_av_status_checker() -> None:
    """Check host firewall or antivirus status."""

    os_name = platform.system()
    if os_name == "Windows":
        command = "powershell -Command \"Get-MpComputerStatus | Select AntivirusEnabled,AMServiceEnabled,RealTimeProtectionEnabled\""
    elif os_name == "Linux":
        command = "sudo ufw status"
    elif os_name == "Darwin":
        command = "/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate"
    else:
        print("Firewall/AV status checker unsupported on this OS.")
        write_action("Firewall status unsupported.", level="WARNING", context={"os": os_name})
        return

    execute_command(command, "Firewall/AV status assessment")


def malware_persistence_scan() -> None:
    try:
        from malware_scanner import MalwareRegistryScanner
    except ImportError:
        print("Malware scanner module unavailable.")
        write_action("Malware scan skipped due to missing module.", level="WARNING")
        return

    scanner = MalwareRegistryScanner()
    scanner.run_full_scan()


MENU_OPTIONS = {
    "1": ("Shadow File Management", shadow_file_management),
    "2": ("AD User Password Audit", ad_user_password_check),
    "3": ("AD User Privilege Audit", ad_user_privileges),
    "4": ("Local User Password Audit", local_user_password_check),
    "5": ("Event Log Analyzer", event_log_analyzer),
    "6": ("Network Share Auditor", network_share_auditor),
    "7": ("Patch Status Checker", patch_status_checker),
    "8": ("File Integrity Checker", file_integrity_checker),
    "9": ("Service/Process Monitor", service_process_monitor),
    "10": ("Backup Verification", backup_verification),
    "11": ("User Session Tracker", user_session_tracker),
    "12": ("Firewall/AV Status Checker", firewall_av_status_checker),
    "13": ("Malware Persistence Scan", malware_persistence_scan),
}


def blue_team_menu() -> None:
    while True:
        print("\n==== Blue Team Tools ====")
        for key, (label, _) in MENU_OPTIONS.items():
            print(f"{key}. {label}")
        print("Q. Back")
        choice = input("Select an option: ").strip().upper()
        if choice == "Q":
            break
        option = MENU_OPTIONS.get(choice)
        if option:
            _, action = option
            action()
        else:
            print("Invalid selection.")
