# blue_team.py

"""
Blue Team Toolkit CLI module

Provides various Blue Team audit and defense utilities,
including Active Directory auditing, malware scans,
file integrity, and new content spoofing detection.

User navigates a menu to select tools interactively.
"""

import os
import getpass
import subprocess
from datetime import datetime, timedelta

from utils.logging_utils import write_action
from utils.command_utils import execute_command

from ldap3 import Server, Connection, ALL, NTLM

from blue_team.mpet_scan import MalwarePersistenceScanner
from blue_team.contentSpoofChecker import scan_directory as content_spoof_scan  # Assumes scan function exposed


def filetime_to_dt(filetime):  # complete
    """
    Convert Windows FILETIME format to human-readable datetime string.

    FILETIME is number of 100-nanosecond intervals since Jan 1, 1601 UTC.
    Returns "Never" if no value or zero provided.
    """
    if not filetime or int(filetime) == 0:
        return "Never"
    try:
        us = int(filetime) / 10  # convert to microseconds
        dt = datetime(1601, 1, 1) + timedelta(microseconds=us)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(filetime)


def shadow_file_management(log_folder=None):  # placeholder
    """
    Placeholder for Shadow File Management audit.
    """
    print("[PLACEHOLDER] Shadow file management not yet implemented.")
    if log_folder:
        write_action("Shadow file management placeholder accessed.", log_folder)


def ad_user_password_check(log_folder=None):  # placeholder
    """
    Placeholder for auditing AD user password policies.
    """
    print("[PLACEHOLDER] AD user password audit not yet implemented.")
    if log_folder:
        write_action("AD user password audit placeholder accessed.", log_folder)


def ad_user_privileges(log_folder=None):  # complete
    """
    Active Directory User Privilege Audit
    """
    print("\n=== AD User Privilege Audit ===")
    ad_server = input("Enter AD server (hostname or IP): ").strip()
    ad_domain = input("Enter AD domain (e.g., CONTOSO.COM): ").strip()
    ad_user = input("Enter AD username (e.g., jdoe): ").strip()
    ad_password = getpass.getpass("Enter AD password: ")
    target_user = input("Enter the username to audit (e.g., jdoe): ").strip()

    conn = None
    try:
        server = Server(ad_server, get_info=ALL)
        conn = Connection(server, user=f"{ad_domain}\\{ad_user}", password=ad_password, authentication=NTLM, auto_bind=True)

        dc_parts = ad_domain.split('.')
        search_base = ','.join(f"DC={part}" for part in dc_parts)
        search_filter = f"(&(objectClass=user)(sAMAccountName={target_user}))"
        conn.search(search_base, search_filter, attributes=[
            'memberOf', 'distinguishedName', 'userAccountControl', 'description',
            'whenCreated', 'lastLogonTimestamp']
        )

        if not conn.entries:
            print(f"User {target_user} not found in AD.")
            if log_folder:
                write_action(f"AD user {target_user} not found.", log_folder)
            return

        user_entry = conn.entries[0]
        print(f"\nUser: {target_user}")
        print(f"Distinguished Name: {user_entry.distinguishedName.value or 'N/A'}")
        print(f"Description: {user_entry.description.value or 'N/A'}")
        print(f"Account Control: {user_entry.userAccountControl.value or 'N/A'}")
        print(f"Created: {user_entry.whenCreated.value or 'N/A'}")
        print(f"Last Logon: {filetime_to_dt(user_entry.lastLogonTimestamp.value)}")

        groups = user_entry.memberOf.values if user_entry.memberOf else []
        print("\nGroup Memberships:")
        for group in groups:
            print(f"  - {group}")

        privileged = [g for g in groups if any(p in g for p in [
            "Domain Admins", "Enterprise Admins", "Administrators", "Schema Admins"
        ])]
        if privileged:
            print("\n[!] User is a member of privileged groups:")
            for group in privileged:
                print(f"  [PRIVILEGED] {group}")
            if log_folder:
                write_action(f"User {target_user} is privileged: {privileged}", log_folder)
        else:
            print("\nUser is not a member of typical privileged groups.")
            if log_folder:
                write_action(f"User {target_user} has no privileged group membership.", log_folder)

    except Exception as e:
        print(f"[ERROR] LDAP query failed: {e}")
        if log_folder:
            write_action(f"LDAP query failed for {target_user}: {e}", log_folder, level="ERROR")
    finally:
        if conn:
            try:
                conn.unbind()
            except Exception:
                pass


