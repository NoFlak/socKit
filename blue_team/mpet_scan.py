import winreg
import subprocess
import os
import glob
import ctypes
import sys
import argparse
from datetime import datetime

class MalwarePersistenceScanner:
    """
    Malware Persistence & Execution Tracker (MPET) scans Windows registry,
    startup folders, scheduled tasks, prefetch files, and PowerShell event logs
    for suspicious persistence mechanisms and execution artifacts.
    """

    def __init__(self, log_dir="logs", log_file=None):
        # Registry locations to scan for autostart entries
        self.registry_paths = {
            "HKCU_Run": r"Software\Microsoft\Windows\CurrentVersion\Run",
            "HKCU_RunOnce": r"Software\Microsoft\Windows\CurrentVersion\RunOnce",
            "HKLM_Run": r"Software\Microsoft\Windows\CurrentVersion\Run",
            "HKLM_RunOnce": r"Software\Microsoft\Windows\CurrentVersion\RunOnce",
            "HKLM_RunOnceEx": r"Software\Microsoft\Windows\CurrentVersion\RunOnceEx",
            "HKLM_StartupApproved": r"Software\Microsoft\Windows\CurrentVersion\StartupApproved\Run",
            "HKLM_Services": r"SYSTEM\CurrentControlSet\Services"
        }

        # Startup folders (current user and all users)
        self.startup_dirs = [
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"),
            os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs\Startup")
        ]

        # Keywords indicating suspicious or malicious activity
        self.suspicious_keywords = [
            "cmd.exe", "powershell", "wscript", "cscript", "regsvr32",
            "bitsadmin", "schtasks", "curl", ".bat", ".ps1", ".js", ".vbs",
            "startup", "appdata", "temp", "system32", "autorun", "rundll32",
            "wmic", "mshta", "ftp", "tftp", "netsh"
        ]

        # Keywords indicating severe/high risk malware families
        self.severe_keywords = [
            "ransomware", "cryptolocker", "coinminer", "keylogger", "backdoor",
            "mimikatz", "cobaltstrike", "meterpreter"
        ]

        self.total_entries = 0
        self.suspicious_count = 0
        self.severe_count = 0

        # Create log directory if it doesn't exist
        if log_file:
            # If a log file path includes directories, ensure they exist
            log_dirname = os.path.dirname(log_file)
            if log_dirname and not os.path.exists(log_dirname):
                os.makedirs(log_dirname, exist_ok=True)
        else:
            os.makedirs(log_dir, exist_ok=True)

        # If no log filename specified, create one with timestamp inside logs folder
        if not log_file:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"mpet_scan_log_{ts}.txt"
            log_file = os.path.join(log_dir, log_file)

        self.log_file = log_file

        # Clear/create log file upfront
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write(f"MPET Scan started at {datetime.now()}\n\n")

    def log(self, message):
        print(message)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(message + "\n")

    def get_hive(self, hive_name):
        """Return registry hive constant based on hive string prefix."""
        if hive_name.startswith("HKCU"):
            return winreg.HKEY_CURRENT_USER
        elif hive_name.startswith("HKLM"):
            return winreg.HKEY_LOCAL_MACHINE
        else:
            raise ValueError(f"Unknown hive: {hive_name}")

    def scan_registry(self):
        self.log("\n🔍 Scanning Registry for Auto-Start Entries...\n")
        for hive_name, subkey in self.registry_paths.items():
            try:
                hive = self.get_hive(hive_name)
            except ValueError as ve:
                self.log(f"⚠️ {ve}")
                continue

            self.log(f"📂 {hive_name}\\{subkey}")
            try:
                with winreg.OpenKey(hive, subkey) as key:
                    value_count = winreg.QueryInfoKey(key)[1]
                    if value_count == 0:
                        self.log("  (No entries found)")
                    for i in range(value_count):
                        try:
                            name, value, _ = winreg.EnumValue(key, i)
                            self.total_entries += 1
                            value_lower = str(value).lower()
                            is_suspicious = any(k in value_lower for k in self.suspicious_keywords)
                            is_severe = any(k in value_lower for k in self.severe_keywords)
                            if is_severe:
                                self.severe_count += 1
                            if is_suspicious:
                                self.suspicious_count += 1
                            status = "⚠️ SEVERE" if is_severe else ("⚠️ SUSPICIOUS" if is_suspicious else "✅")
                            self.log(f"  {status} {name}: {value}")
                        except OSError:
                            # Continue if registry value cannot be read
                            continue
            except FileNotFoundError:
                self.log("  (Key not found)")
            except Exception as e:
                self.log(f"  ⚠️ Error reading {hive_name}\\{subkey}: {e}")
            self.log("")

    def scan_startup_folders(self):
        self.log("📁 Scanning Startup Folder Executables...\n")
        for path in self.startup_dirs:
            self.log(f"📂 {path}")
            try:
                if os.path.exists(path):
                    files = os.listdir(path)
                    if not files:
                        self.log("  (No files found)")
                    for file in files:
                        file_path = os.path.join(path, file)
                        self.total_entries += 1
                        file_lower = file.lower()
                        is_suspicious = any(k in file_lower for k in self.suspicious_keywords)
                        is_severe = any(k in file_lower for k in self.severe_keywords)
                        if is_severe:
                            self.severe_count += 1
                        if is_suspicious:
                            self.suspicious_count += 1
                        status = "⚠️ SEVERE" if is_severe else ("⚠️ SUSPICIOUS" if is_suspicious else "✅")
                        self.log(f"  {status} {file}")
                else:
                    self.log("  (Path does not exist)")
            except Exception as e:
                self.log(f"  ⚠️ Error accessing {path}: {e}")
            self.log("")

    def list_scheduled_tasks(self):
        self.log("📅 Listing Scheduled Tasks...\n")
        suspicious_tasks = []
        try:
            result = subprocess.run(
                ["schtasks", "/query", "/fo", "LIST", "/v"],
                capture_output=True, text=True, shell=True
            )
            if result.returncode != 0:
                self.log(f"⚠️ Failed to query scheduled tasks: {result.stderr.strip()}")
                return 0

            lines = result.stdout.splitlines()
            current_task = []

            for line in lines:
                if line.strip() == "":
                    # End of current task block
                    task_block = "\n".join(current_task)
                    if any(k in task_block.lower() for k in self.suspicious_keywords):
                        suspicious_tasks.append(task_block)
                    current_task = []
                else:
                    current_task.append(line)
            # Check last task block if no trailing newline
            if current_task:
                task_block = "\n".join(current_task)
                if any(k in task_block.lower() for k in self.suspicious_keywords):
                    suspicious_tasks.append(task_block)

            if suspicious_tasks:
                self.log(f"⚠️ Found {len(suspicious_tasks)} suspicious scheduled task(s):\n")
                for task in suspicious_tasks:
                    self.log(task)
                    self.log("-" * 60)
            else:
                self.log("✅ No suspicious scheduled tasks found.")
        except Exception as e:
            self.log(f"⚠️ Error retrieving scheduled tasks: {e}")
            return 0

        return len(suspicious_tasks)

    def scan_prefetch(self):
        self.log("\n🕵️ Scanning Prefetch Files for Suspicious Activity...\n")
        prefetch_dir = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'Prefetch')
        if not os.path.isdir(prefetch_dir):
            self.log(f"⚠️ Prefetch directory not found: {prefetch_dir}")
            return

        try:
            count = 0
            for pf_file in glob.glob(os.path.join(prefetch_dir, "*.pf")):
                name = os.path.basename(pf_file).lower()
                if any(k in name for k in self.suspicious_keywords):
                    self.log(f"  ⚠️ Suspicious prefetch file: {name}")
                    count += 1
            if count == 0:
                self.log("✅ No suspicious prefetch files found.")
        except Exception as e:
            self.log(f"⚠️ Error scanning prefetch files: {e}")

    def scan_powershell_event_log(self):
        self.log("\n🧠 Scanning PowerShell Event Log (Event ID 4104)...\n")
        try:
            result = subprocess.run(
                ['wevtutil', 'qe', 'Microsoft-Windows-PowerShell/Operational',
                 '/q:*[System[(EventID=4104)]]', '/f:text', '/c:30'],
                capture_output=True, text=True, shell=True
            )
            if result.returncode != 0:
                self.log(f"⚠️ Failed to query PowerShell event log: {result.stderr.strip()}")
                return

            lines = result.stdout.splitlines()
            suspicious_entries = [line for line in lines if any(k in line.lower() for k in self.suspicious_keywords)]
            if suspicious_entries:
                self.log(f"⚠️ Found {len(suspicious_entries)} suspicious PowerShell event entries:")
                for entry in suspicious_entries:
                    self.log(f"  🔸 {entry}")
            else:
                self.log("✅ No suspicious PowerShell script executions found.")
        except Exception as e:
            self.log(f"⚠️ Error reading PowerShell event log: {e}")

    def run_full_scan(self):
        self.log("\n🛡️ Starting Malware Persistence & Execution Tracker (MPET) Scan...\n")
        self.scan_registry()
        self.scan_startup_folders()
        suspicious_tasks_count = self.list_scheduled_tasks()
        self.scan_prefetch()
        self.scan_powershell_event_log()

        self.log("\n--- Scan Summary ---")
        self.log(f"Total entries scanned: {self.total_entries}")
        self.log(f"Suspicious entries found: {self.suspicious_count}")
        self.log(f"Severe entries found: {self.severe_count}")
        self.log(f"Suspicious scheduled tasks found: {suspicious_tasks_count}")
        self.log(f"Log saved to: {self.log_file}")
        self.log("\n✅ Scan complete. Please review the above entries carefully.\n")


def main():
    if not ctypes.windll.shell32.IsUserAnAdmin():
        print("⚠️ Please run this tool as Administrator.")
        input("Press Enter to exit...")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Malware Persistence & Execution Tracker (MPET)"
    )
    parser.add_argument("--log", metavar="FILE", help="Write scan results to a log file (inside logs/ folder)")
    args = parser.parse_args()

    log_path = None
    if args.log:
        log_path = os.path.join("logs", args.log)

    scanner = MalwarePersistenceScanner(log_file=log_path)
    scanner.run_full_scan()


if __name__ == "__main__":
    main()
