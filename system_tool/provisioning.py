"""CSV-driven user provisioning helpers.

Supports creating users in:
- Active Directory (Windows, via PowerShell ActiveDirectory module)
- Local machine accounts (Windows via New-LocalUser; Linux via useradd)

Expected CSV columns (case-insensitive, best-effort):
- username (samAccountName)
- password (optional; if empty, account may be created disabled or without password)
- givenName, surname, displayName, email (optional)
- ou (AD distinguishedName path, e.g., OU=Users,DC=contoso,DC=com)
- groups (semicolon/comma-separated group names)
"""

from __future__ import annotations

import csv
import os
import platform
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Iterable, Optional

from utils.logging_utils import write_action


def _read_rows(csv_path: str) -> Iterable[Dict[str, str]]:
    with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize keys to lowercase for flexible matching
            yield {k.lower(): (v or "").strip() for k, v in row.items() if k}


def _ps_available(cmd: str) -> bool:
    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                cmd,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return completed.returncode == 0
    except OSError:
        return False


def _escape_ps(value: str) -> str:
    # Escape single quotes for PowerShell single-quoted strings
    return value.replace("'", "''")


def provision_users_from_csv(log_folder: str, csv_path: str, target: str = "ad") -> None:
    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"[ERROR] CSV file not found: {csv_file}")
        write_action("Provisioning failed: CSV not found.", log_folder, level="ERROR", detailed_results=str(csv_file))
        return

    target = (target or "ad").lower()
    os_name = platform.system()

    if target == "ad":
        if os_name != "Windows":
            print("[ERROR] Active Directory provisioning requires Windows host.")
            write_action("AD provisioning unsupported OS.", log_folder, level="ERROR", detailed_results=os_name)
            return

        # Check if AD module is available; if not, provide guidance
        ad_ok = _ps_available("$m = Get-Module ActiveDirectory -ListAvailable; if ($m) { exit 0 } else { exit 1 }")
        if not ad_ok:
            msg = (
                "ActiveDirectory PowerShell module not available. Install RSAT AD tools, e.g.:\n"
                "Add-WindowsCapability -Online -Name Rsat.ActiveDirectory.DS-LDS.Tools~~~~0.0.1.0"
            )
            print(msg)
            write_action("AD module missing.", log_folder, level="ERROR", detailed_results=msg)
            return

        created, failed = 0, 0
        for row in _read_rows(str(csv_file)):
            username = row.get("username") or row.get("samaccountname")
            if not username:
                failed += 1
                continue
            given = row.get("givenname", "")
            sn = row.get("surname", "")
            display = row.get("displayname", f"{given} {sn}".strip())
            upn = row.get("upn") or row.get("userprincipalname") or ""
            email = row.get("email") or row.get("mail") or ""
            ou = row.get("ou") or row.get("path") or ""
            groups_raw = row.get("groups") or ""
            groups = [g.strip() for g in groups_raw.replace(";", ",").split(",") if g.strip()]
            password = row.get("password") or ""

            # Build PowerShell command
            fields = [
                f"-Name '{_escape_ps(display or username)}'",
                f"-SamAccountName '{_escape_ps(username)}'",
            ]
            if given:
                fields.append(f"-GivenName '{_escape_ps(given)}'")
            if sn:
                fields.append(f"-Surname '{_escape_ps(sn)}'")
            if email:
                fields.append(f"-EmailAddress '{_escape_ps(email)}'")
            if upn:
                fields.append(f"-UserPrincipalName '{_escape_ps(upn)}'")
            if ou:
                fields.append(f"-Path '{_escape_ps(ou)}'")

            if password:
                ps = (
                    "$sec = ConvertTo-SecureString '" + _escape_ps(password) + "' -AsPlainText -Force; "
                    "New-ADUser " + " ".join(fields) + " -AccountPassword $sec -Enabled $true"
                )
            else:
                ps = "New-ADUser " + " ".join(fields)

            try:
                r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
                if r.returncode != 0:
                    failed += 1
                    write_action(
                        "AD user create failed.",
                        log_folder,
                        level="ERROR",
                        context={"user": username},
                        detailed_results=r.stderr or r.stdout,
                    )
                    continue
                created += 1
                write_action("AD user created.", log_folder, context={"user": username})

                # Add to groups
                for g in groups:
                    add_cmd = f"Add-ADGroupMember -Identity '{_escape_ps(g)}' -Members '{_escape_ps(username)}'"
                    gr = subprocess.run(["powershell", "-NoProfile", "-Command", add_cmd], capture_output=True, text=True)
                    if gr.returncode != 0:
                        write_action(
                            "Add to AD group failed.",
                            log_folder,
                            level="ERROR",
                            context={"user": username, "group": g},
                            detailed_results=gr.stderr or gr.stdout,
                        )
                    else:
                        write_action("Added to AD group.", log_folder, context={"user": username, "group": g})
            except OSError as exc:
                failed += 1
                write_action("PowerShell failed to start.", log_folder, level="ERROR", detailed_results=str(exc))

        print(f"Provisioning complete. Created: {created}, Failed: {failed}")
        write_action("AD provisioning complete.", log_folder, context={"created": created, "failed": failed})
        return

    # Local machine provisioning
    created, failed = 0, 0
    for row in _read_rows(str(csv_file)):
        username = row.get("username")
        if not username:
            failed += 1
            continue
        password = row.get("password") or ""
        display = row.get("displayname", username)

        if os_name == "Windows":
            # Prefer PowerShell New-LocalUser when available
            if shutil.which("powershell"):
                if password:
                    ps = (
                        "$pass = ConvertTo-SecureString '" + _escape_ps(password) + "' -AsPlainText -Force; "
                        f"New-LocalUser -Name '{_escape_ps(username)}' -FullName '{_escape_ps(display)}' -Password $pass -PasswordNeverExpires $true -ErrorAction Stop"
                    )
                else:
                    ps = f"New-LocalUser -Name '{_escape_ps(username)}' -FullName '{_escape_ps(display)}' -NoPassword -ErrorAction Stop"
                try:
                    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
                    if r.returncode != 0:
                        failed += 1
                        write_action("Local user create failed.", log_folder, level="ERROR", detailed_results=r.stderr or r.stdout)
                        continue
                    created += 1
                    write_action("Local user created.", log_folder, context={"user": username})
                except OSError as exc:
                    failed += 1
                    write_action("PowerShell failed to start.", log_folder, level="ERROR", detailed_results=str(exc))
                continue

            # Fallback to 'net user'
            cmd = ["net", "user", username]
            if password:
                cmd += [password, "/add"]
            else:
                cmd += ["/add"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                failed += 1
                write_action("Local user create failed (net).", log_folder, level="ERROR", detailed_results=result.stderr or result.stdout)
            else:
                created += 1
                write_action("Local user created (net).", log_folder, context={"user": username})
        else:
            # Linux/macOS: requires sudo
            cmd = ["sudo", "useradd", "-m", username]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                failed += 1
                write_action("Local user create failed (useradd).", log_folder, level="ERROR", detailed_results=result.stderr or result.stdout)
            else:
                created += 1
                write_action("Local user created (useradd).", log_folder, context={"user": username})

    print(f"Provisioning complete. Created: {created}, Failed: {failed}")
    write_action("Local provisioning complete.", log_folder, context={"created": created, "failed": failed})