def local_user_password_check(log_folder=None):  # complete
    """
    Local User Password Audit (Windows Only)
    """
    print("\n=== Local User Password Audit ===")

    ps_script = r"""
    Get-LocalUser | Select-Object Name,Enabled,PasswordLastSet,PasswordExpires,UserMayChangePassword,AccountNeverExpires | Format-Table -AutoSize
    """

    try:
        result = subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True)

        if result.returncode != 0:
            print(f"[ERROR] PowerShell execution failed:\n{result.stderr.strip()}")
            if log_folder:
                write_action(f"Local user password audit failed: {result.stderr.strip()}", log_folder, level="ERROR")
            return

        output = result.stdout.strip()
        if not output:
            print("No local user information found.")
            if log_folder:
                write_action("Local user password audit found no data.", log_folder)
            return

        print("Local User Accounts:\n")
        print(output)

        if log_folder:
            write_action("Local user password audit performed.", log_folder)

    except Exception as e:
        print(f"[ERROR] Failed to audit local users: {e}")
        if log_folder:
            write_action(f"Local user password audit error: {e}", log_folder, level="ERROR")


def event_log_analyzer(log_folder=None):  # placeholder
    print("[PLACEHOLDER] Event log analyzer not yet implemented.")
    if log_folder:
        write_action("Event log analyzer placeholder accessed.", log_folder)


def network_share_auditor(log_folder=None):  # complete
    print("\n=== Network Share Auditor ===")
    try:
        result = subprocess.run(["net", "share"], capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)
            if log_folder:
                write_action("Network share auditor executed.", log_folder)
        else:
            print(f"[ERROR] net share command failed:\n{result.stderr.strip()}")
            if log_folder:
                write_action(f"Network share auditor failed: {result.stderr.strip()}", log_folder, level="ERROR")
    except Exception as e:
        print(f"[ERROR] Network share auditor error: {e}")
        if log_folder:
            write_action(f"Network share auditor error: {e}", log_folder, level="ERROR")


def patch_status_checker(log_folder=None):  # complete
    print("\n=== Patch Status Checker ===")
    ps_script = r"""
    Get-HotFix | Select-Object HotFixID, InstalledOn | Format-Table -AutoSize
    """
    try:
        result = subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[ERROR] PowerShell execution failed:\n{result.stderr.strip()}")
            if log_folder:
                write_action(f"Patch status check failed: {result.stderr.strip()}", log_folder, level="ERROR")
            return
        print(result.stdout)
        if log_folder:
            write_action("Patch status checker executed.", log_folder)
    except Exception as e:
        print(f"[ERROR] Patch status checker error: {e}")
        if log_folder:
            write_action(f"Patch status checker error: {e}", log_folder, level="ERROR")


def file_integrity_checker(log_folder=None):  # placeholder
    print("[PLACEHOLDER] File integrity checker not yet implemented.")
    if log_folder:
        write_action("File integrity checker placeholder accessed.", log_folder)


def service_process_monitor(log_folder=None):  # complete
    print("\n=== Service and Process Monitor ===")
    try:
        svc_result = subprocess.run(["powershell", "-Command", "Get-Service | Format-Table -AutoSize"], capture_output=True, text=True)
        print("Services:\n", svc_result.stdout)

        proc_result = subprocess.run(["powershell", "-Command", "Get-Process | Sort-Object CPU -Descending | Select-Object -First 10 | Format-Table -AutoSize"], capture_output=True, text=True)
        print("Top 10 processes by CPU usage:\n", proc_result.stdout)

        if log_folder:
            write_action("Service/process monitor executed.", log_folder)
    except Exception as e:
        print(f"[ERROR] Service/process monitor error: {e}")
        if log_folder:
            write_action(f"Service/process monitor error: {e}", log_folder, level="ERROR")


def backup_verification(log_folder=None):  # placeholder
    print("[PLACEHOLDER] Backup verification not yet implemented.")
    if log_folder:
        write_action("Backup verification placeholder accessed.", log_folder)


def user_session_tracker(log_folder=None):  # complete
    print("\n=== User Session Tracker ===")
    try:
        result = subprocess.run(["query", "user"], capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)
            if log_folder:
                write_action("User session tracker executed.", log_folder)
        else:
            print(f"[ERROR] query user command failed:\n{result.stderr.strip()}")
            if log_folder:
                write_action(f"User session tracker failed: {result.stderr.strip()}", log_folder, level="ERROR")
    except Exception as e:
        print(f"[ERROR] User session tracker error: {e}")
        if log_folder:
            write_action(f"User session tracker error: {e}", log_folder, level="ERROR")


def firewall_av_status_checker(log_folder=None):  # complete
    print("\n=== Firewall and AV Status Checker ===")
    try:
        fw_result = subprocess.run(["powershell", "-Command", "Get-NetFirewallProfile | Format-Table Name,Enabled"], capture_output=True, text=True)
        print("Firewall Profiles:\n", fw_result.stdout)

        av_result = subprocess.run(["powershell", "-Command", "Get-MpComputerStatus | Select-Object AMServiceEnabled,AntispywareEnabled,AntivirusEnabled,RealTimeProtectionEnabled | Format-List"], capture_output=True, text=True)
        print("Windows Defender Status:\n", av_result.stdout)

        if log_folder:
            write_action("Firewall/AV status checker executed.", log_folder)
    except Exception as e:
        print(f"[ERROR] Firewall/AV status checker error: {e}")
        if log_folder:
            write_action(f"Firewall/AV status checker error: {e}", log_folder, level="ERROR")


def malware_persistence_scan(log_folder):  # complete
    print("\n=== Malware Persistence Scan ===")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_folder, f"mpet_scan_log_{ts}.txt")
    scanner = MalwarePersistenceScanner(log_file=log_file)
    scanner.run_full_scan()
    print(f"\nScan complete. Log saved to: {log_file}\n")
    write_action("Malware Persistence Scan completed.", log_folder)


def content_spoof_checker_menu(log_folder):  # complete
    print("\n=== Content Spoof Checker ===")
    folder = input("Enter directory path to scan for spoofed files (e.g., uploads/): ").strip()
    if not folder:
        print("No folder provided. Returning to menu.")
        return
    try:
        results = content_spoof_scan(folder)
        spoofed = [r for r in results if not r.get("match", True)]
        print(f"Scan complete. Found {len(spoofed)} potential spoofed files:")
        for r in spoofed:
            print(f" - {r['file']} (Ext: {r['extension']} vs Detected: {r['detected_type']})")
        print("See spoof_report.txt for full details.")
        write_action(f"Content Spoof Checker ran on {folder}, {len(spoofed)} spoofed files found.", log_folder)
    except Exception as e:
        print(f"[ERROR] Content spoof checker failed: {e}")
        write_action(f"Content Spoof Checker error: {e}", log_folder, level="ERROR")


def blue_team_menu(log_folder):  # complete
    while True:
        print("\n==== Blue Team Tools ====")
        print("1. Shadow File Management")
        print("2. AD User Password Audit")
        print("3. AD User Privilege Audit")
        print("4. Local User Password Audit")
        print("5. Event Log Analyzer")
        print("6. Network Share Auditor")
        print("7. Patch Status Checker")
        print("8. File Integrity Checker")
        print("9. Service/Process Monitor")
        print("10. Backup Verification")
        print("11. User Session Tracker")
        print("12. Firewall/AV Status Checker")
        print("13. Malware Persistence Scan")
        print("14. Content Spoof Checker")
        print("Q. Back")
        choice = input("Select an option: ").strip().upper()
        if choice == "1":
            shadow_file_management(log_folder)
        elif choice == "2":
            ad_user_password_check(log_folder)
        elif choice == "3":
            ad_user_privileges(log_folder)
        elif choice == "4":
            local_user_password_check(log_folder)
        elif choice == "5":
            event_log_analyzer(log_folder)
        elif choice == "6":
            network_share_auditor(log_folder)
        elif choice == "7":
            patch_status_checker(log_folder)
        elif choice == "8":
            file_integrity_checker(log_folder)
        elif choice == "9":
            service_process_monitor(log_folder)
        elif choice == "10":
            backup_verification(log_folder)
        elif choice == "11":
            user_session_tracker(log_folder)
        elif choice == "12":
            firewall_av_status_checker(log_folder)
        elif choice == "13":
            malware_persistence_scan(log_folder)
        elif choice == "14":
            content_spoof_checker_menu(log_folder)
        elif choice == "Q":
            break
        else:
            print("Invalid selection.")

def run(log_folder):
    blue_team_menu(log_folder)

if __name__ == "__main__":  # complete
    logs_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    blue_team_menu(log_folder=logs_dir)
